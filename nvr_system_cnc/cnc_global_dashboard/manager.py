# Global Dashboard Manager
# Aggregates data for the main C&C dashboard.

import logging
import asyncio

logger = logging.getLogger(__name__)

class GlobalDashboardManager:
    def __init__(self, federation_client):
        self.federation_client = federation_client
        self.global_status = {
            "total_cameras": 0,
            "total_incidents": 0,
            "sites_online": 0,
            "sites_offline": 0
        }

    async def start(self):
        logger.info("Starting Global Dashboard Manager...")
        asyncio.create_task(self._aggregate_data())

    async def _aggregate_data(self):
        """Periodically aggregates data from all connected clusters."""
        while True:
            all_statuses = self.federation_client.get_all_cluster_statuses()
            
            online = 0
            offline = 0
            total_cams = 0
            
            for name, status in all_statuses.items():
                if status.get('status') == 'ONLINE':
                    online += 1
                    # This assumes the health status includes camera counts
                    total_cams += status.get('camera_count', 0) 
                else:
                    offline += 1
            
            self.global_status['sites_online'] = online
            self.global_status['sites_offline'] = offline
            self.global_status['total_cameras'] = total_cams
            # Incident aggregation would require another API endpoint on the NVRs
            
            logger.info(f"Global status aggregated: {self.global_status}")
            await asyncio.sleep(60)

    def get_current_global_status(self):
        return self.global_status
