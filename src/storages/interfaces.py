from abc import ABC, abstractmethod


class S3StorageInterface(ABC):

    @abstractmethod
    async def upload_file(self, file_name: str, file_data: bytes | bytearray, content_type: str) -> None:
        pass

    @abstractmethod
    async def delete_file(self, file_name: str) -> None:
        pass

    @abstractmethod
    async def get_file_url(self, file_name: str) -> str:
        pass
