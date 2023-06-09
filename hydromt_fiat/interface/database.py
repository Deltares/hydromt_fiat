from abc import ABCMeta, abstractmethod


class IDatabase(ABCMeta):
    
    def __init__(self):
        self.location: str
    
    @abstractmethod
    @classmethod
    def create_database(cls):
        raise NotImplementedError
        
    
    @abstractmethod
    def add_file(self):
        raise NotImplementedError
        
    @abstractmethod
    def delete_file(self):
        raise NotImplementedError
    
    @abstractmethod
    def copy_file(self):
        raise NotImplementedError
    
    @abstractmethod
    def select_file(self):
        raise NotImplementedError        raise NotImplementedError