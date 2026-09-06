from typing import Dict

from storages.interfaces import S3StorageInterface


class FakeS3Storage(S3StorageInterface):
    def __init__(self):
        self.storage: Dict[str, bytes] = {}


    async def upload_file(self, file_name: str, file_data: bytes | bytearray, content_type: str) -> None:
        self.storage[file_name] = file_data

    async def delete_file(self, file_name: str) -> None:
        self.storage.pop(file_name)

    async def get_file_url(self, file_name: str) -> str:
        return f"http://fake-s3.local/{file_name}"
