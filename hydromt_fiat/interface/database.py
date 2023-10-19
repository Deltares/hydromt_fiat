from abc import ABC, abstractmethod
from pathlib import Path


class IDatabase(ABC):
    @abstractmethod
    def __init__(self, *args: str):
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def create_database(cls, drive_path: Path) -> object:
        raise NotImplementedError

    @abstractmethod
    def write(self, filepath: Path) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete(self, filename: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_file(self, filename: str) -> Path | None:
        raise NotImplementedError
