from minio import Minio
from minio.error import S3Error
from app.core.config import settings
import io

class StorageService:
    def __init__(self):
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ROOT_USER,
            secret_key=settings.MINIO_ROOT_PASSWORD,
            secure=settings.MINIO_SECURE
        )
        self.bucket_name = settings.MINIO_BUCKET
        self._ensure_bucket()

    def _ensure_bucket(self):
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
        except S3Error as e:
            print(f"Error checking/creating bucket: {e}")

    def upload_file(self, object_name: str, file_data: bytes) -> str:
        data_stream = io.BytesIO(file_data)
        self.client.put_object(
            self.bucket_name,
            object_name,
            data_stream,
            length=len(file_data)
        )
        return object_name

    def upload_stream(self, object_name: str, stream, length: int) -> str:
        self.client.put_object(
            self.bucket_name,
            object_name,
            stream,
            length=length,
            part_size=10*1024*1024
        )
        return object_name

    def get_file(self, object_name: str) -> bytes:
        response = self.client.get_object(self.bucket_name, object_name)
        data = response.read()
        response.close()
        response.release_conn()
        return data

storage = StorageService()
