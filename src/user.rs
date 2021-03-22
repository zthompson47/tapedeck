use std::thread::{self, JoinHandle};

use crossterm::event::{self, Event, KeyCode, KeyModifiers};
use tokio::sync::mpsc;

#[derive(Debug, PartialEq)]
pub enum Command {
    NextTrack,
    PrevTrack,
    Print(String),
    Quit,
}

pub fn start_tui(tx_cmd: mpsc::UnboundedSender<Command>) -> JoinHandle<()> {
    thread::spawn(move || loop {
        match event::read().unwrap() {
            Event::Key(event) => match event.code {
                KeyCode::Char(ch) => match ch {
                    'c' => {
                        if event.modifiers == KeyModifiers::CONTROL {
                            tx_cmd.send(Command::Quit).unwrap();
                        }
                    }
                    'i' => {}
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
            },
            _ => {}
        }
    })
}
