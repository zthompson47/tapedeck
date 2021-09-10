use std::{env, path::PathBuf};

use rusqlite::Connection;

const APP: &str = "tapedeck";

#[derive(Debug)]
pub struct Store {
    pub conn: Connection,
}

impl Store {
    pub fn new() -> Result<Self, anyhow::Error> {
        Store::with_base_dir(None)
    }

    pub fn with_base_dir(base_dir: Option<PathBuf>) -> Result<Self, anyhow::Error> {
        let db_path = match base_dir {
            Some(dir) => dir,
            None => match env::var("XDG_DATA_HOME") {
                Ok(dir) => PathBuf::from(dir).join(APP),
                Err(_) => match env::var("HOME") {
                    Ok(dir) => PathBuf::from(dir).join(".local").join("share").join(APP),
                    Err(_) => PathBuf::from("/tmp").join(APP),
                },
            },
        };

        // Make sure the database directory exists
        let db_path = match std::fs::create_dir_all(&db_path) {
            Ok(_) => Some(db_path),
            Err(err) if err.kind() == std::io::ErrorKind::AlreadyExists => Some(db_path),
            Err(_) => None,
        };

        // Open the database, which creates a new db file if needed
        let conn = match db_path {
            Some(mut db_path) => {
                db_path = db_path.join(APP);
                db_path.set_extension("db");
                Connection::open(&db_path)?
            }
            None => Connection::open_in_memory()?,
        };

        // Create tables if this is a new database
        if conn.prepare("select max(id) from version").is_err() {
            init_db(&conn)?;
        }

        Ok(Store { conn })
    }
}

pub async fn get_test_store() -> Result<Store, anyhow::Error> {
    let store = Connection::open_in_memory()?;
    init_db(&store)?;
    Ok(Store { conn: store })
}

fn init_db(conn: &Connection) -> Result<(), anyhow::Error> {
    conn.execute_batch(
        "\
        create table media_dir(
            id integer primary key not null,
            last_modified integer,
            location blob unique not null
        );
        create table media_file(
            id integer primary key not null,
            media_dir_id integer not null,
            file_size integer,
            media_type text,
            location blob unique not null,
            foreign key(media_dir_id) references media_dir(id)
        );
        create table version(id int);
        insert into version values(1);
        ",
    )?;

    Ok(())
}
