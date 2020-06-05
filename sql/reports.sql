DROP TABLE IF EXISTS staff_reports;
DROP TABLE IF EXISTS rollbacks;

CREATE TABLE IF NOT EXISTS staff_reports(
    id          int PRIMARY KEY,
    username    text,
    type        text,
    punishment  text,
    image_links text[],
    blocks      int,
    staff       text,
    summary     text,
    happened_at date,
    reported_at timestamp DEFAULT current_timestamp,
    rollbacks   int[]
);

CREATE TABLE IF NOT EXISTS rollbacks(
    id          int PRIMARY KEY,
    username    text,
    blocks      int,
    staff       text,
    happened_at timestamp,
    created_at  timestamp DEFAULT current_timestamp,
    filled      boolean DEFAULT FALSE
);

