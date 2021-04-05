use std::thread;

use crossterm::event::{self, Event, KeyCode, KeyEvent, KeyModifiers};
use futures::future::FutureExt;
use tokio::{
    sync::{
        mpsc::{unbounded_channel, UnboundedReceiver, UnboundedSender},
        oneshot,
    },
    task::unconstrained,
};

#[derive(Debug, PartialEq)]
pub enum Command {
    Info,
    NextTrack,
    PrevTrack,
    Print(String),
    ScrollUp(usize),
    ScrollDown(usize),
    Quit,
}

#[derive(Debug, PartialEq)]
pub enum LevelDelta {
    PercentUp(usize),
    PercentDown(usize),
}

pub struct User {
    tx_cmd: UnboundedSender<Command>,
    tx_user: UnboundedSender<UserCommand>,
    rx_user: UnboundedReceiver<UserCommand>,
}

#[derive(Clone)]
pub struct UserHandle {
    pub tx_user: UnboundedSender<UserCommand>,
}

impl UserHandle {
    pub async fn take_input(&self) -> UnboundedReceiver<KeyEvent> {
        let (tx, rx) = oneshot::channel::<UnboundedReceiver<KeyEvent>>();
        self.tx_user.send(UserCommand::TakeInput(tx)).unwrap();

        rx.await.unwrap()
    }
}

#[derive(Debug)]
pub enum UserCommand {
    TakeInput(oneshot::Sender<UnboundedReceiver<KeyEvent>>),
}

impl User {
    pub fn new(tx_cmd: UnboundedSender<Command>) -> Self {
        let (tx_user, rx_user) = unbounded_channel::<UserCommand>();
        Self {
            tx_cmd,
            tx_user,
            rx_user,
        }
    }

    pub fn get_handle(&self) -> UserHandle {
        UserHandle {
            tx_user: self.tx_user.clone(),
        }
    }

    pub async fn run(self) {
        // Listen for keyboard and mouse events from separate thread
        let (tx, mut rx) = unbounded_channel::<Event>();
        {
            let tx = tx;
            thread::spawn(move || loop {
                while let Ok(event) = event::read() {
                    tx.send(event).unwrap();
                }
            });
        }

        // Channel to retrieve widget handles from UserCommand listener task
        let (tx_widget_stack, mut rx_widget_stack) = unbounded_channel();

        {
            // Handle incoming commands
            let mut rx_user = self.rx_user;
            tokio::spawn(async move {
                while let Some(command) = rx_user.recv().await {
                    match command {
                        UserCommand::TakeInput(tx_oneshot) => {
                            // Create channeel for intercepted events
                            let (tx, rx) = unbounded_channel();
                            // Push tx end on widget stack
                            tx_widget_stack.send(tx).unwrap();
                            // Return rx
                            tx_oneshot.send(rx).unwrap();
                        }
                    }
                }
            });
        }

        let mut widget_stack: Vec<UnboundedSender<KeyEvent>> = Vec::new();

        while let Some(event) = rx.recv().await {
            // Check for a new widget to take over the input
            if let Some(Some(tx_widget)) = unconstrained(rx_widget_stack.recv()).now_or_never() {
                widget_stack.push(tx_widget);
            }
            match event {
                Event::Key(event) => match event.code {
                    KeyCode::Char(ch) => {
                        if !widget_stack.is_empty() {
                            // Try to send events to top widget
                            match widget_stack[widget_stack.len() - 1].send(event) {
                                Ok(_) => continue,
                                Err(_) => {
                                    // Dropped connection, so pop goes the weasel
                                    widget_stack.pop();
                                }
                            }
                        }
                        // Default key commands
                        match ch {
                            'c' => {
                                if event.modifiers == KeyModifiers::CONTROL {
                                    self.tx_cmd.send(Command::Quit).unwrap();
                                }
                            }
                            'i' => {
                                self.tx_cmd.send(Command::Info).unwrap();
                            }
                            'q' => {
                                self.tx_cmd.send(Command::Quit).unwrap();
                            }
                            _ => {}
                        }
                    }
                    KeyCode::Esc => {
                        tracing::debug!("{:?}", Command::Quit);
                        self.tx_cmd.send(Command::Quit).unwrap();
                    }
                    KeyCode::Left => {
                        tracing::debug!("{:?}", Command::PrevTrack);
                        self.tx_cmd.send(Command::PrevTrack).unwrap();
                    }
                    KeyCode::Right => {
                        tracing::debug!("{:?}", Command::NextTrack);
                        self.tx_cmd.send(Command::NextTrack).unwrap();
                    }
                    _ => {}
                },
                Event::Mouse(_) => {}
                Event::Resize(_, _) => {}
            }
        }
    }
}
