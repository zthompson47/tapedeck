use std::{
    env,
    fmt::{Error, Write},
    path::Path,
};

use crossterm::style::Colorize;
use tracing::{
    subscriber::Subscriber,
    {Event, Level},
};
use tracing_appender::{non_blocking::WorkerGuard, rolling};
use tracing_log::NormalizeEvent;
use tracing_subscriber::{
    fmt::time::{ChronoLocal, FormatTime},
    fmt::{FmtContext, FormatEvent, FormatFields},
    registry::LookupSpan,
};

pub fn dev_log() -> Option<WorkerGuard> {
    let log_dir = match env::var("TAPEDECK_DEV_DIR") {
        Ok(dir) => Path::new(&dir).to_path_buf(),
        Err(_) => return None,
    };
    let default_level = Level::INFO;
    let file_appender = rolling::never(log_dir, String::from("log"));
    let (log_writer, guard) = tracing_appender::non_blocking(file_appender);

    tracing_subscriber::fmt()
        .with_max_level(match env::var("RUST_LOG") {
            Ok(level) => match level.as_str() {
                "info" | "INFO" => Level::INFO,
                "warn" | "WARN" => Level::WARN,
                "error" | "ERROR" => Level::ERROR,
                "debug" | "DEBUG" => Level::DEBUG,
                "trace" | "TRACE" => Level::TRACE,
                _ => default_level,
            },
            _ => default_level,
        })
        .with_writer(log_writer)
        .event_format(SimpleFmt)
        .try_init().unwrap();

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
        writer: &mut dyn Write,
        event: &Event<'_>,
    ) -> Result<(), Error> {
        // Create timestamp
        let time_format = "%b %d %I:%M:%S%.6f %p";
        let mut time_now = String::new();
        ChronoLocal::with_format(time_format.into()).format_time(&mut time_now)?;

        // Get line numbers from log crate events
        let normalized_meta = event.normalized_metadata();
        let meta = normalized_meta.as_ref().unwrap_or_else(|| event.metadata());

        // Write formatted log record
        let message = format!(
            "{}{} {}{}{} ",
            time_now.grey(),
            meta.level().to_string().blue(),
            meta.file().unwrap_or("").to_string().yellow(),
            String::from(":").yellow(),
            meta.line().unwrap_or(0).to_string().yellow(),
        );
        write!(writer, "{}", message).unwrap();
        ctx.format_fields(writer, event)?;
        writeln!(writer)
    }
}

#[cfg(test)]
mod tests {
    use std::{env, fs, io::prelude::*, io::BufReader};

    use log;
    use tempfile::tempdir;
    use tracing;

    use super::*;

    #[test]
    fn generate_log_records() {
        // Use tempdir for log files
        let dir = tempdir().unwrap().into_path();
        env::set_var("XDG_CACHE_DIR", &dir);
        let _logging = dev_log();

        // Try both logging crates
        log::info!("test log INFO");
        tracing::debug!("test tracing DEBUG");

        // Confirm log file created
        let dir = dir.join("appname-test");
        assert!(dir.is_dir());
        let log_file = dir.join("log");
        assert!(log_file.is_file());

        // Drop logging guard to flush logs.
        // TODO test it??  failure below was intermittent
        //   hmm still dropping records after this drop..
        drop(_logging);

        // Check log records
        let file = fs::File::open(&log_file).unwrap();
        let buf_reader = BufReader::new(file);
        let log_records: Vec<String> = buf_reader.lines().map(|x| x.unwrap()).collect();
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
