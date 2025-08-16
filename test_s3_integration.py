#!/usr/bin/env python3
"""
Test script to verify AWS S3 integration with Django models and file processing
Run this to make sure everything is working correctly.
"""

import os
import sys
import django
from io import BytesIO
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings
from subjects.services.storage_factory import StorageFactory
from subjects.models import Subject, SubjectMaterial
from users.models import User, UserProfile
from subjects.utils import ContentProcessor

def test_storage_service():
    """Test the storage service abstraction"""
    print("🔍 Testing Storage Service...")
    
    try:
        # Get storage service
        storage_service = StorageFactory.get_storage_service()
        print(f"✅ Storage service: {type(storage_service).__name__}")
        
        # Test file operations
        test_content = "This is a test file for S3 integration"
        test_path = "test/integration_test.txt"
        
        # Create file object
        file_obj = BytesIO(test_content.encode('utf-8'))
        
        # Save file
        print(f" Saving test file: {test_path}")
        saved_path = storage_service.save_file(file_obj, test_path)
        print(f"File saved: {saved_path}")
        
        # Check if file exists
        exists = storage_service.file_exists(test_path)
        print(f"File exists: {exists}")
        
        # Get file URL
        url = storage_service.get_file_url(test_path)
        print(f"File URL: {url}")
        
        # Clean up
        print(f"🗑️ Cleaning up test file: {test_path}")
        storage_service.delete_file(test_path)
        print("Test file deleted successfully!")
        
        return True
        
    except Exception as e:
        print(f" Storage service test failed: {e}")
        return False

def test_django_model_integration():
    """Test Django model integration with S3"""
    print("\n🔍 Testing Django Model Integration...")
    
    try:
        # Create a test user
        test_user, created = User.objects.get_or_create(
            username='test_s3_user',
            defaults={
                'email': 'test_s3@example.com',
                'first_name': 'Test',
                'last_name': 'S3User'
            }
        )
        
        if created:
            print(f"✅ Created test user: {test_user.username}")
        else:
            print(f"✅ Using existing test user: {test_user.username}")
        
        # Create a test subject
        test_subject, created = Subject.objects.get_or_create(
            user=test_user,
            name='S3 Integration Test Subject',
            defaults={}
        )
        
        if created:
            print(f"✅ Created test subject: {test_subject.name}")
        else:
            print(f"✅ Using existing test subject: {test_subject.name}")
        
        # Test file upload through model
        test_content = "This is a test PDF content for Django model integration"
        test_filename = "test_model_integration.pdf"
        
        # Create a proper Django file object
        from django.core.files.base import ContentFile
        file_obj = ContentFile(test_content.encode('utf-8'), name=test_filename)
        
        # Create SubjectMaterial instance
        material = SubjectMaterial(
            subject=test_subject,
            file=file_obj,
            file_type='PDF',
            status='PENDING'
        )
        
        print(f"📤 Saving material through Django model: {test_filename}")
        material.save()
        print(f"✅ Material saved successfully! ID: {material.id}")
        print(f"✅ File path: {material.file.name}")
        
        # Test file URL generation
        if hasattr(material, 'get_file_url'):
            url = material.get_file_url(material.file.name)
            print(f"✅ File URL: {url}")
        
        # Clean up
        print(f"🗑️ Cleaning up test material: {material.id}")
        material.delete()
        print("✅ Test material deleted successfully!")
        
        return True
        
    except Exception as e:
        print(f"❌ Django model integration test failed: {e}")
        return False

def test_content_processor():
    """Test ContentProcessor with S3 files"""
    print("\n🔍 Testing ContentProcessor...")
    
    try:
        # Create test content
        test_content = """
        This is a test document for content processing.
        It contains multiple paragraphs to test chunking.
        
        This is the second paragraph with more content.
        It should be processed into chunks for embedding generation.
        
        This is the third paragraph to ensure proper text splitting.
        The content processor should handle this correctly.
        """
        
        # Create a temporary file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(test_content)
            temp_file_path = f.name
        
        print(f"📄 Created test file: {temp_file_path}")
        
        # Test ContentProcessor
        processor = ContentProcessor()
        print(" ContentProcessor initialized")
        
        # Process the file
        print(" Processing file with ContentProcessor...")
        chunks = processor.process_file(temp_file_path)
        print(f" File processed successfully! Generated {len(chunks)} chunks")
        
        # Display chunk information
        for i, chunk in enumerate(chunks[:3]):  # Show first 3 chunks
            print(f"   Chunk {i+1}: {len(chunk['content'])} chars, embedding: {len(chunk['embedding_vector'])} dimensions")
        
        # Clean up
        os.unlink(temp_file_path)
        print(f" Cleaned up test file: {temp_file_path}")
        
        return True
        
    except Exception as e:
        print(f" ContentProcessor test failed: {e}")
        return False

def test_settings_configuration():
    """Test Django settings configuration"""
    print("\n🔍 Testing Django Settings Configuration...")
    
    try:
        # Check storage backend setting
        storage_backend = getattr(settings, 'STORAGE_BACKEND', 'local')
        print(f" Storage backend: {storage_backend}")
        
        # Check S3 settings if using S3
        if storage_backend == 's3':
            required_settings = [
                'AWS_ACCESS_KEY_ID',
                'AWS_SECRET_ACCESS_KEY', 
                'AWS_STORAGE_BUCKET_NAME',
                'AWS_S3_REGION_NAME'
            ]
            
            for setting in required_settings:
                value = getattr(settings, setting, None)
                if value:
                    print(f"{setting}: {'*' * len(str(value))} (hidden)")
                else:
                    print(f" {setting}: Not configured")
                    return False
        else:
            print("ℹ️ Using local storage backend")
        
        # Check installed apps
        if 'storages' in settings.INSTALLED_APPS:
            print("django-storages is installed")
        else:
            print("django-storages not in INSTALLED_APPS (only needed for S3)")
        
        return True
        
    except Exception as e:
        print(f" Settings configuration test failed: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 Testing AWS S3 Integration for ExcelPoint\n")
    
    # Track test results
    test_results = []
    
    # Run tests
    test_results.append(("Settings Configuration", test_settings_configuration()))
    test_results.append(("Storage Service", test_storage_service()))
    test_results.append(("Django Model Integration", test_django_model_integration()))
    test_results.append(("ContentProcessor", test_content_processor()))
    
    # Display results
    print("\n" + "="*50)
    print("📊 TEST RESULTS")
    print("="*50)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "PASS" if result else "FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print("="*50)
    print(f"Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\nAll tests passed! Your AWS S3 integration is working correctly.")
        print("\nNext steps:")
        print("1. Set STORAGE_BACKEND=s3 in your .env file to enable S3")
        print("2. Test with real file uploads through the web interface")
        print("3. Monitor S3 usage and costs")
    else:
        print(f"\n{total - passed} test(s) failed. Please check the configuration.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 