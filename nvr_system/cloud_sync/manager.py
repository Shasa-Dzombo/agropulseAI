# Cloud Sync Manager
# Manages a queue of files to be backed up to a cloud storage provider.

import logging
import asyncio
from .s3_handler import S3Handler

logger = logging.getLogger(__name__)

class CloudSyncManager:
    def __init__(self, config, db_manager, alert_manager):
        self.config = config.get('cloud_sync', {})
        self.db_manager = db_manager
        self.alert_manager = alert_manager
        
        self.is_enabled = self.config.get('enabled', False)
        self.is_running = False
        self.upload_queue = asyncio.Queue()
        
        provider = self.config.get('provider', 's3').lower()
        if provider == 's3':
            self.handler = S3Handler(self.config.get('s3', {}))
        else:
            logger.error(f"Unsupported cloud provider '{provider}'. Disabling cloud sync.")
            self.is_enabled = False
            
        logger.info(f"Cloud Sync Manager initialized. Enabled: {self.is_enabled}")

    async def start(self):
        if not self.is_enabled:
            logger.info("Cloud Sync is disabled. Skipping start.")
            return
        
        self.is_running = True
        asyncio.create_task(self._worker())
        logger.info("Cloud Sync worker started.")

    async def stop(self):
        if not self.is_running:
            return
        self.is_running = False
        await self.upload_queue.put(None) # Sentinel to stop the worker
        logger.info("Cloud Sync worker stopped.")

    async def queue_upload(self, event_id, local_path, object_classes):
        """Adds a file to the upload queue if it meets criteria."""
        if not self.is_enabled:
            return

        # Check if the event's detected objects warrant an upload
        upload_classes = self.config.get('upload_on_object', [])
        if not any(cls in upload_classes for cls in object_classes):
            logger.debug(f"Event {event_id} does not contain objects for cloud upload. Skipping.")
            return

        await self.upload_queue.put({'event_id': event_id, 'local_path': local_path})
        logger.info(f"Queued event '{event_id}' for cloud backup.")
        await self.db_manager.update_event_cloud_status(event_id, 'QUEUED')

    async def _worker(self):
        """The worker task that processes the upload queue."""
        while self.is_running:
            item = await self.upload_queue.get()
            if item is None: # Sentinel
                break

            event_id = item['event_id']
            local_path = item['local_path']
            
            try:
                logger.info(f"Starting cloud upload for event '{event_id}'...")
                await self.db_manager.update_event_cloud_status(event_id, 'UPLOADING')
                
                remote_path = f"events/{event_id}/{local_path.name}"
                success = await self.handler.upload_file(local_path, remote_path)
                
                if success:
                    logger.info(f"Successfully uploaded event '{event_id}' to the cloud.")
                    await self.db_manager.update_event_cloud_status(event_id, 'ARCHIVED')
                    
                    # Optionally, delete local file after successful upload
                    if self.config.get('delete_after_upload', False):
                        local_path.unlink()
                        logger.info(f"Deleted local file for event '{event_id}'.")
                else:
                    logger.error(f"Cloud upload failed for event '{event_id}'. Will retry later.")
                    await self.db_manager.update_event_cloud_status(event_id, 'FAILED')
                    # Simple retry logic: put it back in the queue
                    await asyncio.sleep(300) # Wait 5 mins before retry
                    await self.upload_queue.put(item)

            except Exception as e:
                logger.error(f"Exception in cloud sync worker for event {event_id}: {e}", exc_info=True)
                await self.db_manager.update_event_cloud_status(event_id, 'FAILED')
            
            self.upload_queue.task_done()
