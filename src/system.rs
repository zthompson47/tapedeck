use std::thread::{self, JoinHandle};

use bytes::BytesMut;
use libpulse_binding::{
    sample::{Format, Spec},
    stream::Direction,
};
use libpulse_simple_binding::Simple as Pulse;
use tokio::sync::mpsc;
use tracing::debug;

pub fn init_pulse(mut rx_audio: mpsc::Receiver<BytesMut>) -> JoinHandle<()> {
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
