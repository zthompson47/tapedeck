use std::panic;

use crossterm::terminal::{disable_raw_mode, enable_raw_mode};

/// Create a scope with the terminal in raw mode.  Attempt to catch
/// panics so we can disable raw mode before exiting.
/// https://www.ralfj.de/blog/2019/11/25/how-to-panic-in-rust.html
pub fn with_raw_mode(f: impl FnOnce() + panic::UnwindSafe) -> Result<(), anyhow::Error> {
    let saved_hook = panic::take_hook();
    panic::set_hook(Box::new(|p| {
        // Extract unformatted error message from panic:
        // rust/src/libstd/panicking.rs:176
        // Formatted messages end up in p.message
        let msg = match p.payload().downcast_ref::<&'static str>() {
            Some(s) => *s,
            None => match p.payload().downcast_ref::<String>() {
                Some(s) => &s[..],
                None => "Box<Any>",
            },
        };

        // Override the default error message print handler
        eprintln!("PANIC! {} {:?}", msg, p);
    }));

    // Run the provided code in raw mode
    enable_raw_mode()?;
    let result = panic::catch_unwind(f);
    disable_raw_mode()?;

    // Resume normal panic handling after raw mode disabled
    panic::set_hook(saved_hook);
    match result {
        Ok(_) => Ok(()),
        Err(e) => {
            eprintln!("BEFORE RESUME_UNWIND()");
            panic::resume_unwind(e)
        }
    }
}
