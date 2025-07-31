from abc import ABC, abstractmethod
from django.core.files.storage import default_storage
from django.conf import settings
import os

class StorageService(ABC):
    """Abstract base class for storage operations"""
    
    @abstractmethod
    def save_file(self, file_obj, path):
        """Save a file to storage"""
        pass
    
    @abstractmethod
    def get_file_url(self, path):
        """Get the URL for a file"""
        pass
    
    @abstractmethod
    def delete_file(self, path):
        """Delete a file from storage"""
        pass
    
    @abstractmethod
    def file_exists(self, path):
        """Check if a file exists"""
        pass

class LocalStorageService(StorageService):
    """Local file storage implementation"""
    
    def save_file(self, file_obj, path):
        """Save file using Django's default storage"""
        # Handle both file objects and file paths
        if hasattr(file_obj, 'read'):
            # It's a file object, save it directly
            return default_storage.save(path, file_obj)
        else:
            # It's a file path, open and save
            with open(file_obj, 'rb') as f:
                return default_storage.save(path, f)
    
    def get_file_url(self, path):
        """Get file URL using Django's default storage"""
        return default_storage.url(path)
    
    def delete_file(self, path):
        """Delete file using Django's default storage"""
        if default_storage.exists(path):
            default_storage.delete(path)
    
    def file_exists(self, path):
        """Check if file exists using Django's default storage"""
        return default_storage.exists(path)

class S3StorageService(StorageService):
    """S3 storage implementation"""
    
    def __init__(self):
        import boto3
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )
        self.bucket_name = settings.AWS_STORAGE_BUCKET_NAME
    
    def save_file(self, file_obj, path):
        """Save file to S3"""
        try:
            # Handle different types of file objects
            if hasattr(file_obj, 'read'):
                # It's a file-like object
                if hasattr(file_obj, 'seek'):
                    file_obj.seek(0)
                self.s3_client.upload_fileobj(file_obj, self.bucket_name, path)
            elif hasattr(file_obj, 'temporary_file_path'):
                # It's a Django uploaded file with temporary path
                self.s3_client.upload_file(file_obj.temporary_file_path(), self.bucket_name, path)
            else:
                # It's a file path
                self.s3_client.upload_file(file_obj, self.bucket_name, path)
            
            return path
        except Exception as e:
            raise Exception(f"Failed to save file to S3: {str(e)}")
    
    def get_file_url(self, path):
        """Get S3 file URL"""
        return f"https://{self.bucket_name}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/{path}"
    
    def delete_file(self, path):
        """Delete file from S3"""
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=path)
        except Exception:
            # Silently fail if file doesn't exist
            pass
    
    def file_exists(self, path):
        """Check if file exists in S3"""
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=path)
            return True
        except Exception:
            return False 