use std::time::{Duration, Instant};

use bytes::Bytes;
use tokio::sync::oneshot;
use tokio::{io::AsyncReadExt, process, sync::mpsc, time::timeout};

use crate::audio_dir::MediaFile;
use crate::ffmpeg::audio_from_url;
use crate::user::Command;

/// Plays a playlist and responds to user commands.
#[derive(Debug)]
pub struct Transport {
    files: Vec<MediaFile>,
    cursor: usize,
    tx_transport_cmd: mpsc::UnboundedSender<TransportCommand>,
    rx_transport_cmd: mpsc::UnboundedReceiver<TransportCommand>,
    tx_audio: mpsc::Sender<Bytes>,
}

/// Commands for manipulating playback.
#[derive(Debug)]
pub enum TransportCommand {
    NextTrack,
    PrevTrack,
    NowPlaying(oneshot::Sender<MediaFile>),
}

pub struct TransportHandle {
    pub tx_transport_cmd: mpsc::UnboundedSender<TransportCommand>,
}

impl TransportHandle {
    pub fn next_track(&self) -> Result<(), anyhow::Error> {
        self.tx_transport_cmd.send(TransportCommand::NextTrack)?;
        Ok(())
    }
    pub fn prev_track(&self) -> Result<(), anyhow::Error> {
        self.tx_transport_cmd.send(TransportCommand::PrevTrack)?;
        Ok(())
    }
    pub async fn now_playing(&self) -> Result<MediaFile, anyhow::Error> {
        let (tx, rx) = oneshot::channel();
        self.tx_transport_cmd.send(TransportCommand::NowPlaying(tx))?;
        Ok(rx.await?)
    }
}

impl Transport {
    /// Create a new Transport out of channel endpoints.
    pub fn new(
        tx_audio: mpsc::Sender<Bytes>,
        //rx_transport_cmd: mpsc::UnboundedReceiver<TransportCommand>,
    ) -> Self {
        let (tx_transport_cmd, rx_transport_cmd) = mpsc::unbounded_channel();
        Self {
            files: Vec::new(),
            cursor: 0,
            tx_audio,
            tx_transport_cmd,
            rx_transport_cmd,
        }
    }

    pub fn get_handle(&mut self) -> TransportHandle {
        let (tx_transport_cmd, rx_transport_cmd) = mpsc::unbounded_channel::<TransportCommand>();
        self.rx_transport_cmd = rx_transport_cmd;
        TransportHandle { tx_transport_cmd }
    }

    /// Add files to the end of the playlist.
    pub fn extend(&mut self, files: Vec<MediaFile>) {
        self.files.extend(files);
    }

    /// Return the file at the cursor.
    pub fn now_playing(&self) -> &MediaFile {
        &self.files[self.cursor]
    }

    /// Stream audio to output device and respond to user commands.
    pub async fn run(mut self, tx_cmd: mpsc::UnboundedSender<Command>) {
        let mut buf = [0u8; 4096];

        'play: loop {
            // Get next file to play
            let mut audio_reader = match self.get_reader_at_cursor().await {
                Ok(reader) => reader,
                Err(_) => break 'play,
            };

            tx_cmd
                .send(Command::Print(
                    self.now_playing().location.to_string_lossy().to_string(), // TODO ? Cow?
                ))
                .unwrap(); // TODO got panic here pressing esc to exit..

            // PrevTrack usually restarts the current track, but it goes back
            // to the _actual_ previous track when called at the beginning of
            // a track. Useful for navigating back and forth in the playlist.
            const DOUBLE_TAP: Duration = Duration::from_millis(333);
            let start_time = Instant::now();

            // Send audio file to output device
            while let Ok(len) = audio_reader.read(&mut buf).await {
                if len == 0 {
                    self.cursor += 1;
                    continue 'play;
                } else {
                    let chunk = Bytes::copy_from_slice(&buf[0..len]);
                    self.tx_audio.send(chunk).await.unwrap();
                }

                // Poll for transport commands that interrupt playback
                if let Ok(Some(cmd)) =
                    timeout(Duration::from_millis(0), self.rx_transport_cmd.recv()).await
                {
                    match cmd {
                        TransportCommand::NextTrack => {
                            if self.cursor < self.files.len() - 1 {
                                self.cursor += 1;
                            }
                            continue 'play;
                        }
                        TransportCommand::PrevTrack => {
                            if start_time.elapsed() < DOUBLE_TAP {
                                self.cursor = self.cursor.saturating_sub(1);
                            }
                            continue 'play;
                        }
                        TransportCommand::NowPlaying(tx) => {
                            tx.send(self.now_playing().clone()).unwrap();
                        }
                    }
                }
            }
            self.cursor += 1;
        }
        tx_cmd.send(Command::Quit).unwrap();
    }

    /// Create a stream of audio data from the current playlist position.
    async fn get_reader_at_cursor(&mut self) -> Result<process::ChildStdout, anyhow::Error> {
        // TODO ! not returning reader, so bad name
        if self.cursor >= self.files.len() {
            return Err(anyhow::Error::msg("cursor index out of bounds, just quit"));
        }
        let file = self.now_playing().location.to_string_lossy();
        let mut file = audio_from_url(&file).await.spawn()?;
        file.stdout
            .take()
            .ok_or_else(|| anyhow::Error::msg("could not take music file's stdout"))
    }
}
