use std::io::Write;
use std::sync::mpsc;
use std::sync::Mutex;
use tracing::{subscriber, Level};
use tracing_log::LogTracer;
use tracing_subscriber::FmtSubscriber;

/// Initialize logging system.
pub fn init_logging() {
    // Support log crate
    LogTracer::init().unwrap();

    // Send logs to stderr
    let subscriber = FmtSubscriber::builder()
        .with_max_level(
            match std::env::var("RUST_LOG") {
                Ok(level) => match level.as_str() {
                    "info" => Level::INFO,
                    "warn" => Level::WARN,
                    "error" => Level::ERROR,
                    "debug" => Level::DEBUG,
                    "trace" => Level::TRACE,
                    _ => Level::TRACE,
                },
                _ => Level::TRACE,
            }
        )
        .with_writer(RawWriter::new)
        .finish();
    subscriber::set_global_default(subscriber).expect("problem setting global logger");
}

#[derive(Debug, Default)]
struct RawWriter;

impl RawWriter {
    fn new() -> Self {
        RawWriter::default()
    }
}

impl std::io::Write for RawWriter {
    fn write(&mut self, buf: &[u8]) -> std::io::Result<usize> {
        let buf = std::str::from_utf8(buf).unwrap();

        // `buf` is only terminated by '\n', so add '\r' (search c_oflag OPOST)
        #[allow(clippy::explicit_write)]
        write!(std::io::stderr(), "{}\r", buf).unwrap();

        Ok(buf.len())
    }

    fn flush(&mut self) -> std::io::Result<()> {
        Ok(())
    }
}

// -------------- OLD STUFF - for log crate ------------------

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
    level: log::LevelFilter,
    snd: Mutex<mpsc::Sender<LogRecord>>,
}

impl Logger {
    pub fn init() {
        let (snd, rcv) = mpsc::channel();
        let logger = Logger {
            level: match std::env::var("RUST_LOG") {
                Ok(level) => match level.as_str() {
                    "info" => log::LevelFilter::Info,
                    "warn" => log::LevelFilter::Warn,
                    "error" => log::LevelFilter::Error,
                    "debug" => log::LevelFilter::Debug,
                    "trace" => log::LevelFilter::Trace,
                    _ => log::LevelFilter::Info,
                },
                _ => log::LevelFilter::Info,
            },
            snd: Mutex::new(snd),
        };
        log::set_boxed_logger(Box::new(logger)).expect("already set logger");
        log::set_max_level(log::LevelFilter::Trace);

        // Log to stdout
        std::thread::spawn(move || {
            while let Ok(msg) = rcv.recv() {
                write!(std::io::stdout(), "{:?}\r\n", msg).expect("stdout write error");
            }
        });
    }
}

impl log::Log for Logger {
    fn enabled(&self, _metadata: &log::Metadata) -> bool {
        true
    }

    fn log(&self, record: &log::Record) {
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
