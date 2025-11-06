# ONVIF Client Manager
# Discovers and interacts with ONVIF-compliant cameras.

import logging
import asyncio
from onvif import ONVIFCamera

logger = logging.getLogger(__name__)

class ONVIFManager:
    def __init__(self, config):
        self.config = config.get('onvif', {})
        self.is_enabled = self.config.get('enabled', False)
        logger.info(f"ONVIF Manager initialized. Enabled: {self.is_enabled}")

    async def discover_cameras(self):
        """Discovers ONVIF cameras on the local network."""
        if not self.is_enabled: return []
        # This is a blocking operation and should be run in an executor
        # For simplicity, we'll just note that it's a placeholder.
        logger.info("ONVIF discovery is a blocking process and is placeholder here.")
        # In a real implementation:
        # loop = asyncio.get_event_loop()
        # cameras = await loop.run_in_executor(None, onvif_discover_function)
        return []

    async def get_rtsp_uri(self, ip, user, password):
        """Gets the RTSP stream URI from an ONVIF camera."""
        if not self.is_enabled: return None
        
        try:
            cam = ONVIFCamera(ip, 80, user, password)
            await cam.update_xaddrs()
            media_service = cam.create_media_service()
            profiles = await media_service.GetProfiles()
            # Get the stream URI for the first profile
            uri = await media_service.GetStreamUri({
                'StreamSetup': {'Stream': 'RTP-Unicast', 'Transport': {'Protocol': 'RTSP'}},
                'ProfileToken': profiles[0].token
            })
            return uri.Uri
        except Exception as e:
            logger.error(f"Failed to get ONVIF stream URI from {ip}: {e}")
            return None
