-- create a new DB with the following command:
-- sqlite3 -batch database/images.db < database/create.sql
--
CREATE TABLE "files" (
    "file_id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "file_path" TEXT NOT NULL UNIQUE
);
CREATE TABLE "images" (
    "image_id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "file_id" INTEGER NOT NULL,
    "frame" INTEGER NOT NULL,
    "described_filename" TEXT,
    "is_described" INTEGER NOT NULL CHECK(
        is_described >= 0
        and is_described <= 1
    ),
    "is_being_described" INTEGER NOT NULL CHECK(
        is_being_described >= 0
        and is_being_described <= 1
    ),
    FOREIGN KEY("file_id") REFERENCES "files"("file_id"),
    UNIQUE("file_id", "frame")
);
CREATE TABLE "descriptions" (
    "description_id" INTEGER NOT NULL,
    "image_id" INTEGER NOT NULL,
    "start_x" INTEGER NOT NULL,
    "start_y" INTEGER NOT NULL,
    "end_x" INTEGER NOT NULL,
    "end_y" INTEGER NOT NULL,
    FOREIGN KEY("image_id") REFERENCES "images"("image_id"),
    PRIMARY KEY("image_id", "description_id")
);