create table audio_dir(
    id integer primary key not null,
    last_modified integer,
    location blob unique not null
);
create table audio_file(
    id integer primary key not null,
    audio_dir_id integer not null,
    file_size integer,
    mime_type text,
    location blob unique not null,
    foreign key(audio_dir_id) references audio_dir(id)
);
