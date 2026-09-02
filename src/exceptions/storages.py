class BaseS3Error(Exception):

    def __init__(self, message: str = "An S3 storage error occurred.") -> None:
        super().__init__(message)


class S3ConnectionError(BaseS3Error):

    def __init__(self, message: str = "S3 bucket not found.") -> None:
        super().__init__(message)


class S3FileUploadError(BaseS3Error):

    def __init__(self, message: str = "Failed to upload file to S3.") -> None:
        super().__init__(message)


class S3FileNotFoundError(BaseS3Error):

    def __init__(self, message: str = "Requested file not found in S3.") -> None:
        super().__init__(message)
