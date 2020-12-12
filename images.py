from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable, List, Optional
from pathlib import Path
import logging
import os

import matplotlib.pyplot as plt
import numpy as np
import sqlite3


@dataclass(frozen=True)
class Image:
    id: int
    filepath: str
    is_described: bool

    @lru_cache(maxsize=None)  # TODO: replace with functools.cache with Python3.9
    def load(self):
        with np.load(self.filepath) as file_data:
            return file_data.get(file_data.files[0])[0]


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

    def add_images(self, file_paths: Iterable[str]) -> None:
        self.db_connection.executemany(
            "INSERT INTO images (filepath, is_described, is_being_described)"
            " VALUES (?, ?, ?)",
            [(path, 0, 0) for path in file_paths],
        )
        self.db_connection.commit()

    @staticmethod
    def _image_from_db_row(row):
        return Image(row["image_id"], row["filepath"], row["is_described"])

    def fetch_image(self, id) -> Image:
        row = self.db_connection.execute(
            "SELECT image_id, filepath, is_described FROM images WHERE image_id=?",
            (id,),
        ).fetchone()
        if row is None:
            raise ImagesDatabaseError(f"Image with id={id} does not exist in the DB")
        return self._image_from_db_row(row)

    def fetch_images(self, *, described: Optional[bool] = None) -> List[Image]:
        query_sql = "SELECT image_id, filepath, is_described FROM images"
        query_params = ()
        if described is not None:
            query_sql += " WHERE is_described=?"
            query_params = (described,)
        rows = self.db_connection.execute(query_sql, query_params).fetchall()
        return [self._image_from_db_row(row) for row in rows]

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
    def __init__(self, source_path: Path, dest_path: Path) -> None:
        super().__init__()
        self.source_path = source_path
        self.dest_path = dest_path
        # self._db = ImagesDatabase()
        self._put_new_files_in_db()

    @property
    def _db(self):
        return ImagesDatabase()

    def _put_new_files_in_db(self):
        new_files = self._find_new_files()
        logging.info(f"Putting {len(new_files)} new files in the DB")
        self._db.add_images(new_files)

    def _find_new_files(self) -> Iterable[str]:
        logging.info("Searching for new files...")
        dir_paths = set(self._find_all_files())
        db_paths = {i.filepath for i in self._db.fetch_images()}
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

    def get_images(self, described: Optional[bool] = None) -> Iterable[Image]:
        return self._db.fetch_images(described=described)

    def add_description(self, d: Description) -> None:
        self._db.add_description(d)

    def get_description(self, image_id: int, description_id: int) -> Description:
        try:
            return self._db.fetch_description(image_id, description_id)
        except ImagesDatabaseError as e:
            raise DescriptionNotExistsError(image_id, description_id) from e

    def get_descriptions(self, image_id: int) -> Iterable[Description]:
        return self._db.fetch_descriptions(image_id)
