use std::collections::HashMap;
use std::ffi::OsString;
use std::fmt;
use std::path::PathBuf;

use crossterm::style::Colorize;
use mime_guess::{self, Mime};
use sqlx::sqlite::SqlitePool;
use tokio_stream::StreamExt;
use tracing::debug;

#[derive(Clone, Debug, PartialEq)]
pub enum Location {
    Path(PathBuf),
    None,
    Url(String),
}

impl Default for Location {
    fn default() -> Self {
        Self::None
    }
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
#[derive(Clone, Debug, Default)]
pub struct AudioDir {
    pub id: Option<i64>,
    pub location: Location,
    pub extra: HashMap<OsString, Vec<PathBuf>>,
    pub last_modified: i64,
    files: Vec<AudioFile>,
}

/// An audio file.
#[derive(Clone, Debug, Default)]
pub struct AudioFile {
    pub id: Option<i64>,
    pub location: Location,
    pub mime_type: Option<Mime>,
    pub file_size: Option<i64>,
    pub last_modified: Option<i64>,
}

/// A non-audio file in an audio directory.
#[derive(Clone, Debug, Default)]
pub struct ExtraFile {
    pub id: Option<i64>,
    pub location: Location,
    pub mime_type: Option<Mime>,
}

impl From<(Option<String>, Option<Vec<u8>>)> for Location {
    fn from((url, path): (Option<String>, Option<Vec<u8>>)) -> Self {
        if let Some(path) = path {
            Location::Path(PathBuf::from(OsString::from_vec(path)))
        } else if let Some(url) = url {
            Location::Url(url)
        } else {
            Location::None
        }
    }
}

impl From<PathBuf> for AudioFile {
    fn from(p: PathBuf) -> Self {
        Self {
            location: Location::Path(p),
            ..AudioFile::default()
        }
    }
}

impl From<Location> for AudioDir {
    fn from(location: Location) -> Self {
        Self {
            location,
            ..Self::default()
        }
    }
}

impl From<Row> for AudioDir {
    fn from(row: Row) -> Self {
        Self {
            id: Some(row.id),
            last_modified: row.last_modified.unwrap(), // TODO!
            location: row.location(),
            ..Self::default()
        }
    }
}

impl From<Row> for AudioFile {
    fn from(row: Row) -> Self {
        Self {
            id: Some(row.id),
            last_modified: row.last_modified,
            location: row.location(),
            ..Self::default()
        }
    }
}

// ---------------------------------------------
// TODO system predicate
use std::os::unix::ffi::OsStrExt;
use std::os::unix::ffi::OsStringExt;

#[derive(Debug)]
struct Row {
    id: i64,
    url: Option<String>,
    path: Option<Vec<u8>>,
    last_modified: Option<i64>,
}

impl Row {
    fn location(&self) -> Location {
        match &self.path {
            Some(ref path) => Location::Path(PathBuf::from(OsString::from_vec(path.clone()))),
            None => match &self.url {
                Some(url) => Location::Url(url.clone()),
                None => Location::None,
            },
        }
    }
}

// ---------------------------------------------

impl AudioDir {
    pub fn extend_files(&mut self, f: Vec<AudioFile>) {
        self.files.extend(f);
    }

    pub fn push_file(&mut self, f: AudioFile) {
        self.files.push(f);
    }

    pub fn files(&self) -> &Vec<AudioFile> {
        &self.files
    }

    /// Find a list of directories by matching path with a pattern.
    pub async fn get_with_path(pool: &SqlitePool, pattern: &str) -> Vec<AudioDir> {
        let mut dirs = sqlx::query_as!(
            Row,
            r#"
            SELECT
                id as id,
                url as url,
                path as path,
                last_modified as last_modified
            FROM audio_dir
            WHERE path like ?
            "#,
            pattern
        )
        .fetch(pool);

        let mut result = Vec::new();

        while let Ok(Some(row)) = dirs.try_next().await {
            result.push(AudioDir {
                id: Some(row.id),
                location: row.location(),
                ..AudioDir::default()
            });
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
                path as path,
                last_modified as last_modified
            FROM audio_dir
            "#,
        )
        .fetch(pool);

        let mut result = Vec::new();

        while let Ok(Some(row)) = rows.try_next().await {
            result.push(AudioDir::from(row));
        }

        result
    }

    /// Return a list of all audio files in a particular audio directory.
    pub async fn get_audio_files(pool: &SqlitePool, id: i64) -> Vec<AudioFile> {
        let mut files = sqlx::query!(
            r#"
            select id, path, url, last_modified, file_size
            from audio_file
            where id in (
                select audio_file_id
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
                    location: Location::from((row.url, row.path)),
                    file_size: row.file_size,
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
            // TODO system predicate
            Location::Path(path) => (None, Some(path.as_os_str().as_bytes())),
            Location::Url(url) => (Some(url), None),
            Location::None => (None, None),
        };

        println!("about to insert self: {:#?}", self);

        let insert_id = sqlx::query!(
            r#"
            INSERT INTO audio_dir(url, path, last_modified)
            VALUES(?1, ?2, ?3)
            "#,
            url,
            path,
            self.last_modified,
        )
        .execute(pool)
        .await?
        .last_insert_rowid();

        self.id = Some(insert_id);

        for audio_file in &mut self.files[..] {
            let (url, path) = &match audio_file.location {
                Location::Path(ref path) => (None, Some(path.as_os_str().as_bytes())),
                Location::Url(ref url) => (Some(url), None),
                Location::None => (None, None),
            };

            let mime_type = audio_file
                .mime_type
                .as_ref()
                .map(|m| m.essence_str().to_string());

            let audio_file_id = sqlx::query!(
                r#"
                INSERT INTO audio_file(url, path, mime_type, file_size)
                VALUES(?1, ?2, ?3, ?4);
                "#,
                url,
                path,
                mime_type,
                audio_file.file_size,
            )
            .execute(pool)
            .await?
            .last_insert_rowid();
            audio_file.id = Some(audio_file_id);

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
        if !self.extra.is_empty() {
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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn defaults() {
        assert_eq!(Location::default(), Location::None);
        assert_eq!(AudioDir::default().id, None);
        assert_eq!(AudioFile::default().id, None);
        assert_eq!(ExtraFile::default().id, None);
    }

    #[test]
    fn locations() {
        let path = Location::Path(PathBuf::from("/"));
        assert_eq!(path.to_string(), "/");
        let url = Location::Url(String::from("http://www.web.net"));
        assert_eq!(url.to_string(), "http://www.web.net");
    }

    #[test]
    fn audio_dir_from_row() {
        let dir = AudioDir::from(Row {
            id: 42,
            url: Some("url".to_string()),
            path: Some("path".as_bytes().to_vec()),
            last_modified: Some(47),
        });
        assert_eq!(dir.id, Some(42));
        assert_eq!(dir.location, Location::Path(PathBuf::from("path")));
        assert_eq!(dir.last_modified, 47);
    }

    #[test]
    fn audio_file_from_row() {
        let file = AudioFile::from(Row {
            id: 42,
            url: Some("url".to_string()),
            path: Some("path".as_bytes().to_vec()),
            last_modified: Some(47),
        });
        assert_eq!(file.id, Some(42));
        assert_eq!(file.location, Location::Path(PathBuf::from("path")));
        assert_eq!(file.last_modified, Some(47));
    }
}
