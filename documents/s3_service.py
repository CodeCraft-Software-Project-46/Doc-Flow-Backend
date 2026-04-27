import boto3
from django.conf import settings

class S3Service:
    def __init__(self):
        # Connect to AWS using your settings
        self.s3 = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )
        self.bucket_name = settings.AWS_STORAGE_BUCKET_NAME

    def upload_file_bytes(self, file_bytes, file_name, content_type):
        """
        Takes raw binary data from Celery and uploads it directly to S3.
        """
        try:
            # We organize them into a 'secure-archive' folder inside the bucket
            s3_path = f"secure-archive/{file_name}"
            
            self.s3.put_object(
                Bucket=self.bucket_name,
                Key=s3_path,
                Body=file_bytes,
                ContentType=content_type
            )
            
            # Return the exact URL where the file now lives forever
            file_url = f"https://{self.bucket_name}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/{s3_path}"
            return file_url
            
        except Exception as e:
            print(f"❌ AWS S3 Upload failed: {str(e)}")
            raise e