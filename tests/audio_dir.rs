use std::ffi::OsString;

use tapedeck::{
    audio_dir::{MediaDir, MediaFile},
    database::get_test_store,
};

#[tokio::test(flavor = "multi_thread", worker_threads = 1)]
async fn audio_dir_create_and_read() {
    let store = get_test_store().unwrap();

    // Create records
    let mut dir = MediaDir::default();
    for i in 0..4 {
        // TODO maybe implement push()?
        dir.extend(Vec::from([MediaFile {
            location: OsString::from(i.to_string()),
            file_size: Some(42),
            ..MediaFile::default()
        }]));
    }
    dir.extend(vec![MediaFile::default()]);
    dir.last_modified = 47;

    dir.db_insert(&store).unwrap();

    assert_eq!(dir.id.unwrap(), 1);
    assert_eq!(dir.files().len(), 5);
    assert_eq!(dir.files()[2].id.unwrap(), 3);
    //assert_eq!(dir.extra.len(), 3);

    drop(dir);

    let dirs = MediaDir::get_audio_dirs(&store).unwrap();
    assert_eq!(dirs.len(), 1);
    assert_eq!(dirs[0].last_modified, 47);

    let files = MediaDir::get_audio_files(&store, 1).unwrap();
    println!("{:#?}", files);
    assert_eq!(files.len(), 5);
    assert_eq!(files[3].file_size, Some(42));
}
