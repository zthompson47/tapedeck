use crossterm::terminal;
use std::panic;

/// Create a scope with the terminal in raw mode.  Attempt to catch
/// panics so we can disable raw mode before exiting.
pub fn with_raw_mode(f: impl FnOnce() + panic::UnwindSafe) {
    let saved_hook = panic::take_hook();
    panic::set_hook(Box::new(|_| {
        // Do nothing: overrides console error message from panic!()
    }));

    terminal::enable_raw_mode().expect("raw mode enabled");
    let result = panic::catch_unwind(f);
    terminal::disable_raw_mode().expect("raw mode disabled");

    panic::set_hook(saved_hook);
    if let Err(err) = result {
        panic::resume_unwind(err);
    }
}
