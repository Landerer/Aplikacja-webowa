from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable, List, Optional
from pathlib import Path
import io
import logging
import os
import sys

import matplotlib.pyplot as plt
import numpy as np
import sqlite3


@dataclass(frozen=True)
class File:
    id: int
    file_path: str


@dataclass(frozen=True)
class Image:
    NPZ_FRAME_MULTIPLIER = 1_000_000
    id: int
    file: File
    frame: int
    is_described: bool

    @lru_cache(maxsize=None)  # TODO: replace with functools.cache with Python3.9
    def load(self):
        with np.load(self.file.file_path) as file_data:
            npz_file = file_data.files[self.frame // self.NPZ_FRAME_MULTIPLIER]
            npz_frame = self.frame % self.NPZ_FRAME_MULTIPLIER
            logging.info(
                "Loading NPZ %s file %s frame %d",
                self.file.file_path,
                npz_file,
                npz_frame,
            )
            return file_data.get(npz_file)[npz_frame]

    def asPng(self):
        file_object = io.BytesIO()
        plt.imsave(file_object, self.load(), cmap="viridis")
        file_object.seek(0)
        return file_object


@dataclass(frozen=True)
class Description:
    id: int
    image_id: int
    x: int
    y: int
    width: int
    height: int


class ImagesDatabaseError(RuntimeError):
    pass


class ImagesDatabase:
    DATABASE_PATH = "database/images.db"
    CREATE_DB_SCRIPT = "database/create.sql"

    def __init__(self) -> None:
        super().__init__()

        db_exists = os.path.isfile(self.DATABASE_PATH)
        self.db_connection = sqlite3.connect(self.DATABASE_PATH)
        self.db_connection.row_factory = sqlite3.Row
        if not db_exists:
            self.create_tables()

    def create_tables(self):
        with open(self.CREATE_DB_SCRIPT) as f:
            sqls = f.read()
        self.db_connection.executescript(sqls)
        self.db_connection.commit()

    ### files ###

    def add_file(self, file_path: str) -> int:
        cursor = self.db_connection.execute(
            "INSERT INTO files (file_path) VALUES (?)", (file_path,)
        )
        file_id = cursor.lastrowid
        self.db_connection.commit()
        return file_id

    @staticmethod
    def _file_from_db_row(row):
        return File(row["file_id"], row["file_path"])

    def fetch_files(self) -> List[File]:
        rows = self.db_connection.execute(
            "SELECT file_id, file_path FROM files"
        ).fetchall()
        return [self._file_from_db_row(row) for row in rows]

    ### images ###

    def add_images(self, file_id, frames: Iterable[int]) -> None:
        self.db_connection.executemany(
            "INSERT INTO images"
            " (file_id, frame, is_described, is_being_described)"
            " VALUES (?, ?, 0, 0)",
            [(file_id, frame) for frame in frames],
        )
        self.db_connection.commit()

    @staticmethod
    def _image_from_db_row(row):
        return Image(
            row["image_id"],
            File(row["file_id"], row["file_path"]),
            row["frame"],
            row["is_described"],
        )

    def fetch_image(self, id) -> Image:
        row = self.db_connection.execute(
            "SELECT image_id, file_id, file_path, frame, is_described"
            " FROM images"
            " NATURAL JOIN files"
            " WHERE image_id=?",
            (id,),
        ).fetchone()
        if row is None:
            raise ImagesDatabaseError(f"Image with id={id} does not exist in the DB")
        return self._image_from_db_row(row)

    def fetch_images(self, *, is_described: Optional[bool] = None) -> List[Image]:
        query_sql = (
            "SELECT image_id, file_id, file_path, frame, is_described"
            " FROM images"
            " NATURAL JOIN files"
            + (" WHERE is_described=?" if is_described is not None else "")
            + " ORDER BY image_id"
        )
        query_params = (is_described,) if is_described is not None else ()

        rows = self.db_connection.execute(query_sql, query_params).fetchall()
        return [self._image_from_db_row(row) for row in rows]

    def update_image(self, image_id: int, is_described: bool) -> None:
        self.db_connection.execute(
            "UPDATE images SET is_described=? WHERE image_id=?",
            (is_described, image_id),
        )
        self.db_connection.commit()

    ### descriptions ###

    def add_description(self, d: Description) -> None:
        self.db_connection.execute(
            "INSERT INTO descriptions (description_id, image_id, start_x, start_y, end_x, end_y)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (d.id, d.image_id, d.x, d.y, d.x + d.width, d.y + d.height),
        )
        self.db_connection.commit()

    @staticmethod
    def _description_from_db_row(image_id: int, description_id: int, row):
        return Description(
            description_id,
            image_id,
            x=int(row["start_x"]),
            y=int(row["start_y"]),
            width=int(row["end_x"]) - int(row["start_x"]),
            height=int(row["end_y"]) - int(row["start_y"]),
        )

    def fetch_description(self, image_id: int, description_id: int) -> Description:
        row = self.db_connection.execute(
            "SELECT start_x, start_y, end_x, end_y"
            " FROM descriptions WHERE image_id=? AND description_id=?",
            (image_id, description_id),
        ).fetchone()
        if row is None:
            raise ImagesDatabaseError(
                f"Description with id={description_id}"
                " for image with id={image_id} does not exist in the DB"
            )
        return self._description_from_db_row(image_id, description_id, row)

    def fetch_descriptions(self, image_id: int) -> List[Image]:
        rows = self.db_connection.execute(
            "SELECT description_id, start_x, start_y, end_x, end_y"
            " FROM descriptions WHERE image_id=?",
            (image_id,),
        ).fetchall()
        return [
            self._description_from_db_row(image_id, row["description_id"], row)
            for row in rows
        ]

    def delete_description(self, image_id: int, description_id: int) -> None:
        self.db_connection.execute(
            "DELETE FROM descriptions WHERE image_id=? AND description_id=?",
            (image_id, description_id),
        )
        self.db_connection.commit()

    def delete_descriptions(self, image_id: int) -> None:
        self.db_connection.execute(
            "DELETE FROM descriptions WHERE image_id=?", (image_id,)
        )
        self.db_connection.commit()


class ImageNotExistsError(RuntimeError):
    def __init__(self, id) -> None:
        super().__init__()
        self.id = id

    def __str__(self) -> str:
        return f"Image with id={self.id} does not exist"


class DescriptionNotExistsError(RuntimeError):
    def __init__(self, image_id, description_id) -> None:
        super().__init__()
        self.image_id = image_id
        self.description_id = description_id

    def __str__(self) -> str:
        return (
            f"Description with id={self.description_id} for"
            f" image with id={self.image_id} does not exist"
        )


class Images:
    DESCRIPTION_PNG_COLOR = "red"
    MAX_FRAMES_FROM_NPZ = 3  # sys.maxsize

    def __init__(self, source_path: Path, dest_path: Path) -> None:
        super().__init__()
        self.source_path = source_path
        self.dest_path = dest_path
        self._put_new_images_in_db()

    @property
    def _db(self):
        return ImagesDatabase()

    def _put_new_images_in_db(self):
        new_files = self._find_new_files()
        logging.info(f"Putting {len(new_files)} new files in the DB")
        for file_path in new_files:
            file_id = self._db.add_file(file_path)
            # add all NPZ frames
            with np.load(file_path) as npz:
                for npz_count, npz_file in enumerate(npz.files):
                    frame_count_start = Image.NPZ_FRAME_MULTIPLIER * npz_count
                    frame_count = min(len(npz.get(npz_file)), self.MAX_FRAMES_FROM_NPZ)
                    self._db.add_images(file_id, range(frame_count_start, frame_count))

    def _find_new_files(self) -> Iterable[str]:
        logging.info("Searching for new files...")
        dir_paths = set(self._find_all_files())
        db_paths = {i.file_path for i in self._db.fetch_files()}
        return dir_paths - db_paths

    def _find_all_files(self) -> Iterable[str]:
        for root, dirs, files in os.walk(str(self.source_path)):
            for file in files:
                yield str(Path(root) / Path(file))

    def get_image(self, image_id: int) -> Image:
        try:
            return self._db.fetch_image(image_id)
        except ImagesDatabaseError as e:
            raise ImageNotExistsError(image_id) from e

    def get_images(self, is_described: Optional[bool] = None) -> Iterable[Image]:
        return self._db.fetch_images(is_described=is_described)

    def add_description(self, d: Description) -> None:
        self._db.add_description(d)

    def get_description(self, image_id: int, description_id: int) -> Description:
        try:
            return self._db.fetch_description(image_id, description_id)
        except ImagesDatabaseError as e:
            raise DescriptionNotExistsError(image_id, description_id) from e

    def get_descriptions(self, image_id: int) -> Iterable[Description]:
        return self._db.fetch_descriptions(image_id)

    def delete_description(self, image_id: int, description_id: int) -> None:
        self._db.delete_description(image_id, description_id)

    def delete_descriptions(self, image_id: int) -> None:
        self._db.delete_descriptions(image_id)

    def save_image(self, image_id: int) -> None:
        self._db.update_image(image_id, is_described=True)
        image = self._db.fetch_image(image_id)
        image_filename = Path(image.file.file_path).name
        saved_filepath = Path(self.dest_path) / f"{image_filename}_{image.frame}.png"
        logging.info("Saving image to %s", saved_filepath)
        with open(saved_filepath, "wb") as f:
            f.write(image.asPng().read())
