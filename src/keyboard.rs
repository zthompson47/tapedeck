use std::io::Read;
use std::thread::{self, JoinHandle};

use tokio::sync::mpsc;
use tracing::debug;

enum KeyCommand {
    Quit,
    Unknown(u8),
}

impl KeyCommand {
    fn from_byte(b: u8) -> Self {
        match b {
            3 | 113 => Self::Quit,
            _ => Self::Unknown(b),
        }
    }
}

pub fn init_key_command(tx_quit: mpsc::UnboundedSender<()>) -> JoinHandle<()> {
    thread::spawn(move || {
        let mut stdin = std::io::stdin();
        let mut buf: [u8; 1] = [0; 1];

        loop {
            stdin.read_exact(&mut buf).unwrap();
            match KeyCommand::from_byte(buf[0]) {
                KeyCommand::Quit => {
                    debug!("Got QUIT signal");
                    tx_quit.send(()).unwrap();
                    break;
                }
                KeyCommand::Unknown(cmd) => {
                    debug!("keyboard input >{}<", cmd);
                }
            }
        }
    })
}
