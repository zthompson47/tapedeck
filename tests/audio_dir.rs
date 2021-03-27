use tapedeck::{
    audio_dir::{AudioDir, AudioFile},
    database::get_test_database,
};

#[tokio::test(flavor = "multi_thread", worker_threads = 1)]
async fn audio_dir_create_and_read() {
    let db = get_test_database().await.unwrap();

    // Create records
    let mut dir = AudioDir::default();
    for _ in 0..4 {
        dir.push_file(AudioFile {
            file_size: Some(42),
            ..AudioFile::default()
        });
    }
    dir.extend_files(vec![AudioFile::default()]);
    dir.last_modified = 47;

    // TODO need methods on dir to add files
    //for _ in 0..3 {
    //    dir.extra.push(ExtraFile::default());
    //}

    dir.db_insert(&db).await.unwrap();

    assert_eq!(dir.id.unwrap(), 1);
    assert_eq!(dir.files().len(), 5);
    assert_eq!(dir.files()[2].id.unwrap(), 3);
    //assert_eq!(dir.extra.len(), 3);

    drop(dir);

    let dirs = AudioDir::get_audio_dirs(&db).await;
    assert_eq!(dirs.len(), 1);
    assert_eq!(dirs[0].last_modified, 47);

    let files = AudioDir::get_audio_files(&db, 1).await;
    println!("{:#?}", files);
    assert_eq!(files.len(), 5);
    assert_eq!(files[3].file_size, Some(42));
}
