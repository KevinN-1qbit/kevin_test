use std::{collections::VecDeque, fmt::Write, io::{Bytes, Read}};
use lazy_static::lazy_static;
use regex::Regex;
use anyhow::{bail, Context};

use crate::operation::phase::Phase;


#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Pauli {
    I,
    X,
    Y,
    Z,
}


impl TryFrom<char> for Pauli {
    type Error = char;

    fn try_from(value: char) -> Result<Self, Self::Error> {
        match value {
            'X' | 'x' => Ok(Self::X),
            'Y' | 'y' => Ok(Self::Y),
            'Z' | 'z' => Ok(Self::Z),
            'I' | 'i' => Ok(Self::I),
            _ => Err(value),
        }
    }
}



#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Token {
    Rotate(i8),
    Measure(Phase),
    Pauli(Pauli),
    Repeat(u32),
    End,
}


#[derive(Debug)]
pub struct TokenIterator<R: Read> {
    source: Bytes<R>,
    token_buf: VecDeque<Token>,
    line_buf: String,
    line_count: usize,
}


impl<R: Read> TokenIterator<R> {
    pub fn new(source: R) -> Self {
        Self {
            source: source.bytes(),
            token_buf: VecDeque::with_capacity(128),
            line_buf: String::with_capacity(128),
            line_count: 0,
        }
    }
}


lazy_static! {
    static ref REPEAT: Regex = {
        // optional whitespace
        // literal 'Repeat'
        // at least one whitespace
        // at least one digit (named capture group: 'repeats')
        // optional whitespace
        Regex::new(r"^\s*Repeat\s+(?<repeats>\d+)\s*$").unwrap()
    };

    static ref END: Regex = {
        // optional whitespace
        // literal 'End'
        // optional whitespace
        Regex::new(r"^\s*End\s*$").unwrap()
    };

    static ref ROTATE: Regex = {
        // optional whitespace
        // literal 'Rotate'
        // at least one whitespace
        // signed integer (named capture group 'angle')
        // optional whitespace
        // literal ':'
        // optional whitespace
        // at least one pauli (named capture group 'paulis')
        // optional whitespace
        Regex::new(r"^\s*Rotate\s+(?<angle>\-?\d+)\s*:\s*(?<paulis>[IXYZ]+)\s*$").unwrap()
    };

    static ref MEASURE: Regex = {
        // optional whitespace
        // literal 'Measure'
        // at least one whitespace
        // sign (named capture group 'sign')
        // optional whitespace
        // literal ':'
        // at least one pauli (named capture group 'paulis')
        // optional whitespace
        Regex::new(r"^\s*Measure\s+(?<sign>[+-])\s*:\s*(?<paulis>[IXYZ]+)\s*$").unwrap()
    };
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

    fn read_line(&mut self) -> anyhow::Result<usize> {
        let mut read = 0;

        loop {
            match self.source.next() {
                None => break,
                Some(r) => match r {
                    Ok(b'\n') => {
                        read += 1;
                        break;
                    },
                    Ok(byte) => {
                        read += 1;

                        let Some(ch) = char::from_u32(byte as u32) else {
                            bail!("Non-ASCII character found in source");
                        };
                        // check for ETX or EOT
                        if ch == '\u{03}' || ch == '\u{04}' {
                            break;
                        }
                        self.line_buf.write_char(ch)?;
                    },
                    Err(e) => {
                        return Err(e.into());
                    }
                }
            }
        }

        Ok(read)
    }

    fn fill_token_buf(&mut self) -> anyhow::Result<()>{
        // read lines until one is nonempty
        loop {
            self.line_count += 1;
            self.line_buf.clear();
            let len = self.read_line()?;

            if len == 0 {
                // EOF
                return Ok(());
            }

            if self.line_buf.chars().any(|ch| !ch.is_ascii_whitespace()) {
                break;
            }
        }

        // otherwise, fill the token buffer

        if let Some(m) = REPEAT.captures(&self.line_buf) {
            let val: u32 = m["repeats"].parse().with_context(||
                format!("Could not parse repeat statement on line {} ('{}'): wrong or too large repeat count", self.line_count, self.line_buf)
            )?;
            self.token_buf.push_back(Token::Repeat(val))
        } else if let Some(m) = ROTATE.captures(&self.line_buf) {
            let angle: i8 = m["angle"].parse().with_context(|| format!("Wrong or too large angle on line {} ('{}')", self.line_count, self.line_buf))?;
            if angle.abs() > 2 {
                bail!("Angle on line {} too large ", self.line_count);
            }
            self.token_buf.push_back(Token::Rotate(angle));

            for ch in m["paulis"].chars() {
                self.token_buf.push_back(Token::Pauli(Pauli::try_from(ch).unwrap()))
            }
        } else if let Some(m) = MEASURE.captures(&self.line_buf) {
            let phase = match &m["sign"] {
                "+" => Phase::Positive,
                "-" => Phase::Negative,
                _ => unreachable!()
            };
            self.token_buf.push_back(Token::Measure(phase));

            for ch in m["paulis"].chars() {
                self.token_buf.push_back(Token::Pauli(Pauli::try_from(ch).unwrap()))
            }
        } else if END.is_match(&self.line_buf) {
            self.token_buf.push_back(Token::End)
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
    fn test_end() {
        let src = "End\n";
        let tok = tokens(src);
        assert_eq!(tok.len(), 1);
        assert_eq!(tok[0], Token::End);

        // test with windows line ending and extraneous spaces
        let src = "End\r\n";
        let tok = tokens(src);
        assert_eq!(tok.len(), 1);
        assert_eq!(tok[0], Token::End);

        let src = "  End \n";
        let tok = tokens(src);
        assert_eq!(tok.len(), 1);
        assert_eq!(tok[0], Token::End);
    }

    #[test]
    fn test_repeat() {
        let toks = tokens("Repeat 25\n");
        assert_eq!(toks.len(), 1);
        assert_eq!(toks[0], Token::Repeat(25));

        let toks = tokens(" Repeat 25\r\n");
        assert_eq!(toks.len(), 1);
        assert_eq!(toks[0], Token::Repeat(25));
    }

    #[test]
    fn test_measure() {
        let toks = tokens("Measure +: IXYZ\r\n");
        assert_eq!(toks.len(), 5);
        assert_eq!(toks[0], Token::Measure(Phase::Positive));
        assert_eq!(toks[1], Token::Pauli(Pauli::I));
        assert_eq!(toks[2], Token::Pauli(Pauli::X));
        assert_eq!(toks[3], Token::Pauli(Pauli::Y));
        assert_eq!(toks[4], Token::Pauli(Pauli::Z));

        let toks = tokens(" Measure  - :  IXYZ \n");
        assert_eq!(toks.len(), 5);
        assert_eq!(toks[0], Token::Measure(Phase::Negative));
        assert_eq!(toks[1], Token::Pauli(Pauli::I));
        assert_eq!(toks[2], Token::Pauli(Pauli::X));
        assert_eq!(toks[3], Token::Pauli(Pauli::Y));
        assert_eq!(toks[4], Token::Pauli(Pauli::Z));
    }

    #[test]
    fn test_rotate() {
        let toks = tokens("Rotate -2: IXYZ  \r\n");
        assert_eq!(toks.len(), 5);
        assert_eq!(toks[0], Token::Rotate(-2));
        assert_eq!(toks[1], Token::Pauli(Pauli::I));
        assert_eq!(toks[2], Token::Pauli(Pauli::X));
        assert_eq!(toks[3], Token::Pauli(Pauli::Y));
        assert_eq!(toks[4], Token::Pauli(Pauli::Z));

        let toks = tokens("Rotate 1: IXYZ\n");
        assert_eq!(toks.len(), 5);
        assert_eq!(toks[0], Token::Rotate(1));
        assert_eq!(toks[1], Token::Pauli(Pauli::I));
        assert_eq!(toks[2], Token::Pauli(Pauli::X));
        assert_eq!(toks[3], Token::Pauli(Pauli::Y));
        assert_eq!(toks[4], Token::Pauli(Pauli::Z));
    }

    #[test]
    fn test_first_line() {
        let src = r#"
Measure +: XYZI
Repeat 5
  Rotate 2: XYZI
End"#;
        let mut tok_iter = TokenIterator::<_>::new(src.as_bytes());
        let mut buf = Vec::new();

        tok_iter.pop_line(&mut buf).unwrap();
        assert_eq!(buf.len(), 5);
        assert_eq!(buf[0], Token::Measure(Phase::Positive));

        // count the rest of the tokens
        let rest_toks: Vec<_> = tok_iter.into_iter().collect();
        assert_eq!(rest_toks.len(), 1 + 1 + 4 + 1);
    }
}
