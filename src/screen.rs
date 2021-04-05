use std::io::Write;

use crossterm::{
    cursor,
    style::{self, Colorize},
    terminal, QueueableCommand,
};
use tokio::sync::mpsc::{unbounded_channel, UnboundedReceiver, UnboundedSender};

/// An interface to the terminal screen.
pub struct Screen {
    /// The current status message.
    pub status: String,
    /// Endpoint for sending commands to the screen.
    pub tx_screen_cmd: UnboundedSender<ScreenCommand>,
    /// Endpoint for receiving commands in the screen.
    pub rx_screen_cmd: UnboundedReceiver<ScreenCommand>,
}

/// Commands for a screen.
#[derive(Debug)]
pub enum ScreenCommand {
    /// Draw lines of text to the screen.
    Draw(Vec<String>),
    /// Set the status message at the bottom of the screen.
    SetStatus(String),
}

impl Screen {
    /// Create a channel and spawn a background task to process incoming commands.
    pub fn new() -> Self {
        let (tx_screen_cmd, rx_screen_cmd) = unbounded_channel::<ScreenCommand>();

        Self {
            status: String::new(),
            tx_screen_cmd,
            rx_screen_cmd,
        }
    }

    pub fn run(mut self) -> ScreenHandle {
        let handle = ScreenHandle {
            tx_screen_cmd: self.tx_screen_cmd.clone(),
        };

        tokio::spawn(async move {
            while let Some(cmd) = self.rx_screen_cmd.recv().await {
                match cmd {
                    ScreenCommand::Draw(lines) => {
                        let mut stdout = std::io::stdout();
                        stdout
                            .queue(terminal::Clear(terminal::ClearType::All))
                            .unwrap();
                        stdout.queue(cursor::MoveTo(0, 0)).unwrap();
                        // TODO: u16 conversion might panic?
                        let (_x, y) = terminal::size().unwrap();
                        for i in 0..(std::cmp::min(y as usize - 1, lines.len() - 1)) {
                            stdout.queue(cursor::MoveTo(0, i as u16)).unwrap();
                            stdout
                                .queue(style::Print(lines[i as usize].as_str()))
                                .unwrap();
                        }
                        stdout.flush().unwrap();
                        self.draw_status();
                    }
                    ScreenCommand::SetStatus(message) => {
                        //use unicode_width::UnicodeWidthStr;
                        self.status = message.clone();
                        self.draw_status();
                    }
                }
            }
        });

        handle
    }

    fn draw_status(&self) {
        let (x, y) = terminal::size().unwrap();
        let xx = (x - 2) as usize; // TODO: check predicted unicode widths
        let mut stdout = std::io::stdout();
        stdout.queue(cursor::MoveTo(0, y)).unwrap();
        print!("{}", truncate(self.status.as_str(), xx as usize).green());
        std::io::stdout().flush().unwrap();
    }
}

/// A handle for calling in to a screen.
#[derive(Clone)]
pub struct ScreenHandle {
    /// A channel for sending comands to the screen.
    pub tx_screen_cmd: UnboundedSender<ScreenCommand>,
}

// From https://stackoverflow.com/questions/38461429/\
// how-can-i-truncate-a-string-to-have-at-most-n-characters
/// Truncate a unicode string with possible multibyte characters.
fn truncate(s: &str, max_chars: usize) -> &str {
    match s.char_indices().nth(max_chars) {
        None => s,
        Some((idx, _)) => &s[..idx],
    }
}

impl ScreenHandle {
    /// Set the status message displayed at the bottom of the screen.
    pub fn status(&self, message: String) {
        self.tx_screen_cmd
            .send(ScreenCommand::SetStatus(message))
            .unwrap();
    }
    /// Draw a page of text to the screen.
    pub fn draw(&self, lines: &Vec<String>) {
        self.tx_screen_cmd
            .send(ScreenCommand::Draw(lines.clone()))
            .unwrap();
    }
    /// Enter the terminal's alternate screen.
    pub fn enter_alternate_screen(&self) {
        let mut stdout = std::io::stdout();
        stdout.queue(terminal::EnterAlternateScreen).unwrap();
        stdout.flush().unwrap();
    }
    /// Leave the terminal's alternate screen.
    pub fn leave_alternate_screen(&self) {
        let mut stdout = std::io::stdout();
        stdout.queue(terminal::LeaveAlternateScreen).unwrap();
        stdout.flush().unwrap();
    }
}
