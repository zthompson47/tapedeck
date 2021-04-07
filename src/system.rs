use std::thread::{self, JoinHandle};

use bytes::Bytes;
use libpulse_binding::{
    sample::{Format, Spec},
    stream::Direction,
};
use libpulse_simple_binding::Simple as Pulse;
use tokio::sync::mpsc;

pub fn start_pulse(mut rx_audio: mpsc::Receiver<Bytes>) -> JoinHandle<()> {
    thread::spawn(move || {
        let spec = Spec {
            format: Format::S16le,
            channels: 2,
            rate: 44100,
        };
        if !spec.is_valid() {
            panic!("Audio spec not valid: {:?}", spec);
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
                panic!("Can't connect PulseAudio: {:?}", e);
            }
        };

        while let Some(buf) = rx_audio.blocking_recv() {
            match pulse.write(&buf) {
                Ok(_) => {}
                Err(_e) => {}  // tracing::debug!("{:?}", e.to_string()),
            }
            //pulse.drain().unwrap(); TODO makes audio breakup.. but backpressure?
        }
    })
}
