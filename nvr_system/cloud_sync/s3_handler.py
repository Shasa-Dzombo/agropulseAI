# S3 Cloud Storage Handler

import logging
import aiobotocore
from pathlib import Path

logger = logging.getLogger(__name__)

class S3Handler:
    def __init__(self, config):
        self.config = config
        self.bucket_name = config.get('bucket_name')
        self.session = aiobotocore.get_session()
        logger.info("S3 Handler initialized.")

    async def upload_file(self, local_path: Path, remote_path: str) -> bool:
        """Uploads a single file to the S3 bucket."""
        if not self.bucket_name:
            logger.error("S3 bucket_name is not configured.")
            return False

        try:
            async with self.session.create_client(
                's3',
                aws_access_key_id=self.config.get('access_key'),
                aws_secret_access_key=self.config.get('secret_key'),
                endpoint_url=self.config.get('endpoint_url'), # For S3-compatible services like MinIO
                region_name=self.config.get('region')
            ) as client:
                with open(local_path, 'rb') as f:
                    await client.put_object(
                        Bucket=self.bucket_name,
                        Key=remote_path,
                        Body=f
                    )
            return True
        except Exception as e:
            logger.error(f"Failed to upload {local_path} to S3 bucket {self.bucket_name}: {e}", exc_info=True)
            return False
