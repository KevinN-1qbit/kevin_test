use std::io;

use crate::{basis::Basis, operation::{phase::Phase, Operation}};


pub trait Output {
    fn flush(&mut self) -> anyhow::Result<()>;
    fn write_operation<B: Basis>(&mut self, n_qubits: usize, operation: &Operation<B>) -> anyhow::Result<()>;
}


pub fn fmt_operation<B: Basis>(buf: &mut String, n_qubits: usize, operation: &Operation<B>) -> anyhow::Result<()> {
    use std::fmt::Write;

    buf.clear();
    match operation.kind {
        crate::operation::OperationKind::Nop => unreachable!(),
        crate::operation::OperationKind::Measurement { phase } => {
            buf.write_str("Measure ")?;
            match phase {
                Phase::Positive => buf.write_char('+'),
                Phase::Negative => buf.write_char('-'),
            }?;
        },
        crate::operation::OperationKind::Rotation { angle } => {
            let angle_code = angle as i8;
            buf.write_fmt(format_args!("Rotate {}", angle_code))?;
        },
    };

    buf.write_str(": ")?;

    // TODO: make this more efficient
    for q in 0..n_qubits {
        let x = operation.x.get_bit(q);
        let z = operation.z.get_bit(q);
        match (x, z) {
            (false, false) => buf.write_char('I')?,
            (true, false) => buf.write_char('X')?,
            (false, true) => buf.write_char('Z')?,
            (true, true) => buf.write_char('Y')?,
        };
    }

    buf.write_char('\n')?;

    Ok(())
}


// throw away writes, useful for testing
#[derive(Debug)]
pub struct Void { }


impl io::Write for Void {
    fn write(&mut self, buf: &[u8]) -> std::io::Result<usize> {
        Ok(buf.len())
    }

    fn flush(&mut self) -> std::io::Result<()> {
        Ok(())
    }
}


impl Output for Void {
    fn flush(&mut self) -> anyhow::Result<()> {
        Ok(())
    }

    fn write_operation<B: Basis>(&mut self, _n_qubits: usize, _operation: &Operation<B>) -> anyhow::Result<()> {
        Ok(())
    }
}


#[derive(Debug)]
pub struct StringOut<'a> {
    single: String,
    pub output: &'a mut String,
}

impl<'a> StringOut<'a> {
    pub fn new(output: &'a mut String) -> Self {
        Self {
            single: String::with_capacity(128),
            output,
        }
    }
}

impl<'a> Output for StringOut<'a> {
    fn flush(&mut self) -> anyhow::Result<()> {
        Ok(())
    }

    fn write_operation<B: Basis>(&mut self, n_qubits: usize, operation: &Operation<B>) -> anyhow::Result<()> {
        fmt_operation(&mut self.single, n_qubits, operation)?;
        for char in self.single.chars() {
            self.output.push(char);
        }
        Ok(())
    }
}


#[derive(Debug)]
pub struct WriteOutput<W: io::Write> {
    writer: io::BufWriter<W>, // Write tries to flush on drop, we don't need to impl that manually
    line_buf: String,
}


impl<W: io::Write> WriteOutput<W> {
    pub fn new(writer: W) -> Self {
        Self {
            writer: io::BufWriter::new(writer),
            line_buf: String::with_capacity(256),
        }
    }
}

impl<W: io::Write> Output for WriteOutput<W> {
    fn flush(&mut self) -> anyhow::Result<()> {
        use io::Write;
        self.writer.flush()?;
        Ok(())
    }

    fn write_operation<B: Basis>(&mut self, n_qubits: usize, operation: &Operation<B>) -> anyhow::Result<()> {
        use io::Write;
        
        fmt_operation(&mut self.line_buf, n_qubits, operation)?;

        let amount = self.writer.write(self.line_buf.as_bytes())?;
        debug_assert!(amount == self.line_buf.as_bytes().len());
        Ok(())
    }
}
