# IPFS Client
# Interacts with an InterPlanetary File System node.

import logging
import asyncio
import httpx # Using http client, ipfs-http-client is another option

logger = logging.getLogger(__name__)

class IPFSClient:
    def __init__(self, config):
        self.api_addr = config.get('api_addr', 'http://127.0.0.1:5001')
        self.client = httpx.AsyncClient(base_url=self.api_addr)

    async def connect(self):
        try:
            response = await self.client.post('/api/v0/version')
            response.raise_for_status()
            logger.info(f"IPFS client connected successfully to {self.api_addr}. Version: {response.json()['Version']}")
        except Exception as e:
            logger.error(f"Failed to connect to IPFS node: {e}")

    async def disconnect(self):
        await self.client.aclose()
        logger.info("IPFS client disconnected.")

    async def add_file(self, file_path):
        """Adds a file to IPFS and returns its hash."""
        try:
            with open(file_path, 'rb') as f:
                files = {'file': f}
                response = await self.client.post('/api/v0/add', files=files)
                response.raise_for_status()
                return response.json()['Hash']
        except Exception as e:
            logger.error(f"Failed to add file to IPFS: {e}")
            return None
