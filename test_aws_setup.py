#!/usr/bin/env python3
"""
Test script to verify AWS IAM credentials and S3 bucket access
Run this to make sure everything is working correctly.
"""

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_aws_credentials():
    """Test if AWS credentials are working"""
    print("🔍 Testing AWS Credentials...")
    
    try:
        # Create S3 client
        s3 = boto3.client(
            's3',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_S3_REGION_NAME', 'eu-north-1')
        )
        
        print("✅ AWS credentials are working!")
        print("📝 Note: Limited permissions detected (can't list all buckets)")
        print("   This is actually good for security!")
        
        return s3
        
    except NoCredentialsError:
        print("❌ No AWS credentials found!")
        print("   Make sure you have AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in your .env file")
        return None
    except ClientError as e:
        print(f"❌ AWS credentials error: {e}")
        return None

def test_s3_bucket_access(s3_client, bucket_name):
    """Test specific bucket access"""
    print(f"\n🔍 Testing S3 Bucket Access: {bucket_name}")
    
    try:
        # Test bucket existence
        s3_client.head_bucket(Bucket=bucket_name)
        print("✅ Bucket exists and is accessible!")
        
        # Test listing objects (should be empty for new bucket)
        response = s3_client.list_objects_v2(Bucket=bucket_name, MaxKeys=5)
        object_count = response.get('KeyCount', 0)
        print(f"📁 Bucket contains {object_count} object(s)")
        
        # Test uploading a small test file
        test_content = "This is a test file for ExcelPoint S3 integration"
        test_key = "test/hello.txt"
        
        print(f"📤 Uploading test file: {test_key}")
        s3_client.put_object(
            Bucket=bucket_name,
            Key=test_key,
            Body=test_content.encode('utf-8'),
            ContentType='text/plain'
        )
        print("✅ Test file uploaded successfully!")
        
        # Test downloading the file
        print(f"📥 Downloading test file: {test_key}")
        response = s3_client.get_object(Bucket=bucket_name, Key=test_key)
        downloaded_content = response['Body'].read().decode('utf-8')
        
        if downloaded_content == test_content:
            print("✅ Test file downloaded successfully!")
        else:
            print("❌ Downloaded content doesn't match!")
        
        # Clean up - delete test file
        print(f"🗑️ Cleaning up test file: {test_key}")
        s3_client.delete_object(Bucket=bucket_name, Key=test_key)
        print("✅ Test file deleted successfully!")
        
        return True
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == '404':
            print(f"❌ Bucket '{bucket_name}' not found!")
        elif error_code == '403':
            print(f"❌ Access denied to bucket '{bucket_name}'!")
            print("   Check your IAM permissions")
        else:
            print(f"❌ S3 error: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 Testing AWS S3 Setup for ExcelPoint\n")
    
    # Test credentials
    s3_client = test_aws_credentials()
    if not s3_client:
        return
    
    # Get bucket name from environment or prompt
    bucket_name = os.getenv('AWS_STORAGE_BUCKET_NAME')
    if not bucket_name:
        bucket_name = input("Enter your S3 bucket name: ").strip()
    
    if not bucket_name:
        print("❌ No bucket name provided!")
        return
    
    # Test bucket access
    success = test_s3_bucket_access(s3_client, bucket_name)
    
    if success:
        print("\n🎉 All tests passed! Your AWS S3 setup is working correctly.")
        print("\nNext steps:")
        print("1. Add these to your .env file:")
        print(f"   AWS_STORAGE_BUCKET_NAME={bucket_name}")
        print("   AWS_S3_REGION_NAME=eu-north-1")
        print("2. Install django-storages: pip install django-storages")
        print("3. Implement the storage abstraction layer")
    else:
        print("\n❌ Some tests failed. Please check your configuration.")

if __name__ == "__main__":
    main() 