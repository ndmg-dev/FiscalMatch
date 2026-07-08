from minio import Minio
from minio.error import S3Error
from app.core.config import settings
import io

class StorageService:
    def __init__(self):
        self._client = None
        self.bucket_name = settings.MINIO_BUCKET

    @property
    def client(self):
        if self._client is None:
            self._client = Minio(
                settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ROOT_USER,
                secret_key=settings.MINIO_ROOT_PASSWORD,
                secure=settings.MINIO_SECURE
            )
            self._ensure_bucket()
        return self._client

    def _ensure_bucket(self):
        try:
            if not self._client.bucket_exists(self.bucket_name):
                self._client.make_bucket(self.bucket_name)
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
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def delete_company_files(self, empresa_id: str):
        from minio.deleteobjects import DeleteObject
        
        # Delete XMLs
        xml_objects = self.client.list_objects(self.bucket_name, prefix=f"xml/{empresa_id}/", recursive=True)
        xml_delete_list = [DeleteObject(obj.object_name) for obj in xml_objects]
        if xml_delete_list:
            errors = self.client.remove_objects(self.bucket_name, xml_delete_list)
            for error in errors:
                print("Error deleting xml object:", error)
                
        # Delete SPEDs
        sped_objects = self.client.list_objects(self.bucket_name, prefix=f"sped/{empresa_id}/", recursive=True)
        sped_delete_list = [DeleteObject(obj.object_name) for obj in sped_objects]
        if sped_delete_list:
            errors = self.client.remove_objects(self.bucket_name, sped_delete_list)
            for error in errors:
                print("Error deleting sped object:", error)

storage = StorageService()
