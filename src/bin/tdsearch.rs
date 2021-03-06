use std::cmp::Ordering;
use std::collections::HashMap;
use std::env::{self, args};
use std::ffi::OsString;
use std::path::PathBuf;

use crossterm::style::Colorize;
use mime_guess;
use sqlx::migrate::Migrator;
use sqlx::sqlite::SqlitePool;
use walkdir::WalkDir;

use tapedeck::audio::dir::{AudioDir, AudioFile};

static MIGRATOR: Migrator = sqlx::migrate!();

fn get_database_url(name: &str) -> Result<String, ()> {
    let result = match env::var("DATABASE_URL") {
        Ok(url) => Ok(url),
        Err(_) => match env::var("HOME") {
            Ok(dir) => {
                let mut path = PathBuf::from(dir)
                    .join(".local")
                    .join("share")
                    .join(name)
                    .join(name);
                path.set_extension("db");
                Ok(path.to_str().unwrap().to_string())
            }
            Err(_) => Ok("tmp".to_string()),
        },
    };

    result
}

#[tokio::main]
async fn main() {
    let _guard = tapedeck::logging::init_logging("tapedeck");

    let mut music_dirs: HashMap<PathBuf, Vec<AudioFile>> = HashMap::new();
    let mut extensions: HashMap<OsString, usize> = HashMap::new();
    let mut extra: HashMap<OsString, Vec<PathBuf>> = HashMap::new();

    tracing::debug!("{:?}", get_database_url("tapedeck"));

    let pool = SqlitePool::connect(&get_database_url("tapedeck").unwrap())
        .await
        .unwrap();
    MIGRATOR.run(&pool).await.unwrap();

    // Sort directories-first with file entries forming an alpahbetized contiguous
    // list followed by their parent directory.
    for entry in WalkDir::new(args().nth(1).unwrap())
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
                    audio_dir.db_insert(&pool).await.unwrap();
                    print_audio_dir(&audio_dir);
                } else {
                    extra.clear();
                }
            }
        }
    }
    println!("{:#?}", extensions);
}

fn print_audio_dir(dir: &AudioDir) {
    println!("{}", dir.path.to_str().unwrap().blue());

    if dir.extra.len() > 0 {
        for key in dir.extra.keys() {
            print!("[{:?}:{}]", key, dir.extra.get(key).unwrap().len());
        }
        println!();
    }

    let mut i = 0;
    for file in dir.files.iter() {
        if i > 5 {
            println!("  {}{}", file, "...".to_string().red());
            break;
        } else {
            println!("  {}", file);
            i += 1
        }
    }
}
