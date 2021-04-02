use std::thread::{self, JoinHandle};

use crossterm::event::{self, Event, KeyCode, KeyModifiers};
use tokio::sync::mpsc;

#[derive(Debug, PartialEq)]
pub enum Command {
    Info,
    ListTracks,
    Meter,
    NextTrack,
    PrevTrack,
    Print(String),
    Spectrum,
    Volume(LevelDelta),
    Quit,
}

#[derive(Debug, PartialEq)]
pub enum LevelDelta {
    PercentUp(usize),
    PercentDown(usize),
}

pub fn start_ui(tx_cmd: mpsc::UnboundedSender<Command>) -> JoinHandle<()> {
    thread::spawn(move || loop {
        if let Event::Key(event) = event::read().unwrap() { match event.code {
        //match event::read().unwrap() {
            //Event::Key(event) => match event.code {
                KeyCode::Char(ch) => match ch {
                    'c' => {
                        if event.modifiers == KeyModifiers::CONTROL {
                            tx_cmd.send(Command::Quit).unwrap();
                        }
                    }
                    'i' => {
                        tx_cmd.send(Command::Info).unwrap();
                    }
                    'g' => {
                        use std::io::Write;
                        use crossterm::{terminal::{size, SetSize}, QueueableCommand};
                        let mut stdout = std::io::stdout();
                        stdout.queue(SetSize(10, 10)).unwrap();
                        print!("{:?}\r\n", size().unwrap());
                        stdout.flush().unwrap();
                    }
                    'j' => {
                        use std::io::Write;
                        use crossterm::{terminal::ScrollUp, QueueableCommand};
                        let mut stdout = std::io::stdout();
                        stdout.queue(ScrollUp(2)).unwrap();
                        stdout.flush().unwrap();
                    }
                    'k' => {
                        use std::io::Write;
                        use crossterm::{terminal::ScrollDown, QueueableCommand};
                        let mut stdout = std::io::stdout();
                        stdout.queue(ScrollDown(2)).unwrap();
                        stdout.flush().unwrap();
                    }
                    'q' => {
                        tx_cmd.send(Command::Quit).unwrap();
                    }
                    _ => {}
                },
                KeyCode::Esc => {
                    tracing::debug!("{:?}", Command::Quit);
                    tx_cmd.send(Command::Quit).unwrap();
                }
                KeyCode::Left => {
                    tracing::debug!("{:?}", Command::PrevTrack);
                    tx_cmd.send(Command::PrevTrack).unwrap();
                }
                KeyCode::Right => {
                    tracing::debug!("{:?}", Command::NextTrack);
                    tx_cmd.send(Command::NextTrack).unwrap();
                }
                _ => {}
            }
            //_ => {}
        }
    })
}
