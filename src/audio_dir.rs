use std::collections::HashMap;
use std::ffi::OsString;
use std::fmt;
use std::path::PathBuf;

use crossterm::style::Colorize;
use mime_guess::{self, Mime};
use sqlx::sqlite::SqlitePool;
use tokio_stream::StreamExt;
use tracing::debug;

#[derive(Debug, Default)]
pub struct AudioDir {
    pub id: Option<i64>,
    pub path: PathBuf,
    pub files: Vec<AudioFile>,
    pub extra: HashMap<OsString, Vec<PathBuf>>,
}

#[derive(Debug, Default)]
pub struct AudioDirSql {
    pub id: i64,
    pub path: String,
}

impl AudioDir {
    pub async fn get_audio_dirs(pool: &SqlitePool) -> Vec<AudioDirSql> {
        let mut result = Vec::new();

        let mut dirs = sqlx::query_as!(
            AudioDirSql,
            r#"
            SELECT
                id as id,
                path as path
            FROM audio_dir
            "#,
        )
        .fetch(pool);

        while let Ok(dir) = dirs.try_next().await {
            match dir {
                Some(dir) => result.push(dir),
                None => break,
            }
        }

        result
    }

    pub async fn get_audio_files(pool: &SqlitePool, id: i64) -> Vec<AudioFileSql> {
        let mut files = sqlx::query_as!(
            AudioFileSql,
            r#"
            SELECT
                id AS id,
                path AS path,
                mime_type AS mime_type
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
                Some(file) => result.push(file),
                None => break,
            }
        }

        result
    }

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
            let mime_type = audio_file.mime_type.essence_str();
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

#[derive(Clone, Debug)]
pub struct AudioFileSql {
    pub id: i64,
    pub path: String,
    pub mime_type: Option<String>,
}

#[derive(Clone, Debug)]
pub struct AudioFile {
    pub id: Option<i64>,
    pub path: PathBuf,
    pub mime_type: Mime,
}

impl fmt::Display for AudioFile {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "{}:{}",
            self.mime_type.to_string().green(),
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

#[derive(Debug)]
pub struct ExtraFile {
    pub id: Option<i64>,
    pub path: PathBuf,
    pub mime_type: Mime,
}