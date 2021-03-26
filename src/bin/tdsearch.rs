use std::{cmp::Ordering, collections::HashMap, ffi::OsString, path::PathBuf};

use crossterm::style::Colorize;
use structopt::StructOpt;
use tokio::runtime::Runtime;
use walkdir::WalkDir;

use tapedeck::{
    audio_dir::{AudioDir, AudioFile, Location},
    database::get_database,
    logging::start_logging,
};

#[derive(StructOpt)]
struct Cli {
    #[structopt(short, long)]
    list: bool,
    #[structopt(parse(from_os_str))]
    search_path: Option<PathBuf>,
}

fn main() -> Result<(), anyhow::Error> {
    let args = Cli::from_args();
    let rt = Runtime::new()?;

    if args.list {
        rt.block_on(list_dirs())?;
    } else if let Some(path) = args.search_path {
        rt.block_on(import_dirs(path))?;
    }

    Ok(())
}

/// Get all audio_dir records from the database and print them to stdout.
async fn list_dirs() -> Result<(), anyhow::Error> {
    let _logging = start_logging("tapedeck");
    let db = get_database("tapedeck").await?;
    let audio_dirs = AudioDir::get_audio_dirs(&db).await;

    for dir in audio_dirs.iter() {
        println!(
            "{}. {}",
            // All AudioDir from the database have `id`
            &dir.id.unwrap().to_string().magenta(),
            &dir.location.to_string(),
        );
    }

    Ok(())
}

/// Search search_path for audio directories and save to database.
async fn import_dirs(search_path: PathBuf) -> Result<(), anyhow::Error> {
    let _logging = start_logging("tapedeck");
    let db = get_database("tapedeck").await?;
    // Containers
    let mut _audio_groups: HashMap<PathBuf, Vec<AudioDir>> = HashMap::new();
    let mut audio_dirs: HashMap<PathBuf, Vec<AudioFile>> = HashMap::new();
    let mut extensions: HashMap<OsString, usize> = HashMap::new();
    let mut extra: HashMap<OsString, Vec<PathBuf>> = HashMap::new();

    // Sort directories-first with file entries forming an alpahbetized
    // contiguous list followed by their parent directory.
    for entry in WalkDir::new(search_path)
        .contents_first(true)
        .sort_by(
            |a, b| match (a.file_type().is_dir(), b.file_type().is_dir()) {
                (true, false) => Ordering::Less,
                (false, true) => Ordering::Greater,
                (true, true) | (false, false) => a.file_name().cmp(b.file_name()),
            },
        )
        .into_iter()
        .flatten()
    {
        let path = entry.path();
        let guess = mime_guess::from_path(path);
        let mut found_audio = false;

        // Store audio files
        if let Some(guess) = guess.first() {
            if guess.type_() == "audio" {
                found_audio = true;
                // Group audio files by directory
                let file_list = audio_dirs
                    .entry(path.parent().unwrap().into())
                    .or_insert_with(Vec::new);
                (*file_list).push(AudioFile {
                    location: Location::Path(path.to_owned()),
                    mime_type: Some(guess),
                    file_size: Some(entry.metadata()?.len()),
                    ..AudioFile::default()
                });
                // Count by extension
                let ext = path.extension().unwrap().into();
                let counter = extensions.entry(ext).or_insert(0);
                *counter += 1;
            }
        }

        // Store extra non-audio files to keep with any audio dirs
        if entry.file_type().is_file() && !found_audio {
            let extra_list = extra
                .entry(path.extension().unwrap_or(&OsString::from("n/a")).into())
                .or_insert_with(Vec::new);
            (*extra_list).push(path.into());
        }

        // Fold each completed directory into results
        if path.is_dir() {
            if audio_dirs.contains_key(path) {
                let mut audio_dir = AudioDir {
                    location: Location::Path(path.to_owned()),
                    files: {
                        match audio_dirs.get(path) {
                            Some(files) => files.to_vec(),
                            None => Vec::new(),
                        }
                    },
                    extra: std::mem::take(&mut extra),
                    last_modified: timestamp(entry.metadata()?.modified()?),
                    ..AudioDir::default()
                };
                // Try to insert into database
                match audio_dir.db_insert(&db).await {
                    Ok(_) => print!("{}", &audio_dir),
                    Err(_) => println!("dup"),
                }
            } else {
                extra.clear();
            }
        }
    }
    println!("{:#?}", extensions);

    Ok(())
}

use std::time::{SystemTime, UNIX_EPOCH};
fn timestamp(t: SystemTime) -> u128 {
    match t.duration_since(UNIX_EPOCH) {
        Ok(n) => n.as_millis(),
        Err(_) => 0,
    }
}
