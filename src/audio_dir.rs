use std::collections::HashMap;
use std::ffi::OsString;
use std::fmt;
use std::path::PathBuf;

use crossterm::style::Colorize;
use mime_guess::{self, Mime};
use sqlx::sqlite::SqlitePool;
use tokio_stream::StreamExt;
use tracing::debug;

/// A directory containing audio files.
#[derive(Clone, Debug, Default)]
pub struct AudioDir {
    pub id: Option<i64>,
    pub path: PathBuf,
    pub files: Vec<AudioFile>,
    pub extra: HashMap<OsString, Vec<PathBuf>>,
}

/// An audio file.
#[derive(Clone, Debug, Default)]
pub struct AudioFile {
    pub id: Option<i64>,
    pub path: PathBuf,
    pub mime_type: Option<Mime>,
}

/// A non-audio file in an audio directory.
#[derive(Clone, Debug, Default)]
pub struct ExtraFile {
    pub id: Option<i64>,
    pub path: PathBuf,
    pub mime_type: Option<Mime>,
}

impl AudioFile {
    /// Generate a String representation of the path.
    pub fn path_as_string(&self) -> String {
        self.path.to_str().unwrap().to_string()
    }
}

impl From<String> for AudioFile {
    fn from(path: String) -> Self {
        Self {
            path: PathBuf::from(path),
            ..Self::default()
        }
    }
}

impl From<&PathBuf> for AudioFile {
    fn from(path: &PathBuf) -> Self {
        Self {
            path: PathBuf::from(path),
            ..Self::default()
        }
    }
}

impl AudioDir {
    /// Find a list of directories by matching path with a pattern.
    pub async fn search_with_path(pool: &SqlitePool, pattern: &str) -> Vec<AudioDir> {
        #[derive(Debug)]
        struct Row {
            pub id: i64,
            pub path: String,
        }

        let mut dirs = sqlx::query_as!(
            Row,
            r#"
            SELECT
                id as id,
                path as path
            FROM audio_dir
            WHERE path like ?
            "#,
            pattern
        )
        .fetch(pool);

        let mut result = Vec::new();

        while let Ok(dir) = dirs.try_next().await {
            match dir {
                Some(dir) => result.push(AudioDir {
                    id: Some(dir.id),
                    path: dir.path.into(),
                    ..AudioDir::default()
                }),
                None => break,
            }
        }

        result
    }

    /// Return a list of all audio directories.
    pub async fn get_audio_dirs(pool: &SqlitePool) -> Vec<AudioDir> {
        #[derive(Debug)]
        pub struct Row {
            pub id: i64,
            pub path: String,
        }

        let mut rows = sqlx::query_as!(
            Row,
            r#"
            SELECT
                id as id,
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
                    path: row.path.into(),
                    ..AudioDir::default()
                }),
                None => break,
            }
        }

        result
    }

    /// Return a list of all audio files in a particular audio directory.
    pub async fn get_audio_files(pool: &SqlitePool, id: i64) -> Vec<AudioFile> {
        #[derive(Debug)]
        pub struct Row {
            pub id: i64,
            pub path: String,
        }

        let mut files = sqlx::query_as!(
            Row,
            r#"
            SELECT
                id AS id,
                path AS path
            FROM audio_file
            WHERE id IN (
                SELECT
                    audio_file_id AS id
                FROM audio_dir_audio_file
                WHERE audio_dir_id = ?
            )
            "#,
            id
        )
        .fetch(pool);

        let mut result = Vec::new();

        while let Ok(file) = files.try_next().await {
            debug!("FILE: {:?}", file);
            match file {
                Some(row) => result.push(AudioFile {
                    id: Some(row.id),
                    path: row.path.into(),
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

        let dir_path = self.path.to_str();
        let insert_id = sqlx::query!(
            r#"
            INSERT INTO audio_dir(path)
            VALUES(?1)
            "#,
            dir_path
        )
        .execute(pool)
        .await?
        .last_insert_rowid();
        self.id = Some(insert_id);

        for audio_file in &self.files[..] {
            let path = audio_file.path.to_str();
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
            self.path.file_name().unwrap().to_str().unwrap().magenta()
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
            self.path.to_str().unwrap().blue()
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
