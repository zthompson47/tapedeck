use std::thread::{self, JoinHandle};

use libpulse_binding::{
    sample::{Format, Spec},
    stream::Direction,
};
use libpulse_simple_binding::Simple as Pulse;
use tokio::sync::mpsc;
use tracing::debug;

pub mod dir;

const CHUNK: usize = 4096;

pub type Chunk = [u8; CHUNK];

pub trait ChunkLen {
    fn len() -> usize {
        CHUNK
    }
    fn new() -> Chunk {
        [0; CHUNK]
    }
}

impl ChunkLen for Chunk {}

pub fn init_pulse(mut rx_audio: mpsc::Receiver<Chunk>) -> JoinHandle<()> {
    thread::spawn(move || {
        let spec = Spec {
            format: Format::S16le,
            channels: 2,
            rate: 44100,
        };
        if !spec.is_valid() {
            debug!("Spec not valid: {:?}", spec);
            panic!("!!!!!!!!SPEC NOT VALID!!!!!!!!");
        }

        let pulse = match Pulse::new(
            None,                // Use the default server
            "tapedeck",          // Our application’s name
            Direction::Playback, // We want a playback stream
            None,                // Use the default device
            "Music",             // Description of our stream
            &spec,               // Our sample format
            None,                // Use default channel map
            None,                // Use default buffering attributes
        ) {
            Ok(pulse) => pulse,
            Err(e) => {
                debug!("{:?}", e);
                panic!("!!!!!!!!NO PULSEAUDIO!!!!!!!!");
            }
        };

        while let Some(buf) = rx_audio.blocking_recv() {
            match pulse.write(&buf) {
                Ok(_) => {}
                Err(e) => debug!("{:?}", e),
            }
            //pulse.drain().unwrap();
        }
    })
}
