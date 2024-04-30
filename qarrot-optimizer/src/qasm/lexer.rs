use std::{io::{Read, BufRead, BufReader}, collections::VecDeque};
use lazy_static::lazy_static;
use regex::Regex;
use anyhow::{bail, Context};


#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FixedGate {
    H,
    T,
    Tdg,
    S,
    Sdg,
    X,
    Y,
    Z,
    Cx,
}


impl TryFrom<&str> for FixedGate {
    type Error = String;

    fn try_from(value: &str) -> Result<Self, Self::Error> {
        match value {
            "h" => Ok(Self::H),
            "t" => Ok(Self::T),
            "tdg" => Ok(Self::Tdg),
            "s" => Ok(Self::S),
            "sdg" => Ok(Self::Sdg),
            "x" => Ok(Self::X),
            "y" => Ok(Self::Y),
            "z" => Ok(Self::Z),
            "cx" => Ok(Self::Cx),
            _ => Err(String::from(value)),
        }
    }
}


#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Token {
    Version(i8),
    Include(String),
    QregDecl(String, usize),
    FixedGate(FixedGate, Vec<usize>),
}


#[derive(Debug)]
pub struct TokenIterator<R: Read> {
    source: BufReader<R>,
    token_buf: VecDeque<Token>,
    line_buf: String,
    line_count: usize,
}


impl<R: Read> TokenIterator<R> {
    pub fn new(source: R) -> Self {
        Self {
            source: BufReader::new(source),
            token_buf: VecDeque::with_capacity(128),
            line_buf: String::with_capacity(128),
            line_count: 0,
        }
    }
}

lazy_static! {
    static ref VERSION: Regex = {
        Regex::new(r"^\s*OPENQASM\s+(?<version_number_major>\d+).(?<version_number_minor>\d+)\s*;\s*$").unwrap()
    };

    static ref INCLUDE: Regex = {
        Regex::new(r#"^\s*include\s+"(?<filename>\w+.\w+)"\s*;\s*$"#).unwrap()
    };

    static ref QREGDECL: Regex = {
        Regex::new(r"^\s*qreg\s+(?<name>\w+)\[(?<size>\d+)\]\s*;\s*$").unwrap()
    };

    static ref CREGDECL: Regex = {
        Regex::new(r"^\s*creg\s+(?<name>\w+)\[(?<size>\d+)\]\s*;\s*$").unwrap()
    };

    static ref FIXEDGATE: Regex = {
        Regex::new(r"^\s*(?<gate>\w+)\s+(?<qreg>(\w+(\[\d+\])?)(,\s*\w+(\[\d+\])?)*)\s*;\s*$").unwrap()
    };

    static ref SEPARATOR: Regex = {
        Regex::new(r",\s*").unwrap()
    };

    static ref QREG_CAPTURE: Regex = {
        Regex::new(r"(?<qreg_name>\w+)\[(?<index>\d+)\]").unwrap()
    };
} 


fn qregs(value: &str) -> anyhow::Result<Vec<usize>> {
    let qregs_iter = SEPARATOR.split(value).into_iter();
    let mut idxs = Vec::with_capacity(2);
    for reg in qregs_iter {
        if let Some(m) = QREG_CAPTURE.captures(reg) {
            let idx: usize = m["index"].parse().with_context(|| format!("Invalid quantum registers {}')", value))?;
            idxs.push(idx);
        } else {
            bail!("could not interpret {} as quantum registers", value)
        }
    }

    Ok(idxs)
}


impl<R: Read> TokenIterator<R> {
    fn pop(&mut self) -> anyhow::Result<Option<Token>> {
        if let Some(tok) = self.token_buf.pop_front() {
            return Ok(Some(tok));
        }

        self.fill_token_buf().context("while popping next token")?;

        // return the first token we just added
        // if there aren't any we're done iterating
        // (this is why we use a deque and not a vec)
        Ok(self.token_buf.pop_front())
    }


    fn fill_token_buf(&mut self) -> anyhow::Result<()>{
        // read lines until one is nonempty
        loop {
            self.line_count += 1;
            self.line_buf.clear();
            let len = self.source.read_line(&mut self.line_buf)?;

            if len == 0 {
                // EOF
                return Ok(());
            }

            if self.line_buf.chars().any(|ch| !ch.is_ascii_whitespace()) {
                break;
            }
        }

        // otherwise, fill the token buffer

        if let Some(m) = VERSION.captures(&self.line_buf) {
            let version: i8 = m["version_number_major"].parse().with_context(|| format!("Invalid version number on line {} ('{}')", self.line_count, self.line_buf))?;
            self.token_buf.push_back(Token::Version(version));
        } else if let Some(m) = INCLUDE.captures(&self.line_buf) {
            let filename: String = String::from(&m["filename"]);
            self.token_buf.push_back(Token::Include(filename))
        } else if let Some(m) = QREGDECL.captures(&self.line_buf) {
            let size: usize = m["size"].parse().with_context(|| format!("Invalid qreg size on line {} ('{}')", self.line_count, self.line_buf))?;
            let name: String = String::from(&m["name"]);
            self.token_buf.push_back(Token::QregDecl(name, size));
        } else if let Some(_) = CREGDECL.captures(&self.line_buf) {
            self.fill_token_buf()?;
        } else if let Some(m) = FIXEDGATE.captures(&self.line_buf) {
            let gate_type = FixedGate::try_from(&m["gate"]).unwrap();
            let qregs = qregs(&m["qreg"]).unwrap();
            let token = Token::FixedGate(gate_type, qregs);
            self.token_buf.push_back(token);
        } else {
            bail!("Did not recognize line {} ('{}')", self.line_count, self.line_buf);
        }

        Ok(())
    }

    pub fn pop_line(&mut self, buf: &mut Vec<Token>) -> anyhow::Result<()> {
        if self.token_buf.is_empty() {
            self.fill_token_buf()?;
        }
        while let Some(front) = self.token_buf.pop_front() {
            buf.push(front);
        }
        Ok(())
    }

    pub fn peek(&mut self) -> anyhow::Result<Option<&Token>> {
        if self.token_buf.is_empty() {
            self.fill_token_buf()?;
        }

        Ok(self.token_buf.front())
    }
}


impl<R: Read> Iterator for TokenIterator<R> {
    type Item = Token;

    fn next(&mut self) -> Option<Self::Item> {
        self.pop().unwrap()
    }
}


#[cfg(test)]
mod tests {
    use super::*;

    fn tokens(src: &str) -> Vec<Token> {
        let lexer = TokenIterator::<_>::new(src.as_bytes());
        lexer.into_iter().collect()
    }

    #[test]
    fn test_qasm_version() {
        let src = "OPENQASM 2.0;\n";
        let tok = tokens(src);
        assert_eq!(tok.len(), 1);
        assert_eq!(tok[0], Token::Version(2));
    }

    #[test]
    fn test_qasm_include() {
        let src = r#"include "qelib.inc";"#;
        let tok = tokens(src);
        assert_eq!(tok.len(), 1);
        assert_eq!(tok[0], Token::Include(String::from("qelib.inc")));
    }

    #[test]
    fn test_qasm_qreg() {
        let src = r"qreg asdf[3];";
        let tok = tokens(src);
        assert_eq!(tok.len(), 1);
        assert_eq!(tok[0], Token::QregDecl(String::from("asdf"), 3));
    }

    #[test]
    fn test_qasm_fixed_gates() {
        let src = "h q[3];\n";
        let tok = tokens(src);
        assert_eq!(tok.len(), 1);
        assert_eq!(tok[0], Token::FixedGate(FixedGate::H, vec![3]));
    }

    #[test]
    fn test_qasm_multi_qubit() {
        let src = "cx q[3], q[4];\n";
        let tok = tokens(src);
        assert_eq!(tok.len(), 1);
        assert_eq!(tok[0], Token::FixedGate(FixedGate::Cx, vec![3, 4]));

        let src = "cx q[3], q[4];";
        let tok = tokens(src);
        assert_eq!(tok.len(), 1);
        assert_eq!(tok[0], Token::FixedGate(FixedGate::Cx, vec![3, 4]));
    }

    #[test]
    fn test_qasm_file() {
        let src = r#"
    OPENQASM 2.0;
    include "qelib1.inc";
    qreg q[14];
    creg c[14];
    h q[1];
    t q[14];
    t q[12];
    t q[1];
    cx q[12],q[14];
    cx q[1],q[12];
    "#;
        
        let tok = tokens(src);
        dbg!(&tok);
        assert_eq!(tok.len(), 9);
    }
}
