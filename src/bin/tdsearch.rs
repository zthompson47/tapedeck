use std::cmp::Ordering;
use std::collections::HashMap;
use std::ffi::OsString;
use std::path::PathBuf;

use crossterm::style::Colorize;
use mime_guess;
use structopt::StructOpt;
use tokio::runtime::Runtime;
use walkdir::WalkDir;

use tapedeck::audio::dir::{AudioDir, AudioFile};
use tapedeck::database::get_database;

#[derive(StructOpt)]
struct Cli {
    #[structopt(short, long)]
    list: bool,
    #[structopt(parse(from_os_str))]
    search_path: Option<PathBuf>,
}

fn main() {
    let args = Cli::from_args();
    let rt = Runtime::new().unwrap();
    match args.list {
        true => rt.block_on(list_dirs(args)),
        false => rt.block_on(search_dirs(args)),
    }
}

async fn list_dirs(_args: Cli) {
    let _guard = tapedeck::logging::init_logging("tapedeck");
    let db = get_database("tapedeck").await.unwrap();
    let audio_dirs = AudioDir::get_audio_dirs(&db).await;
    for dir in audio_dirs.iter() {
        let path = PathBuf::from(&dir.path);
        println!(
            "{}. {}",
            &dir.id.to_string().magenta(),
            &path.file_name().unwrap().to_string_lossy().yellow()
        );
    }
}

async fn search_dirs(args: Cli) {
    let _guard = tapedeck::logging::init_logging("tapedeck");
    let db = get_database("tapedeck").await.unwrap();
    let mut music_dirs: HashMap<PathBuf, Vec<AudioFile>> = HashMap::new();
    let mut extensions: HashMap<OsString, usize> = HashMap::new();
    let mut extra: HashMap<OsString, Vec<PathBuf>> = HashMap::new();

    // Sort directories-first with file entries forming an alpahbetized
    // contiguous list followed by their parent directory.
    for entry in WalkDir::new(args.search_path.unwrap())
        .contents_first(true)
        .sort_by(
            |a, b| match (a.file_type().is_dir(), b.file_type().is_dir()) {
                (true, false) => Ordering::Less,
                (false, true) => Ordering::Greater,
                (true, true) | (false, false) => a.file_name().cmp(b.file_name()),
            },
        )
    {
        if let Ok(entry) = entry {
            // Try to guess mime-type
            let path = entry.path();
            let guess = mime_guess::from_path(path);
            let mut found_audio = false;
            if let Some(guess) = guess.first() {
                if guess.type_() == "audio" {
                    found_audio = true;
                    // Group audio files by directory
                    let file_list = music_dirs
                        .entry(path.parent().unwrap().into())
                        .or_insert(Vec::new());
                    (*file_list).push(AudioFile {
                        id: None,
                        path: path.into(),
                        mime_type: guess,
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
                    .or_insert(Vec::new());
                (*extra_list).push(path.into());
            }

            // Fold each completed directory into results
            if path.is_dir() {
                if music_dirs.contains_key(path) {
                    let mut audio_dir = AudioDir {
                        path: path.into(),
                        files: {
                            match music_dirs.get(path) {
                                Some(files) => files.to_vec(),
                                None => Vec::new(),
                            }
                        },
                        extra: std::mem::take(&mut extra),
                        ..AudioDir::default()
                    };
                    // Try to insert into database
                    match audio_dir.db_insert(&db).await {
                        Ok(_) => print_audio_dir(&audio_dir),
                        Err(_) => println!("dup"),
                    }
                } else {
                    extra.clear();
                }
            }
        }
    }
    println!("{:#?}", extensions);
}

fn print_audio_dir(dir: &AudioDir) {
    println!(
        "{}. {}",
        dir.id.unwrap_or(-1).to_string().magenta(),
        dir.path.to_str().unwrap().blue()
    );

    let mut i = 0;
    for file in dir.files.iter() {
        if i > 5 {
            println!(" {}{}", file, "...".to_string().green());
            break;
        } else {
            println!(" {}", file);
            i += 1
        }
    }

    if dir.extra.len() > 0 {
        for key in dir.extra.keys() {
            print!(
                " [{}:{}]",
                key.to_str().unwrap(),
                dir.extra.get(key).unwrap().len()
            );
        }
        println!();
    }
}
