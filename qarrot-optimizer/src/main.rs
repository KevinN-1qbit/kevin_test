//! # `qarrot-optimizer`
//! 
//! This is one phase of the QArROT pipeline, which runs after basis decomposition (currently done
//! using the old transpiler code) and before the scheduler.
//! 
//! This is a replacement for the old `qarrot-transpiler` code. It serves exactly the same purpose
//! and can produce equivalent output (see the notes in [`tester`] for more information). However,
//! it is significantly faster due to two new algorithms:
//! 
//! - The new core optimization routine (described on Notion on the page "Improved Transpiler").
//! - A fast approximate partitioning routine
//!
//! For more information on the algorithm, see the documentation for the [`run`] function and the
//! [`optimization`] module.
//!
//! The crate is organized as follows:
//!
//! - [`buffer`] contains a type for a Vec-like struct which can either be regular memory or a
//!   mmap'd file.
//! - [`bits`] contains traits and implementations for bitset manipulations
//! - [`chunk_iter`] contains methods for iterating over slices in chunks of a known size
//!  (to help the autovectorizer)
//! - [`basis`] contains types for representing qubit bases (built on bitsets). These are split
//!   into statically sized bases of various known sizes and a fallback dynamically sized basis
//!   type (which allows any number of qubits but is vastly slower). Most of the functions and
//!   types here are generic w.r.t. the type used to represent bases so long as it impl's the
//!   [`basis::Basis`] trait.
//! - [`operation`] contains the operation type that is used to store circuits
//! - [`input`] contains the lexer and parser for the input format.
//! - [`symplectic`] contains a type for the symplectic representation of Pauli operators
//! - [`clifford`] contains a type for representing Clifford operators
//! - [`optimization`] contains the individual methods used for phases of optimizing circuits
//!   (see the [`run`] function for an overview)
//! - [`output`] contains methods for outputting the optimized circuit
//! - [`tester`] contains methods for comparing optimized circuits while properly accounting for
//!   the non-deterministic ordering of mutually commuting groups of T gates.
//! 
//! Finally, this module contains the primary optimization routine (in the [`run`]) function. For
//! best performance, we want this to be monomorphized depending on the basis type used. But, we
//! obviously don't statically know the size of input circuits. The old transpiler handled that by
//! recompiling for every input size, but we don't need to do that. The sequence of functions
//! called for a normal run are:
//! 
//! 1. [`main`]. This function initializes the logger and parses and verifies the command line
//!    arguments. It opens the relevant files and outputs, then calls the next function.
//! 1. [`infer_run`]. This uses the input source (it's generic over input type, so it doesn't
//!    matter whether it's a compressed file, uncompressed file, string, STDIN, &c) and initializes
//!    the tokenizer over that input. This determines the number of qubits in the file by:
//!    - Reading the first complete token.
//!    - If this token is a repeat statement, read the next token.
//!    - Since loops are not allowed to nest in our input format, we now have an operation. All
//!      operations must have the same length, so we error if they're not. The length of this
//!      operation is now used to statically dispatch on the number of qubits.
//! 1. [`run`]. This function runs the core algorithm.

// pub mod buffer;
pub mod chunk_iter;
pub mod bits;
pub mod basis;
pub mod operation;
pub mod input;
pub mod qasm;
pub mod symplectic;
pub mod clifford;
pub mod optimization;
pub mod output;
pub mod tester;

use log::{debug, info, trace, warn};
use optimization::*;

use std::{collections::HashMap, fmt::Debug, fs, io::{self, Read}, mem, path::{Path, PathBuf}};

use anyhow::{bail, Context};
use lazy_static::lazy_static;
use flate2::read::GzDecoder;

use basis::{Basis, Basis8};
use clap::Parser;
use input::parser::complete_op;
use operation::Operation;
use output::Output;

use crate::{basis::*, input::{lexer::{Token, TokenIterator}, parser::InstructionIterator, Input}, output::{fmt_operation, StringOut, WriteOutput}, tester::Tester};


// accept at most this large a preallocated buffer 
// should help prevent DoS attacks
// equal to 16GiB for 256-bit operation
pub const MAX_PREALLOC_OPERATIONS: usize = (2 << 33) / mem::size_of::<Operation<Basis256>>();


/// Enum of supported compression algorithms. Currently only GZip.
#[derive(Clone, Copy, PartialEq, Eq, Hash, Debug)]
pub enum CompressionAlgorithm {
    GZip,
}

#[derive(Clone, Copy, PartialEq, Eq, Hash, Debug, Default)]
pub enum InputType {
    #[default]
    Other,
    Txt,
    Qasm,
}


lazy_static! {
    /// This is a hashmap from file extensions to compression algorithms used to automatically infer whether a file is compressed (overridden by `--decompression-algorithm`).
    ///
    /// Currently, only GZip is used, recognized with the extensions "gz" and "gzip".
    static ref COMPRESSION_EXTENSION: HashMap<&'static str, CompressionAlgorithm> = {
        let mut map = HashMap::new();

        map.insert("gz", CompressionAlgorithm::GZip);
        map.insert("gzip", CompressionAlgorithm::GZip);

        map
    };
}


/// Run the 
#[derive(Parser, Debug)]
struct CommandLineArgs {
    /// Input path (or "STDIN" to read from standard input)
    #[arg(short, long)]
    input: String,

    /// Output path
    #[arg(short, long)]
    output: String,

    /// File type (if not provided, automatically determined from file extension). "qasm" or "txt".
    #[arg(long, short('t'))]
    file_type: Option<String>,

    /// Big file support (avoids storing the whole circuit in memory, at the cost of speed)
    #[arg(short, long)]
    big_file: bool,

    /// Hint the number of operations. If used correctly, this can reduce reallocations and is especially important if the input file is compressed.
    #[arg(short, long)]
    num_operations: Option<usize>,

    /// Target buffer length
    #[arg(long, default_value_t=16384)]
    target_buffer_length: usize,

    /// Shrink buffer after repeat (possibly reduce non-peak memory usage at the cost of more allocations)
    #[arg(short, long)]
    shrink_buffer_after_repeat: bool,

    /// Overwrite existing output path
    #[arg(long)]
    overwrite: bool,

    /// Bypass optimization (testing use only)
    #[arg(long)]
    bypass: bool,

    /// Force a particular decompression method (usually determined by extension)
    #[arg(long)]
    decompression_algorithm: Option<String>,

    /// GZip compress the output
    #[arg(long, short)]
    compress_output: bool,

    /// Full partitioning (much slower, but may slightly decrease final gate count)
    #[arg(long, short)]
    full_partitioning: bool,

    /// Test against reference
    #[arg(long)]
    test_against: Option<PathBuf>,
}


/// This struct is used to store non-circuit runtime parameters.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub struct RunConfig {
    pub target_buffer_length: usize,
    pub bypass: bool,
    pub shrink_buffer_after_repeat: bool,
    pub full_partitioning: bool,
    pub big_file: bool,
    pub num_operations: Option<usize>,
    pub file_type: InputType,
}


impl TryFrom<&CommandLineArgs> for RunConfig {
    type Error = anyhow::Error;
    
    fn try_from(args: &CommandLineArgs) -> Result<Self, Self::Error> {
        let mut file_type = InputType::Other;

        if let Some(ftype) = &args.file_type {
            let mut ftype = ftype.clone();
            ftype.make_ascii_lowercase();
            match ftype.as_str() {
                "qasm" => {
                    file_type = InputType::Qasm;
                },
                "txt" => {
                    file_type = InputType::Txt;
                },
                _ => {
                    bail!("unrecognized file_type {:?}, possible values are \"txt\" or \"qasm\".", ftype);
                }
            }
        }

        Ok(Self {
            target_buffer_length: args.target_buffer_length,
            bypass: args.bypass,
            shrink_buffer_after_repeat: args.shrink_buffer_after_repeat,
            full_partitioning: args.full_partitioning,
            big_file: args.big_file,
            num_operations: args.num_operations,
            file_type,
        })
    }
}


impl Default for RunConfig {
    fn default() -> Self {
        Self {
            target_buffer_length: 4096,
            bypass: false,
            shrink_buffer_after_repeat: false,
            full_partitioning: false,
            big_file: false,
            num_operations: None,
            file_type: InputType::default()
        }
    }
}


/// Entry point for running the optimizer normally.
///
/// Checks command line arguments, opens files, then calls [`infer_run`].
fn main() -> anyhow::Result<()> {
    env_logger::Builder::new()
        .filter_level(log::LevelFilter::Info) // default to Info
        .format_timestamp_millis()
        .parse_env("QARROT_LOG_LEVEL")
        .init();

    trace!("logger initialized, parsing args");

    let mut args = CommandLineArgs::parse();

    trace!("8: {}", mem::size_of::<Operation<Basis8>>());
    trace!("16: {}", mem::size_of::<Operation<Basis16>>());
    trace!("32: {}", mem::size_of::<Operation<Basis32>>());
    trace!("64: {}", mem::size_of::<Operation<Basis64>>());
    trace!("128: {}", mem::size_of::<Operation<Basis128>>());
    trace!("256: {}", mem::size_of::<Operation<Basis256>>());

    trace!("read command line arguments");
    debug!("input path:  {:?}", args.input);
    debug!("output path: {:?}", args.output);
    debug!("big file?:   {}", args.big_file);
    debug!("full partitioning algorithm: {}", args.full_partitioning);
    debug!("overwrite output:        {}", args.overwrite);
    debug!("bypass optimization:     {}", args.bypass);
    debug!("decompression algorithm: {:?}", args.decompression_algorithm);
    debug!("test against: {:?}", args.test_against);

    debug!("target buffer length:       {:?}", args.target_buffer_length);
    debug!("shrink buffer after repeat: {:?}", args.shrink_buffer_after_repeat);

    let input_path = if args.input != "STDIN" {
        Some(PathBuf::from(&args.input))
    } else {
        None
    };
    let output_path = PathBuf::from(&args.output);

    trace!("checking arguments");

    if let Some(input_path) = input_path.as_ref() {
        if !input_path.exists() {
            bail!("Input path {:?} does not exist.", input_path);
        } else if !input_path.is_file() {
            bail!("Input path {:?} is not a file.", input_path);
        }
    } else if output_path.exists() && !args.overwrite {
        bail!("Output path {:?} exists and --overwrite was not set.", output_path);
    } else if output_path.exists() && !output_path.is_file() {
        bail!("Output path {:?} exists and --overwrite was set, but the path is not a file.", output_path);
    } else if args.big_file && args.full_partitioning {
        bail!("Cannot use both --full-partitioning and --big-file.");
    } else if args.target_buffer_length > MAX_PREALLOC_OPERATIONS {
        warn!("target buffer length ({}) larger than allowed maximum ({}); setting to maximum.", args.target_buffer_length, MAX_PREALLOC_OPERATIONS);
        args.target_buffer_length = MAX_PREALLOC_OPERATIONS;
    }

    let inferred = if let Some(input_path) = input_path.as_ref() {
        if let Some(ext) = input_path.extension() {
            let str = ext.to_str().unwrap();
            let alg = COMPRESSION_EXTENSION.get(str).copied();
            if let Some(alg) = alg {
                debug!("inferred compression on input: {:?}", alg);
            }
            
            alg
        } else {
            debug!("inferred no compression on input");
            None
        }
    } else {
        None
    };

    let required = if let Some(req) = &args.decompression_algorithm {
        let alg = COMPRESSION_EXTENSION.get(req.as_str()).copied();
        if let Some(alg) = alg {
            debug!("requested compression: {:?}", alg)
        } else {
            bail!("Unknown compression algorithm: {:?}", req);
        }
        alg
    } else {
        None
    };

    if args.compress_output {
        warn!("--compress-output was set, but this is not yet supported")
    }

    let compression = required.or(inferred);
    let mut run_config = RunConfig::try_from(&args)?;

    trace!("checking input file type");

    if run_config.file_type == InputType::Other {
        if let Some(input_path) = input_path.as_ref() {
            if let Some(ext) = input_path.extension() {
                let mut str = String::from(ext.to_str().unwrap());
                str.make_ascii_lowercase();
                match str.as_str() {
                    "qasm" => {
                        run_config.file_type = InputType::Qasm;
                    },
                    "txt" => {
                        run_config.file_type = InputType::Txt;
                    },
                    _ => {}
                }
            }
        }
    }

    trace!("args checked; inferred run configuration: {:?}", run_config);

    if let Some(test_against) = (&args.test_against).as_ref() {
        info!("running comparison");
        if input_path.is_none() {
            bail!("input path needs to be a file for test comparison");
        }
        test_files(&input_path.unwrap(), &test_against, args.big_file);
        return Ok(())
    }

    let output = WriteOutput::new(fs::File::create(output_path)?);
    let input = if let Some(input_path) = &input_path {
        if compression.is_some() {
            Input::new_gzip(input_path)?
        } else {
            Input::new(input_path)?
        }
    } else {
        Input::stdin()?
    };

    match run_config.file_type {
        InputType::Qasm => infer_run_qasm(input, output, run_config)?,
        InputType::Txt => infer_run_txt(input, output, run_config)?,
        InputType::Other => bail!("could not determine file type; specify with --file-type"),
    };

    Ok(())
}

 
/// Trivial wrapper over [`_infer_run_txt`] to call it without a tester callback.
pub fn infer_run_txt(input: impl Read + Debug, output: impl Output, run_config: RunConfig) -> anyhow::Result<usize> {
    _infer_run_txt(input, output, run_config, |_, _, _| {})
}


/// Determines the number of qubits in the circuit, then calls [`run`].
pub fn infer_run_qasm(input: impl Read + Debug, output: impl Output, run_config: RunConfig) -> anyhow::Result<usize> {
    use qasm::lexer::Token;
    let mut seen_openqasm = false;
    let mut n_qubits = None;

    let mut tokens = qasm::lexer::TokenIterator::new(input);

    while let Some(tok) = tokens.next() {
        match tok {
            Token::Version(_) => {
                seen_openqasm = true;
            },
            Token::Include(_) => (),
            Token::QregDecl(_, qubits) => {
                n_qubits = Some(qubits);
                break;
            },
            Token::FixedGate(_, _) => bail!("found OpenQASM gate before a qreg declaration"),
        }
    }

    if !seen_openqasm {
        bail!("missing OpenQASM version declaration");
    }

    let n_qubits = n_qubits.unwrap();

    let basis_size = BasisSize::from_size(n_qubits);

    macro_rules! run_with_basis_size {
        ($basis:ty) => {{
            info!("circuit has {} qubits; using basis size {}", n_qubits, basis_size.bits());

            let parser = qasm::parser::InstructionIterator::<_, $basis>::new(n_qubits, tokens, run_config.target_buffer_length)?;

            if run_config.big_file {
                run::<_, _, FileOptimizer<_, _>>(output, parser, n_qubits, run_config)
            } else {
                run::<_, _, InMemoryOptimizer<_>>(output, parser, n_qubits, run_config)
            }
        }}
    }

    match basis_size {
        BasisSize::Basis8 => run_with_basis_size!(Basis8),
        BasisSize::Basis16 => run_with_basis_size!(Basis16),
        BasisSize::Basis32 => run_with_basis_size!(Basis32),
        BasisSize::Basis64 => run_with_basis_size!(Basis64),
        BasisSize::Basis128 => run_with_basis_size!(Basis128),
        BasisSize::Basis256 => run_with_basis_size!(Basis256),
        BasisSize::BasisDyn => {
            warn!("using fallback dynamically sized basis ({} qubits too large for largest static basis, {}). this will be significantly slower than using statically sized bases.", n_qubits, basis::LARGEST_STATIC_BASIS);
            if run_config.big_file {
                warn!("using both big file support and dynamically sized basis likely has no benefit; recommend asking the qarrot team to add a larger static basis.");
            }
            run_with_basis_size!(DBasis)
        },
    }
}


/// Determines the number of qubits in the circuit, then calls [`run`].
///
/// Has a callback parameter for testing. This is called after pulling the one or two lines
/// (depending on whether the first line of the circuit is a repeat).
fn _infer_run_txt<K: Fn(usize, Option<usize>, BasisSize)>(input: impl Read + Debug, output: impl Output, run_config: RunConfig, testing_callback: K) -> anyhow::Result<usize> {
    trace!("running input size inference");
    let mut tokenizer = TokenIterator::new(input);

    // need to determine appropriate basis size
    // so, we'll read one or two lines
    // - one if the first line is an operation
    // - two if the first line is a repeat
    // if there are zero lines we just 
    let mut preread_tokens = Vec::with_capacity(128);
    tokenizer.pop_line(&mut preread_tokens)?;

    let mut repeat = None;
    if let Some(Token::Repeat(n)) = preread_tokens.first() {
        debug!("preread a repeat ({})", n);
        debug_assert!(preread_tokens.len() == 1);
        repeat = Some(*n as usize);
        preread_tokens.clear();

        tokenizer.pop_line(&mut preread_tokens)?;
        
        if preread_tokens.is_empty() {
            bail!("Unexpected end of file while inferring number of qubits");
        }

        if matches!(preread_tokens[0], Token::Measure(_)) {
            bail!("Nested repeat found at start of file");
        }

        if matches!(preread_tokens[0], Token::End) {
            bail!("Empty repeat found at start of file")
        }
    }

    if preread_tokens.is_empty() {
        bail!("Empty input file, cannot infer number of qubits.");
    }

    debug!("preread {} tokens", preread_tokens.len());

    let n_qubits = preread_tokens.len() - 1;

    let basis_size = BasisSize::from_size(n_qubits);

    // for testing
    testing_callback(n_qubits, repeat, basis_size);

    macro_rules! run_with_basis_size {
        ($basis:ty) => {
            {let op = complete_op::<$basis>(n_qubits, &preread_tokens)
                .with_context(|| format!("while building prepended operation ({} bits)", basis_size.bits()))?;
            info!("circuit has {} qubits; using basis size {}", n_qubits, basis_size.bits());
            debug!("preread operation: {:?}", op);
            debug!("preread repeat: {:?}", repeat);

            let mut parser = InstructionIterator::<_, $basis>::new(n_qubits, tokenizer, run_config.target_buffer_length, run_config.shrink_buffer_after_repeat);
            if let Some(repeat) = repeat {
                debug!("prepending repeat and operation");
                parser.prepend_repeat(repeat, op.clone())?;
            } else {
                debug!("prepending operation");
                parser.prepend_op(op.clone());
            }

            if run_config.big_file {
                run::<_, _, FileOptimizer<_, _>>(output, parser, n_qubits, run_config)
            } else {
                run::<_, _, InMemoryOptimizer<_>>(output, parser, n_qubits, run_config)
            }
        }
        };
    }

    match basis_size {
        BasisSize::Basis8 => run_with_basis_size!(Basis8),
        BasisSize::Basis16 => run_with_basis_size!(Basis16),
        BasisSize::Basis32 => run_with_basis_size!(Basis32),
        BasisSize::Basis64 => run_with_basis_size!(Basis64),
        BasisSize::Basis128 => run_with_basis_size!(Basis128),
        BasisSize::Basis256 => run_with_basis_size!(Basis256),
        BasisSize::BasisDyn => {
            warn!("using fallback dynamically sized basis ({} qubits too large for largest static basis, {}). this will be significantly slower than using statically sized bases.", n_qubits, basis::LARGEST_STATIC_BASIS);
            if run_config.big_file {
                warn!("using both big file support and dynamically sized basis likely has no benefit; recommend asking the qarrot team to add a larger static basis.");
            }
            run_with_basis_size!(DBasis)
        },
    }
}


/// Prints the circuit to `STDERR`.
#[allow(dead_code)]
fn debug_out_circuit<B: Basis>(circuit: &[Operation<B>], n_qubits: usize) {
    let mut buf = String::new();
    for op in circuit {
        fmt_operation(&mut buf, n_qubits, op).unwrap();
        eprint!("{}", buf);
    }
}


/// Main body of the optimization algorithm.
///
/// 1. Builds a parser using the lexer, optionally prepending an operation and a repeat statement.
/// 2. Then, loads the whole circuit (currently; this should be changed, at least for large files).
/// 3. If run in bypass mode, write this circuit to the output then exit.
/// 4. 
pub fn run<B: Basis, Ops: Iterator<Item = Operation<B>> + Debug, Opt: Optimizer<B, Ops>>(mut output: impl Output, mut parser: Ops, n_qubits: usize, run_config: RunConfig) -> anyhow::Result<usize> {
    trace!("beginning run");
    let size_of_operation = mem::size_of::<Operation<B>>();
    debug!("size_of operation: {}", size_of_operation);
    let pre_parse = std::time::Instant::now();

    info!("reading circuit and running initial reduction…");

    if run_config.bypass {
        info!("running in bypass mode; writing output");
        while let Some(op) = parser.next() {
            output.write_operation(n_qubits, &op)?;
        }
        output.flush()?;

        return Ok(n_qubits);
    }

    // let mut optimizer = InMemoryOptimizer::new(n_qubits, parser, &run_config)?;
    let mut optimizer = Opt::new(n_qubits, parser, &run_config)?;

    let initial_circuit_length = optimizer.initial_circuit_length();

    let (alloc, used) = optimizer.current_heap_usage();
    debug!("circuit using {} ({} allocated) bytes of heap", used, alloc);

    let start_time = std::time::Instant::now();
    let duration_reduce_rotations = start_time.duration_since(pre_parse);
    if initial_circuit_length.is_none() {
        info!("initialized optimizer in {:?}", duration_reduce_rotations);
    } else {
        info!("initial reduction pass done in {:?}; reduced from {:?} to {:?} operations.", duration_reduce_rotations, initial_circuit_length.unwrap(), optimizer.post_reduction_length().unwrap());
    }

    let mut needs_more_rounds = true;
    let mut rounds = 0usize;

    let mut duration_t_forward = std::time::Duration::from_nanos(0);
    let mut duration_partition = std::time::Duration::from_nanos(0);

    while needs_more_rounds {
        let round = rounds + 1;
        info!("beginning round {}; pushing T gates forward…", round);

        let t0 = std::time::Instant::now();
        needs_more_rounds = false;

        let (_changed, _t_gate_count) = optimizer.push_t_forward().context("while pushing T gates forward")?;

        let t1 = std::time::Instant::now();
        duration_t_forward += t1.duration_since(t0);
        let t_forward_time = t1.duration_since(t0);
        if let Some(stats) = optimizer.latest_stats() {
            info!("pushed T gates forward in {:?}. currently {} operations ({} t gates). partitioning ({})…", t_forward_time, stats.total_operations, stats.t_gates, if run_config.full_partitioning { "full" } else { "fast approximate" });
        } else {
            info!("pushed T gates forward in {:?}. partitioning ({})…", t_forward_time, if run_config.full_partitioning { "full" } else { "fast approximate" });
        }

        // reduce t gate layer
        let (changed, stats) = optimizer.partition().context("while partitioning")?;
        needs_more_rounds |= changed;

        let t2 = std::time::Instant::now();
        info!("partitioned gates in {:?}. currently {} total operations, {} t gates", t2.duration_since(t1), stats.total_operations, stats.t_gates);
        duration_partition += t2.duration_since(t1);

        rounds += 1;
    }

    let final_stats = optimizer.latest_stats().unwrap();
    let final_time = std::time::Instant::now();
    let final_t_gates = final_stats.t_gates;
    let duration_total = final_time.duration_since(start_time);
    info!("finished optimizing circuit from {} operations (final T count: {}) after {} rounds, taking {:?} ({:?} pushing T gates forward, {:?} partitioning).", optimizer.initial_circuit_length().unwrap() , final_t_gates, rounds, duration_total, duration_t_forward, duration_partition);

    info!("saving optimized circuit…");
    optimizer.write_to_output(output)?;

    trace!("done, exiting");
    Ok(n_qubits)
}


fn test_files(in_path: &Path, cmp_path: &Path, big_file: bool) {
    dbg!(&in_path);
    dbg!(&cmp_path);
    
    let in_file = fs::File::open(&in_path).unwrap();

    let cmp: Box<dyn Read>;
    let cmp_file = io::BufReader::new(fs::File::open(&cmp_path).unwrap());
    if let Some(_) = cmp_path.extension().and_then(|ostr| ostr.to_str()).and_then(|ext| COMPRESSION_EXTENSION.get(ext)) {
        cmp = Box::new(GzDecoder::new(cmp_file));
    } else {
        cmp = Box::new(cmp_file);
    }

    let mut this_output = String::with_capacity(16384);
    let output = StringOut::new(&mut this_output);
    let n_qubits;
    let cfg = RunConfig {
        full_partitioning: true,
        big_file,
        ..Default::default()
    };
    if let Some(_) = in_path.extension().and_then(|ostr| ostr.to_str()).and_then(|ext| COMPRESSION_EXTENSION.get(ext)) {
        n_qubits = infer_run_txt(GzDecoder::new(in_file), output, cfg).unwrap();
    } else {
        n_qubits = infer_run_txt(in_file, output, cfg).unwrap();
    }

    let mut tester: Tester<'_, _, Basis128> = Tester::new(cmp, this_output.as_bytes(), n_qubits);
    tester.test_all();
}





#[allow(dead_code)]
fn test_files_with_basis<B: Basis>(n_qubits: usize, in_path: &Path, cmp_path: &Path) {
    dbg!(&in_path);
    dbg!(&cmp_path);
    
    let in_file = fs::File::open(&in_path).unwrap();

    let cmp: Box<dyn Read>;
    let cmp_file = io::BufReader::new(fs::File::open(&cmp_path).unwrap());
    if let Some(_) = cmp_path.extension().and_then(|ostr| ostr.to_str()).and_then(|ext| COMPRESSION_EXTENSION.get(ext)) {
        cmp = Box::new(GzDecoder::new(cmp_file));
    } else {
        cmp = Box::new(cmp_file);
    }

    let mut this_output = String::with_capacity(16384);
    let output = StringOut::new(&mut this_output);
    let final_output;
    let cfg = RunConfig {
        full_partitioning: true,
        ..Default::default()
    };

    if let Some(_) = in_path.extension().and_then(|ostr| ostr.to_str()).and_then(|ext| COMPRESSION_EXTENSION.get(ext)) {
        let tokens = TokenIterator::new(GzDecoder::new(in_file));
        let parser = InstructionIterator::<_, B>::new(n_qubits, tokens, cfg.target_buffer_length, cfg.shrink_buffer_after_repeat);
        final_output = run::<B, _, InMemoryOptimizer<_>>(output, parser, n_qubits, cfg).unwrap();
    } else {
        let tokens = TokenIterator::new(in_file);
        let parser = InstructionIterator::<_, B>::new(n_qubits, tokens, cfg.target_buffer_length, cfg.shrink_buffer_after_repeat);
        final_output = run::<B, _, InMemoryOptimizer<_>>(output, parser, n_qubits, cfg).unwrap();
    }

    let n_qubits = final_output;

    assert!(n_qubits <= 256);

    let mut tester: Tester<'_, _, Basis256> = Tester::new(cmp, this_output.as_bytes(), n_qubits);
    tester.test_all();
}


#[cfg(test)]
mod tests {
    use std::path::PathBuf;

    use self::output::Void;

    use super::*;

    #[test]
    fn test_infer_norepeat() {
        let src = "Rotate 2: IXYZ\nMeasure +: IXYZ";
        let cfg = RunConfig {
            full_partitioning: true,
            ..Default::default()
        };
        _infer_run_txt(src.as_bytes(), Void {}, cfg, |n_qubits, repeat, basis| {
            assert_eq!(n_qubits, 4);
            assert_eq!(repeat, None);
            assert_eq!(basis, BasisSize::Basis8);
        }).unwrap();
    }

    #[test]
    fn test_infer_repeat() {
        let src = "Repeat 2\nRotate 2: IXYZ\nMeasure +: IXYZ\nEnd";
        let cfg = RunConfig {
            full_partitioning: true,
            ..Default::default()
        };
        _infer_run_txt(src.as_bytes(), Void {}, cfg, |n_qubits, repeat, basis| {
            assert_eq!(n_qubits, 4);
            assert_eq!(repeat, Some(2));
            assert_eq!(basis, BasisSize::Basis8);
        }).unwrap();
    }

    fn test_files_qasm(in_path: &Path, cmp_path: &Path, big_file: bool) {
        dbg!(&in_path);
        dbg!(&cmp_path);
        
        let in_file = fs::File::open(&in_path).unwrap();

        let cmp: Box<dyn Read>;
        let cmp_file = io::BufReader::new(fs::File::open(&cmp_path).unwrap());
        if let Some(_) = cmp_path.extension().and_then(|ostr| ostr.to_str()).and_then(|ext| COMPRESSION_EXTENSION.get(ext)) {
            cmp = Box::new(GzDecoder::new(cmp_file));
        } else {
            cmp = Box::new(cmp_file);
        }

        let mut this_output = String::with_capacity(16384);
        let output = StringOut::new(&mut this_output);
        let n_qubits;
        let cfg = RunConfig {
            full_partitioning: true,
            big_file,
            ..Default::default()
        };

        n_qubits = infer_run_qasm(in_file, output, cfg).unwrap();

        let mut tester: Tester<'_, _, Basis128> = Tester::new(cmp, this_output.as_bytes(), n_qubits);
        tester.test_all();
    }

    fn test_file_qasm(filename: &str) {
        let mut inf = String::from(filename);
        inf.push_str(".qasm");
        let mut in_path = PathBuf::from("./test_circuits/qasm");
        in_path.push(&inf);

        let mut outf = String::from(filename);
        outf.push_str(".txt");
        let mut cmp_path = PathBuf::from("./test_circuits/expected");
        cmp_path.push(&outf);

        test_files_qasm(&in_path, &cmp_path, false);
    }
    
    fn test_file(filename: &str) {
        let mut in_path = PathBuf::from("./test_circuits/input");
        in_path.push(filename);

        let mut cmp_path = PathBuf::from("./test_circuits/expected");
        cmp_path.push(filename);

        test_files(&in_path, &cmp_path, false);
        // test_files(&in_path, &cmp_path, true);
    }

    fn test_file_with_basis<B: Basis>(filename: &str, n_qubits: usize) {
        let mut in_path = PathBuf::from("./test_circuits/input");
        in_path.push(filename);

        let mut cmp_path = PathBuf::from("./test_circuits/expected");
        cmp_path.push(filename);

        test_files_with_basis::<B>(n_qubits, &in_path, &cmp_path);
    }

    fn test_bigfile<B: Basis>(filename: &str, n_qubits: usize) {
        let mut in_path = PathBuf::from("./test_circuits/input");
        in_path.push(filename);
        let src = fs::read_to_string(&in_path).unwrap();

        let mut in_mem_output = String::with_capacity(16384);
        let output = StringOut::new(&mut in_mem_output);
        
        let cfg = RunConfig {
            full_partitioning: false,
            big_file: false,
            ..Default::default()
        };
    
        if let Some(_) = in_path.extension().and_then(|ostr| ostr.to_str()).and_then(|ext| COMPRESSION_EXTENSION.get(ext)) {
            let tokens = TokenIterator::new(GzDecoder::new(src.as_bytes()));
            let parser = InstructionIterator::<_, B>::new(n_qubits, tokens, cfg.target_buffer_length, cfg.shrink_buffer_after_repeat);
            run::<B, _, InMemoryOptimizer<_>>(output, parser, n_qubits, cfg).unwrap();
        } else {
            let tokens = TokenIterator::new(src.as_bytes());
            let parser = InstructionIterator::<_, B>::new(n_qubits, tokens, cfg.target_buffer_length, cfg.shrink_buffer_after_repeat);
            run::<B, _, InMemoryOptimizer<_>>(output, parser, n_qubits, cfg).unwrap();
        }

        let mut big_file_output = String::with_capacity(16384);
        let output = StringOut::new(&mut big_file_output);

        let cfg = RunConfig {
            full_partitioning: false,
            big_file: true,
            ..Default::default()
        };

        assert!(n_qubits <= 256);

        if let Some(_) = in_path.extension().and_then(|ostr| ostr.to_str()).and_then(|ext| COMPRESSION_EXTENSION.get(ext)) {
            let tokens = TokenIterator::new(GzDecoder::new(src.as_bytes()));
            let parser = InstructionIterator::<_, B>::new(n_qubits, tokens, cfg.target_buffer_length, cfg.shrink_buffer_after_repeat);
            run::<B, _, InMemoryOptimizer<_>>(output, parser, n_qubits, cfg).unwrap();
        } else {
            let tokens = TokenIterator::new(src.as_bytes());
            let parser = InstructionIterator::<_, B>::new(n_qubits, tokens, cfg.target_buffer_length, cfg.shrink_buffer_after_repeat);
            run::<B, _, InMemoryOptimizer<_>>(output, parser, n_qubits, cfg,).unwrap();
        }

        let mut tester: Tester<'_, _, Basis256> = Tester::new(in_mem_output.as_bytes(), big_file_output.as_bytes(), n_qubits);
        tester.test_all();

    }

    #[test]
    fn test_h() {
        test_file("h.txt");
    }

    #[test]
    fn test_h_bigfile() {
        test_bigfile::<Basis8>("h.txt", 1);
        test_bigfile::<Basis16>("h.txt", 1);
    }

    #[test]
    fn test_h_16() {
        test_file_with_basis::<Basis16>("h.txt", 1);
    }

    #[test]
    fn test_h_32() {
        test_file_with_basis::<Basis32>("h.txt", 1);
    }

    #[test]
    fn test_h_64() {
        test_file_with_basis::<Basis64>("h.txt", 1);
    }

    #[test]
    fn test_h_128() {
        test_file_with_basis::<Basis128>("h.txt", 1);
    }

    #[test]
    fn test_h_256() {
        test_file_with_basis::<Basis256>("h.txt", 1);
    }

    #[test]
    fn test_h_dyn() {
        test_file_with_basis::<DBasis>("h.txt", 1);
    }

    #[test]
    fn test_y() {
        test_file("y.txt");
    }

    #[test]
    fn test_y_bigfile() {
        test_bigfile::<Basis8>("y.txt", 1);
        test_bigfile::<Basis32>("y.txt", 1);
    }

    #[test]
    fn test_x() {
        test_file("x.txt");
    }

    #[test]
    fn test_cx() {
        test_file("cx.txt");
    }

    #[test]
    fn test_inverse_1() {
        test_file("min4.txt");
    }

    #[test]
    fn test_inverse_1_bigfile() {
        test_bigfile::<Basis8>("min4.txt", 2);
        test_bigfile::<Basis32>("min4.txt", 2);
    }

    #[test]
    fn test_10_lines_with_rz() {
        test_file("qasm_test_10_lines_with_rz.txt");
    }

    #[test]
    fn test_10_lines_with_rz_bigfile() {
        test_bigfile::<Basis8>("qasm_test_10_lines_with_rz.txt", 3);
        test_bigfile::<Basis32>("qasm_test_10_lines_with_rz.txt", 3);
    }

    #[test]
    fn test_10_lines() {
        test_file("qasm_test_10.txt");
    }

    #[test]
    fn test_10_lines_bigfile() {
        test_bigfile::<Basis8>("qasm_test_10.txt", 3);
        test_bigfile::<Basis64>("qasm_test_10.txt", 3);
    }

    #[test]
    fn test_50_lines() {
        test_file("qasm_test_50.txt");
    }

    #[test]
    fn test_50_lines_bigfile() {
        test_bigfile::<Basis8>("qasm_test_50.txt", 5);
        test_bigfile::<Basis128>("qasm_test_50.txt", 5);
    }

    #[test]
    fn test_100_lines() {
        test_file("q100.txt");
    }

    #[test]
    fn test_100_lines_bigfile() {
        test_bigfile::<Basis8>("q100.txt", 7);
        test_bigfile::<Basis256>("q100.txt", 7);
    }

    #[test]
    fn test_500_lines() {
        test_file("q500.txt");
    }

    #[test]
    fn test_500_lines_bigfile() {
        test_bigfile::<Basis16>("q500.txt", 15);
        test_bigfile::<Basis256>("q500.txt", 15);
    }

    #[test]
    fn test_p1() {
        test_file("p1.txt");
    }

    #[test]
    fn test_p1_16() {
        test_file_with_basis::<Basis16>("p1.txt", 3);
    }

    #[test]
    fn test_p1_32() {
        test_file_with_basis::<Basis32>("p1.txt", 3);
    }

    #[test]
    fn test_p1_64() {
        test_file_with_basis::<Basis64>("p1.txt", 3);
    }

    #[test]
    fn test_p1_128() {
        test_file_with_basis::<Basis128>("p1.txt", 3);
    }

    #[test]
    fn test_p1_256() {
        test_file_with_basis::<Basis256>("p1.txt", 3);
    }

    #[test]
    fn test_p1_dyn() {
        test_file_with_basis::<DBasis>("p1.txt", 3);
    }

    #[test]
    fn test_p2() {
        test_file("p2.txt");
    }

    #[test]
    fn test_p2_16() {
        test_file_with_basis::<Basis16>("p2.txt", 5);
    }

    #[test]
    fn test_p2_32() {
        test_file_with_basis::<Basis32>("p2.txt", 5);
    }

    #[test]
    fn test_p2_64() {
        test_file_with_basis::<Basis64>("p2.txt", 5);
    }

    #[test]
    fn test_p2_128() {
        test_file_with_basis::<Basis128>("p2.txt", 5);
    }

    #[test]
    fn test_p2_256() {
        test_file_with_basis::<Basis256>("p2.txt", 5);
    }

    #[test]
    fn test_p2_dyn() {
        test_file_with_basis::<DBasis>("p2.txt", 5);
    }

    #[test]
    fn test_p2c() {
        test_file("p2c.txt");
    }
    
    #[test]
    fn test_p2c_16() {
        test_file_with_basis::<Basis16>("p2c.txt", 3);
    }

    #[test]
    fn test_p2c_32() {
        test_file_with_basis::<Basis32>("p2c.txt", 3);
    }

    #[test]
    fn test_p2c_64() {
        test_file_with_basis::<Basis64>("p2c.txt", 3);
    }

    #[test]
    fn test_p2c_128() {
        test_file_with_basis::<Basis128>("p2c.txt", 3);
    }

    #[test]
    fn test_p2c_256() {
        test_file_with_basis::<Basis256>("p2c.txt", 3);
    }

    #[test]
    fn test_p2c_dyn() {
        test_file_with_basis::<DBasis>("p2c.txt", 3);
    }

    #[test]
    fn test_p3() {
        test_file("p3.txt");
    }

    #[test]
    fn test_p_3_16() {
        test_file_with_basis::<Basis16>("p3.txt", 4);
    }

    #[test]
    fn test_p_3_32() {
        test_file_with_basis::<Basis32>("p3.txt", 4);
    }

    #[test]
    fn test_p_3_64() {
        test_file_with_basis::<Basis64>("p3.txt", 4);
    }

    #[test]
    fn test_p_3_128() {
        test_file_with_basis::<Basis128>("p3.txt", 4);
    }

    #[test]
    fn test_p_3_256() {
        test_file_with_basis::<Basis256>("p3.txt", 4);
    }

    #[test]
    fn test_p_3_dyn() {
        test_file_with_basis::<DBasis>("p3.txt", 4);
    }

    #[test]
    fn test_p4() {
        test_file("p4.txt");
    }

    #[test]
    fn test_p6() {
        test_file("p6.txt");
    }

    #[test]
    fn test_1000_lines() {
        test_file("qasm_test_1000.txt");
    }

    #[test]
    fn test_1000_lines_32() {
        test_file_with_basis::<Basis32>("qasm_test_1000.txt", 15);
    }

    #[test]
    fn test_1000_lines_64() {
        test_file_with_basis::<Basis64>("qasm_test_1000.txt", 15);
    }

    #[test]
    fn test_1000_lines_128() {
        test_file_with_basis::<Basis128>("qasm_test_1000.txt", 15);
    }

    #[test]
    fn test_1000_lines_256() {
        test_file_with_basis::<Basis256>("qasm_test_1000.txt", 15);
    }

    #[test]
    fn test_1000_lines_dyn() {
        test_file_with_basis::<DBasis>("qasm_test_1000.txt", 15);
    }

    #[test]
    fn test_5000_lines() {
        test_file("qasm_test_5000.txt");
    }

    #[test]
    fn test_10000_lines() {
        test_file("qasm_test_10000.txt");
    }

    #[test]
    fn test_100000_lines() {
        test_file("qasm_test_10000.txt");
    }

    #[test]
    fn test_mol_hh() {
        test_file("molHH.txt");
    }

    #[test]
    fn test_mol_hh_bigfile() {
        test_bigfile::<Basis8>("molHH.txt", 4);
    }

    // #[test]
    // fn qasm_test_10_qasm() {
    //     test_file_qasm("qasm_test_10");
    // }
}
