from django.conf import settings
from .storage_service import LocalStorageService, S3StorageService

class StorageFactory:
    """Factory for creating storage service instances"""
    
    @staticmethod
    def get_storage_service():
        """Get the appropriate storage service based on settings"""
        backend = getattr(settings, 'STORAGE_BACKEND', 'local')
        
        if backend == 's3':
            return S3StorageService()
        else:
            return LocalStorageService() 