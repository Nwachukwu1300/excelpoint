"""Storage service abstraction for file management.

This module provides a unified interface for file storage operations across
different backends (local filesystem and AWS S3). It implements the Strategy
pattern to allow seamless switching between storage providers without changing
application code.

The service handles:
- File uploads and storage
- URL generation for file access
- File deletion and cleanup
- Existence checking
- Cross-platform file object handling

Key features:
- Abstract base class for consistent interface
- Local storage using Django's default storage
- S3 storage with AWS credentials
- Automatic file object type detection
- Error handling and fallback mechanisms
"""

from abc import ABC, abstractmethod
from django.core.files.storage import default_storage
from django.conf import settings
import os

class StorageService(ABC):
    """Abstract base class defining the storage service interface.
    
    This class defines the contract that all storage implementations
    must follow. It ensures consistent behavior across different
    storage backends and enables easy switching between providers.
    
    All methods are abstract and must be implemented by concrete
    storage service classes.
    """
    
    @abstractmethod
    def save_file(self, file_obj, path):
        """Save a file to storage.
        
        Args:
            file_obj: File object, file path, or Django uploaded file
            path: Destination path within the storage
            
        Returns:
            Path where the file was saved
        """
        pass
    
    @abstractmethod
    def get_file_url(self, path):
        """Get the public URL for accessing a file.
        
        Args:
            path: Path to the file in storage
            
        Returns:
            Public URL for file access
        """
        pass
    
    @abstractmethod
    def delete_file(self, path):
        """Delete a file from storage.
        
        Args:
            path: Path to the file to delete
        """
        pass
    
    @abstractmethod
    def file_exists(self, path):
        """Check if a file exists in storage.
        
        Args:
            path: Path to check
            
        Returns:
            True if file exists, False otherwise
        """
        pass

class LocalStorageService(StorageService):
    """Local filesystem storage implementation.
    
    This service uses Django's default storage backend for local
    file operations. It's suitable for development and small-scale
    deployments where files are stored on the local filesystem.
    
    The service handles various file object types and provides
    consistent error handling for local storage operations.
    """
    
    def save_file(self, file_obj, path):
        """Save file using Django's default storage.
        
        Handles both file objects and file paths, automatically
        detecting the type and using the appropriate save method.
        
        Args:
            file_obj: File object, file path, or Django uploaded file
            path: Destination path within storage
            
        Returns:
            Path where the file was saved
        """
        # Handle both file objects and file paths
        if hasattr(file_obj, 'read'):
            # It's a file object, save it directly
            return default_storage.save(path, file_obj)
        else:
            # It's a file path, open and save
            with open(file_obj, 'rb') as f:
                return default_storage.save(path, f)
    
    def get_file_url(self, path):
        """Get file URL using Django's default storage.
        
        Args:
            path: Path to the file
            
        Returns:
            URL for accessing the file
        """
        return default_storage.url(path)
    
    def delete_file(self, path):
        """Delete file using Django's default storage.
        
        Args:
            path: Path to the file to delete
        """
        if default_storage.exists(path):
            default_storage.delete(path)
    
    def file_exists(self, path):
        """Check if file exists using Django's default storage.
        
        Args:
            path: Path to check
            
        Returns:
            True if file exists, False otherwise
        """
        return default_storage.exists(path)

class S3StorageService(StorageService):
    """AWS S3 storage implementation.
    
    This service provides cloud-based file storage using Amazon S3.
    It's suitable for production deployments where scalability,
    reliability, and global access are important.
    
    The service automatically handles different file object types
    and provides robust error handling for cloud operations.
    """
    
    def __init__(self):
        """Initialize S3 client with credentials from Django settings.
        
        Creates an S3 client using AWS credentials configured in
        Django settings. The client is used for all S3 operations.
        """
        import boto3
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )
        self.bucket_name = settings.AWS_STORAGE_BUCKET_NAME
    
    def save_file(self, file_obj, path):
        """Save file to S3 bucket.
        
        Handles various file object types including Django uploaded
        files, file-like objects, and file paths. Automatically
        detects the type and uses the appropriate upload method.
        
        Args:
            file_obj: File object, Django uploaded file, or file path
            path: Destination path within the S3 bucket
            
        Returns:
            Path where the file was saved
            
        Raises:
            Exception: If S3 upload fails
        """
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
        """Get S3 file URL.
        
        Constructs the public URL for accessing a file stored in S3.
        The URL follows the standard S3 format for public bucket access.
        
        Args:
            path: Path to the file in S3
            
        Returns:
            Public S3 URL for file access
        """
        return f"https://{self.bucket_name}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/{path}"
    
    def delete_file(self, path):
        """Delete file from S3 bucket.
        
        Removes a file from the S3 bucket. The operation fails
        silently if the file doesn't exist to avoid errors during
        cleanup operations.
        
        Args:
            path: Path to the file to delete
        """
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=path)
        except Exception:
            # Silently fail if file doesn't exist
            pass 