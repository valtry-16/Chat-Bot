create table if not exists users (
    id varchar(64) primary key,
    email varchar(255) not null unique,
    name varchar(255),
    created_at timestamptz default now()
);

create table if not exists conversations (
    id bigserial primary key,
    user_id varchar(64) not null references users(id) on delete cascade,
    created_at timestamptz default now()
);

create table if not exists messages (
    id bigserial primary key,
    conversation_id bigint not null references conversations(id) on delete cascade,
    role varchar(16) not null,
    content text not null,
    timestamp timestamptz default now()
);

create table if not exists user_memory (
    id bigserial primary key,
    user_id varchar(64) not null references users(id) on delete cascade,
    memory_text text not null,
    importance real not null default 0.5,
    created_at timestamptz default now()
);

create table if not exists knowledge_cache (
    id bigserial primary key,
    topic varchar(255) not null,
    content text not null,
    source varchar(120) not null,
    created_at timestamptz default now()
);

create index if not exists idx_knowledge_cache_topic on knowledge_cache(topic);
