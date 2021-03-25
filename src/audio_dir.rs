use std::collections::HashMap;
use std::ffi::OsString;
use std::fmt;
use std::path::PathBuf;

use crossterm::style::Colorize;
use mime_guess::{self, Mime};
use sqlx::sqlite::SqlitePool;
use tokio_stream::StreamExt;
use tracing::debug;

#[derive(Clone, Debug)]
pub enum Location {
    Path(PathBuf),
    None,
    Url(String),
}

impl fmt::Display for Location {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "{}",
            match self {
                Self::Path(p) => p.as_os_str().to_string_lossy().into_owned(),
                Self::Url(s) => s.to_string(),
                Self::None => "n/a".into(),
            }
        )
    }
}

/// A directory containing audio files.
#[derive(Clone, Debug)]
pub struct AudioDir {
    pub id: Option<i64>,
    pub location: Location,
    pub files: Vec<AudioFile>,
    pub extra: HashMap<OsString, Vec<PathBuf>>,
}

impl Default for AudioDir {
    fn default() -> Self {
        Self {
            id: Default::default(),
            location: Location::None,
            files: Default::default(),
            extra: Default::default(),
        }
    }
}

/// An audio file.
#[derive(Clone, Debug)]
pub struct AudioFile {
    pub id: Option<i64>,
    pub location: Location,
    pub mime_type: Option<Mime>,
}

impl Default for AudioFile {
    fn default() -> Self {
        Self {
            id: Default::default(),
            location: Location::None,
            mime_type: Default::default(),
        }
    }
}

/// A non-audio file in an audio directory.
#[derive(Clone, Debug)]
pub struct ExtraFile {
    pub id: Option<i64>,
    pub location: Location,
    pub mime_type: Option<Mime>,
}

impl AudioFile {
    /// Generate a String representation of the path.
    pub fn path_as_string(&self) -> String {
        self.location.to_string()
    }
}

impl From<String> for AudioFile {
    fn from(path: String) -> Self {
        Self {
            id: None,
            location: Location::Path(PathBuf::from(path)),
            mime_type: None, // TODO guess mime type
        }
    }
}

impl From<&PathBuf> for AudioFile {
    fn from(path: &PathBuf) -> Self {
        Self {
            id: None,
            location: Location::Path(PathBuf::from(path)),
            mime_type: None, // TODO guess mime type
        }
    }
}

// ---------------------------------------------
// TODO system predicate
use std::os::unix::ffi::OsStringExt;
use std::os::unix::ffi::OsStrExt;

#[derive(Debug)]
struct Row {
    id: i64,
    url: Option<String>,
    path: Option<Vec<u8>>,
}

impl Row {
    fn location(&self) -> Location {
        match &self.path {
            Some(ref path) => Location::Path(PathBuf::from(OsString::from_vec(path.clone()))),
            None => match &self.url {
                Some(url) => Location::Url(url.clone()),
                None => Location::None,
            }
        }
    }

    /*
    fn location_parts(&self) -> (Option<String>, Option<PathBuf>) {
        match self.location() {
            Location::Path(path) => (None, Some(path.as_os_str().as_bytes())),
            Location::Url(url) => (Some(url), None),
            Location::None => (None, None),
        }
    }
    */
}
// ---------------------------------------------

impl AudioDir {
    /// Find a list of directories by matching path with a pattern.
    pub async fn get_with_path(pool: &SqlitePool, pattern: &str) -> Vec<AudioDir> {
        let mut dirs = sqlx::query_as!(
            Row,
            r#"
            SELECT
                id as id,
                url as url,
                path as path
            FROM audio_dir
            WHERE path like ?
            "#,
            pattern
        )
        .fetch(pool);

        let mut result = Vec::new();

        while let Ok(row) = dirs.try_next().await {
            match row {
                Some(row) => result.push(AudioDir {
                    id: Some(row.id),
                    location: row.location(),
                    ..AudioDir::default()
                }),
                None => break,
            }
        }

        result
    }

    /// Return a list of all audio directories.
    pub async fn get_audio_dirs(pool: &SqlitePool) -> Vec<AudioDir> {
        let mut rows = sqlx::query_as!(
            Row,
            r#"
            SELECT
                id as id,
                url as url,
                path as path
            FROM audio_dir
            "#,
        )
        .fetch(pool);

        let mut result = Vec::new();

        while let Ok(row) = rows.try_next().await {
            match row {
                Some(row) => result.push(AudioDir {
                    id: Some(row.id),
                    location: row.location(),
                    ..AudioDir::default()
                }),
                None => break,
            }
        }

        result
    }

    /// Return a list of all audio files in a particular audio directory.
    pub async fn get_audio_files(pool: &SqlitePool, id: i64) -> Vec<AudioFile> {
        let mut files = sqlx::query_as!(
            Row,
            r#"
            select id as id,
                path as path,
                url as url
            from audio_file
            where id in (
                select
                    audio_file_id as id
                from audio_dir_audio_file
                where audio_dir_id = ?
            )"#,
            id
        )
        .fetch(pool);

        let mut result = Vec::new();

        while let Ok(file) = files.try_next().await {
            debug!("FILE: {:?}", file);
            match file {
                Some(row) => result.push(AudioFile {
                    id: Some(row.id),
                    location: row.location(),
                    ..AudioFile::default()
                }),
                None => break,
            }
        }

        result
    }

    /// Save all records to database.
    pub async fn db_insert(&mut self, pool: &SqlitePool) -> Result<(), sqlx::Error> {
        let transaction = pool.begin().await?;

        let (url, path) = match &self.location {
            Location::Path(path) => (None, Some(path.as_os_str().as_bytes())),
            Location::Url(url) => (Some(url), None),
            Location::None => (None, None),
        };

        let insert_id = sqlx::query!(
            r#"
            INSERT INTO audio_dir(url, path)
            VALUES(?1, ?2)
            "#,
            url,
            path
        )
        .execute(pool)
        .await?
        .last_insert_rowid();

        self.id = Some(insert_id);

        for audio_file in &self.files[..] {
            //let path = audio_file.path.unwrap().as_os_str().as_bytes();
            /*
            let path = match audio_file.path {
                Some(ref p) => Some(p.as_os_str().as_bytes()),
                None => None,
            };
            */

            let (_url, path) = &match audio_file.location {
                Location::Path(ref path) => (None, Some(path.as_os_str().as_bytes())),
                Location::Url(ref url) => (Some(url), None),
                Location::None => (None, None),
            };

            let mime_type = match &audio_file.mime_type {
                Some(m) => Some(m.essence_str().to_string()),
                None => None,
            };
            let audio_file_id = sqlx::query!(
                r#"
                INSERT INTO audio_file(path, mime_type)
                VALUES(?1, ?2);
                "#,
                path,
                mime_type,
            )
            .execute(pool)
            .await?
            .last_insert_rowid();

            sqlx::query!(
                r#"
                INSERT INTO audio_dir_audio_file(audio_dir_id, audio_file_id)
                VALUES ($1, $2);
                "#,
                self.id,
                audio_file_id,
            )
            .execute(pool)
            .await?;
        }

        for (extension, files) in &self.extra {
            for extra_file in files {
                let path = extra_file.to_str();
                let extension = extension.to_str();
                let extra_file_id = sqlx::query!(
                    r#"
                    INSERT INTO extra_file(path, mime_type)
                    VALUES(?1, ?2);
                    "#,
                    path,
                    extension,
                )
                .execute(pool)
                .await?
                .last_insert_rowid();

                sqlx::query!(
                    r#"
                    INSERT INTO audio_dir_extra_file(audio_dir_id, extra_file_id)
                    VALUES ($1, $2);
                    "#,
                    self.id,
                    extra_file_id,
                )
                .execute(pool)
                .await?;
            }
        }

        transaction.commit().await
    }
}

impl fmt::Display for AudioFile {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "{}:{}",
            match &self.mime_type {
                Some(m) => m.to_string().green(),
                None => "-/-".to_string().green(),
            },
            self.location.to_string().magenta()
        )
    }
}

impl fmt::Display for AudioDir {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        // Id and path
        writeln!(
            f,
            "{}. {}",
            self.id.unwrap_or(-1).to_string().magenta(),
            self.location.to_string().blue()
        )?;

        // Limited list of `audio_file`s
        let mut i = 0;
        for file in self.files.iter() {
            if i > 5 {
                writeln!(f, " {}{}", file, "...".to_string().green())?;
                break;
            } else {
                writeln!(f, " {}", file)?;
                i += 1
            }
        }

        // Summary of `extra_file`s
        if self.extra.len() > 0 {
            for key in self.extra.keys() {
                write!(
                    f,
                    " [{}:{}]",
                    key.to_str().unwrap(),
                    self.extra.get(key).unwrap().len()
                )?;
            }
            writeln!(f)?;
        }

        Ok(())
    }
}
