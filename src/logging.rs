use log::{debug, error, info, log, trace, warn, Level, LevelFilter, Metadata, Record};
use std::io::Write;
use std::sync::mpsc;
use std::sync::Mutex;

#[derive(Debug)]
pub struct LogRecord {
    meta_level: String,
    pub meta_target: String,
    module_path: String,
    file: String,
    args: String,
    line: u32,
}

#[derive(Debug)]
pub struct Logger {
    level: LevelFilter,
    snd: Mutex<mpsc::Sender<LogRecord>>,
}

impl Logger {
    pub fn init() {
        let (snd, rcv) = mpsc::channel();
        let logger = Logger {
            level: match std::env::var("RUST_LOG") {
                Ok(level) => match level.as_str() {
                    "error" => LevelFilter::Error,
                    "warn" => LevelFilter::Warn,
                    "info" => LevelFilter::Info,
                    "debug" => LevelFilter::Debug,
                    "trace" => LevelFilter::Trace,
                    _ => LevelFilter::Info,
                },
                _ => LevelFilter::Info,
            },
            snd: Mutex::new(snd),
        };
        log::set_boxed_logger(Box::new(logger)).expect("already set logger");
        log::set_max_level(LevelFilter::Trace);

        // Log to stdout
        std::thread::spawn(move || {
            while let Ok(msg) = rcv.recv() {
                //if msg.meta_target == "tdplay" {
                write!(std::io::stdout(), "{:?}\r\n", msg).expect("stdout write error");
                //}
            }
        });

        log!(target: "buttmonkey", Level::Error, "-------------!!!!!!!!! {} error starting", 4);
        error!("-------------!!!!!!!!! {} error starting", 4);
        warn!("-------------!!!!!!!!! {} warn starting", 4);
        info!("-------------!!!!!!!!! {} info starting", 4);
        debug!("-------------!!!!!!!!! {} debug starting", 4);
        trace!("-------------!!!!!!!!! {} trace starting", 4);
    }
}

impl log::Log for Logger {
    fn enabled(&self, _metadata: &Metadata) -> bool {
        true
    }

    fn log(&self, record: &Record) {
        self.snd
            .lock()
            .unwrap()
            .send(LogRecord {
                meta_level: record.level().to_string(),
                meta_target: record.target().to_string(),
                module_path: record.module_path().unwrap().to_string(),
                file: record.file().unwrap().to_string(),
                args: record.args().to_string(),
                line: record.line().unwrap(),
            })
            .expect("channel send error");
    }

    fn flush(&self) {}
}
