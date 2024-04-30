# QArROT Optimzier

To build: `cargo build --release` (leave off `--release` for debug build).

To run: `cargo run --release -- {args here}`, see invocation with `cargo run -- --help` (output below):

```
Usage: qarrot-optimizer [OPTIONS] --input <INPUT> --output <OUTPUT>

Options:
  -i, --input <INPUT>
          Input path
  -o, --output <OUTPUT>
          Output path
  -t, --target-buffer-length <TARGET_BUFFER_LENGTH>
          Target buffer length [default: 4096]
  -s, --shrink-buffer-after-repeat
          Shrink buffer after repeat (possibly reduce non-peak memory usage at the cost of more allocations)
      --overwrite
          Overwrite existing output path
      --bypass
          Bypass optimization (testing use only)
      --decompression-algorithm <DECOMPRESSION_ALGORITHM>
          Force a particular decompression method (usually determined by extension)
  -c, --compress-output
          GZip compress the output
  -f, --full-partitioning
          Full partitioning (much slower, but may slightly decrease final gate count)
      --test-against <TEST_AGAINST>
          Test against reference
  -h, --help
          Print help
```

The executable is in the `target` folder after building (see above). The path will depend on whether a release or debug build is done, but will be `target/{release,debug}/qarrot-optimizer`. Note that by default builds are not portable, so they may not work when transferred to another computer of the same CPU architecture. Comment out the file `.cargo/config.toml` if you need a portable bit, but note that this possibly comes at the cost of performance.

By default, the log level is set to `info`, but can be set to (in descending order of verbosity) `trace`, `debug`, `info`, `warn`, `error`. This is done using the `QARROT_LOG_LEVEL` environment variable, so e.g.

```bash
QARROT_LOG_LEVEL=debug cargo run --release -- --input test_circuits/input/q500.txt --output foo.txt --overwrite
```
