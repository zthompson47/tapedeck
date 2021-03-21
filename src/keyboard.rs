use std::thread::{self, JoinHandle};

use crossterm::event::{self, Event, KeyCode, KeyModifiers};
use tokio::sync::mpsc;

#[derive(Debug, PartialEq)]
pub enum KeyCommand {
    NextTrack,
    PrevTrack,
    Print(String),
    Quit,
}

pub fn init_key_command(tx_cmd: mpsc::UnboundedSender<KeyCommand>) -> JoinHandle<()> {
    thread::spawn(move || loop {
        match event::read().unwrap() {
            Event::Key(event) => match event.code {
                KeyCode::Char(c) => match c {
                    'q' => {
                        tracing::debug!("{:?}", KeyCommand::Quit);
                        tx_cmd.send(KeyCommand::Quit).unwrap();
                    }
                    'c' => {
                        if event.modifiers == KeyModifiers::CONTROL {
                            tracing::debug!("{:?}", KeyCommand::Quit);
                            tx_cmd.send(KeyCommand::Quit).unwrap();
                        } else {
                            tracing::debug!("{:?}", event);
                        }
                    }
                    _ => tracing::debug!("{:?}", event),
                },
                KeyCode::Esc => {
                    tracing::debug!("{:?}", KeyCommand::Quit);
                    tx_cmd.send(KeyCommand::Quit).unwrap();
                }
                KeyCode::Left => {
                    tracing::debug!("{:?}", KeyCommand::PrevTrack);
                    tx_cmd.send(KeyCommand::PrevTrack).unwrap();
                }
                KeyCode::Right => {
                    tracing::debug!("{:?}", KeyCommand::NextTrack);
                    tx_cmd.send(KeyCommand::NextTrack).unwrap();
                }
                _ => tracing::debug!("{:?}", event),
            },
            _ => {}
        }
    })
}
