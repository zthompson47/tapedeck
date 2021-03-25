create table audio_dir(
    id integer primary key not null,
    url text unique,
    path blob unique
);
create table audio_file(
    id integer primary key not null,
    url text unique,
    path blob unique,
    mime_type text
);
create table extra_file(
    id integer primary key not null,
    path text not null unique,
    mime_type text
);
create table audio_dir_audio_file(
    audio_dir_id integer not null,
    audio_file_id integer not null,
    foreign key(audio_dir_id) references audio_dir(id),
    foreign key(audio_file_id) references audio_file(id)
);
create table audio_dir_extra_file(
    audio_dir_id integer not null,
    extra_file_id integer not null,
    foreign key(audio_dir_id) references audio_dir(id),
    foreign key(extra_file_id) references extra_file(id)
);

/*
create table audio_file(
    id integer primary key not null,
    path text not null unique,
    mime_type text
);
*/
