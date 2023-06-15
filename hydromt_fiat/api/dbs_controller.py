import os
import shutil
from contextlib import contextmanager
from pathlib import Path

from hydromt_fiat.interface.database import IDatabase


@contextmanager
def cd(newdir: Path):
    prevdir = Path().cwd()
    os.chdir(newdir)
    try:
        yield
    finally:
        os.chdir(prevdir)


class LocalDatabase(IDatabase):
    def __init__(self, drive_path: Path):
        self.parent: Path = drive_path.parent
        self.drive: Path = drive_path

    @classmethod
    def create_database(cls, drive_path: Path) -> IDatabase:
        temp_drive = drive_path / "temp_database"
        try:
            os.makedirs(temp_drive)
        except FileExistsError:
            print("database already exists, removing all content")
            with cd(temp_drive):
                [os.remove(f) for f in os.listdir()]

        return LocalDatabase(drive_path=temp_drive)

    def write(self, filepath: Path) -> None:
        shutil.copy2(filepath, self.drive)

    def delete(self, filename: str) -> None:
        with cd(self.drive):
            if os.path.isfile(filename):
                os.remove(filename)

    def get_file(self, filename: str) -> Path | None:
        with cd(self.drive):
            if filename in os.listdir():
                return Path(os.path.abspath(filename))
        return None
