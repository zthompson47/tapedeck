use std::{env, path::PathBuf};

use sqlx::{
    migrate::{MigrateDatabase, Migrator},
    sqlite::SqlitePool,
    Pool, Sqlite,
};
use tokio::fs;
use tracing::debug;

pub static MIGRATOR: Migrator = sqlx::migrate!();

/// Find an appropriate place for the database and make sure it exists there.
pub async fn get_database(app_name: &str) -> Result<Pool<Sqlite>, anyhow::Error> {
    // Look for APPNAME_DEV_DIR environment variable to override default
    let mut dev_dir = app_name.to_uppercase();
    dev_dir.push_str("_DEV_DIR");

    // Find directory location from environment
    let dir = match env::var(&dev_dir) {
        Ok(dir) => PathBuf::from(dir),
        Err(_) => match env::var("XDG_DATA_HOME") {
            Ok(dir) => PathBuf::from(dir).join(app_name),
            Err(_) => match env::var("HOME") {
                Ok(dir) => PathBuf::from(dir)
                    .join(".local")
                    .join("share")
                    .join(app_name),
                Err(_) => PathBuf::from("/tmp").join(app_name),
            },
        },
    };

    // Make sure the directory exists
    fs::create_dir_all(&dir).await?;

    debug!("Created db dir: {:?}", dir.to_str());

    // Compose connection string
    let mut url = dir.clone().join(app_name);
    url.set_extension("db");
    let mut conn_str = String::from("sqlite:");
    conn_str.push_str(url.to_str().unwrap_or(":memory:"));

    debug!("Connection str: {:?}", &conn_str);

    // Create if it doesn't exist
    Sqlite::create_database(&conn_str).await?;

    // Connect and migrate
    let db = SqlitePool::connect(&conn_str).await?;
    MIGRATOR.run(&db).await?;

    Ok(db)
}
