use std::env;
use std::fmt::Error;
use std::path::Path;

use crossterm::style::Stylize;

use tracing::subscriber::Subscriber;
use tracing::Event;
use tracing_appender::non_blocking::WorkerGuard;
use tracing_appender::rolling;
use tracing_log::NormalizeEvent;
use tracing_subscriber::{
    filter::EnvFilter,
    fmt::{format::Writer, FmtContext, FormatEvent, FormatFields},
    registry::LookupSpan,
};

pub type Guard = WorkerGuard;

#[must_use]
pub fn init() -> Option<Guard> {
    let log_dir = match env::var("TD_LOG_DIR") {
        Ok(dir) => Path::new(&dir).to_path_buf(),
        Err(_) => Path::new(".").to_path_buf(),
    };
    let file_appender = rolling::never(log_dir, String::from("log"));
    let (log_writer, guard) = tracing_appender::non_blocking(file_appender);

    tracing_subscriber::fmt()
        .with_writer(log_writer)
        .with_env_filter(EnvFilter::from_default_env())
        .event_format(SimpleFmt)
        .try_init()
        .ok();

    Some(guard)
}

struct SimpleFmt;

impl<S, N> FormatEvent<S, N> for SimpleFmt
where
    S: Subscriber + for<'a> LookupSpan<'a>,
    N: for<'a> FormatFields<'a> + 'static,
{
    fn format_event(
        &self,
        ctx: &FmtContext<'_, S, N>,
        mut writer: Writer<'_>,
        event: &Event<'_>,
    ) -> Result<(), Error> {
        let time_now = chrono::Local::now();
        let time_now = time_now.format("%b %d %I:%M:%S%.6f %p").to_string();
        // Get line numbers from log crate events
        let normalized_meta = event.normalized_metadata();
        let meta = normalized_meta.as_ref().unwrap_or_else(|| event.metadata());
        let message = format!(
            "{} {} {}{}{} ",
            time_now.grey(),
            meta.level().to_string().blue(),
            meta.file().unwrap_or("").to_string().yellow(),
            String::from(":").yellow(),
            meta.line().unwrap_or(0).to_string().yellow(),
        );

        write!(writer, "{message}").unwrap();
        // Write actual log message with newline
        ctx.format_fields(writer.by_ref(), event)?;
        writeln!(writer)
    }
}

#[cfg(test)]
mod tests {
    use std::{env, fs, io::prelude::*, io::BufReader};

    use tempfile::tempdir;

    use super::*;

    #[test]
    fn generate_log_records() {
        // Use tempdir for log files
        let dir = tempdir().unwrap().into_path();
        env::set_var("RUST_LOG", "debug");
        env::set_current_dir(&dir).unwrap();
        let _log = init();

        // Try both logging crates
        log::info!("test log INFO");
        tracing::debug!("test tracing DEBUG");

        // Confirm log file created
        //let dir = dir.join("appname-test");
        //let dir = dir.join("log");
        assert!(dir.is_dir());
        let log_file = dir.join("log.txt");
        assert!(log_file.is_file());

        // Drop logging guard to flush logs.
        // TODO test it??  failure below was intermittent
        //   hmm still dropping records after this drop..
        drop(_log);

        // Check log records
        let file = fs::File::open(&log_file).unwrap();
        let buf_reader = BufReader::new(file);
        let log_records: Vec<String> = buf_reader.lines().map(|x| x.unwrap()).collect();
        println!("---------->> {:?}", log_records);
        assert!(log_records.len() >= 2);
        let idx = log_records.len() - 2;

        if !log_records[idx].contains("test log INFO") {
            // TODO - Log records are occasionally dropped... ??
            println!("{}", fs::read_to_string(&log_file).unwrap());
        }

        assert!(log_records[idx].contains("test log INFO"));
        assert!(log_records[idx + 1].ends_with("test tracing DEBUG"));
    }
}
