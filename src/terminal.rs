use std::panic;

use crossterm::terminal::{enable_raw_mode, disable_raw_mode};
use tracing::debug;

/// Create a scope with the terminal in raw mode.  Attempt to catch
/// panics so we can disable raw mode before exiting.
pub fn with_raw_mode(f: impl FnOnce() + panic::UnwindSafe) -> Result<(), anyhow::Error> {
    let saved_hook = panic::take_hook();
    panic::set_hook(Box::new(|p| {
        // Override the default error message print handler
        debug!("PANIC! {:?}", p);
    }));

    debug!("BEFORE ENABLE_RAW_MODE()");
    enable_raw_mode()?;
    let result = panic::catch_unwind(f);
    disable_raw_mode()?;
    debug!("AFTER DISABLE_RAW_MODE()");

    panic::set_hook(saved_hook);
    match result {
        Ok(_) => Ok(()),
        Err(e) => {
            debug!("BEFORE RESUME_UNWIND()");
            panic::resume_unwind(e)
        }
    }
}
