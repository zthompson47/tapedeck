use std::io::Write;

use crossterm::{cursor, style::Colorize, terminal, QueueableCommand};
use tokio::sync::mpsc::{unbounded_channel, UnboundedSender};

pub struct Screen {
    pub tx_screen_cmd: UnboundedSender<ScreenCommand>,
}

impl Screen {
    pub fn new() -> Self {
        let (tx_screen_cmd, mut rx_screen_cmd) = unbounded_channel::<ScreenCommand>();
        tokio::spawn(async move {
            while let Some(cmd) = rx_screen_cmd.recv().await {
                match cmd {
                    ScreenCommand::Draw(lines) => {
                        use crossterm::{cursor::*, style::*};
                        let mut stdout = std::io::stdout();

                        stdout.queue(MoveTo(0, 0)).unwrap();
                        let (_x, y) = terminal::size().unwrap();
                        for i in 0..y - 1 {
                            stdout.queue(MoveTo(0, i)).unwrap();
                            stdout.queue(Print(lines[i as usize].as_str())).unwrap();
                        }
                        stdout.flush().unwrap();
                    }
                }
            }
        });
        Self { tx_screen_cmd }
    }

    pub fn get_handle(&self) -> ScreenHandle {
        ScreenHandle {
            tx_screen_cmd: self.tx_screen_cmd.clone(),
        }
    }
}

#[derive(Clone)]
pub struct ScreenHandle {
    pub tx_screen_cmd: UnboundedSender<ScreenCommand>,
}

fn truncate(s: &str, max_chars: usize) -> &str {
    match s.char_indices().nth(max_chars) {
        None => s,
        Some((idx, _)) => &s[..idx],
    }
}

impl ScreenHandle {
    pub fn status(&self, message: String) {
        //use unicode_width::UnicodeWidthStr;
        let (x, y) = terminal::size().unwrap();
        let xx = (x - 2) as usize;
        let mut stdout = std::io::stdout();
        stdout.queue(cursor::MoveTo(0, y)).unwrap();
        print!("{}", truncate(message.as_str(), xx as usize).green());
        std::io::stdout().flush().unwrap();
    }

    pub fn draw(&self, lines: &Vec<String>) {
        self.tx_screen_cmd
            .send(ScreenCommand::Draw(lines.clone()))
            .unwrap();
    }

    pub fn enter_alternate_screen(&self) {
        let mut stdout = std::io::stdout();
        stdout.queue(terminal::EnterAlternateScreen).unwrap();
        stdout.flush().unwrap();
    }

    pub fn leave_alternate_screen(&self) {
        let mut stdout = std::io::stdout();
        stdout.queue(terminal::LeaveAlternateScreen).unwrap();
        stdout.flush().unwrap();
    }
}

#[derive(Debug)]
pub enum ScreenCommand {
    Draw(Vec<String>),
}
