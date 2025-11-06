# Federation Manager
# Handles node discovery, state synchronization, and inter-node communication.

import logging
import asyncio
from .discovery import NodeDiscovery
from .protocol import Node, NodeStatus, NodeType

logger = logging.getLogger(__name__)

class FederationManager:
    def __init__(self, config, db_manager, alert_manager):
        self.config = config.get('federation', {})
        self.db_manager = db_manager
        self.alert_manager = alert_manager
        
        self.node_type = NodeType[self.config.get('node_type', 'STANDALONE').upper()]
        self.node_name = self.config.get('node_name', 'agropulse-nvr')
        self.is_running = False
        
        self.discovery = NodeDiscovery(
            node_name=self.node_name,
            node_type=self.node_type.value,
            api_port=config.get('api', {}).get('port', 8000)
        )
        
        self.cluster_nodes = {} # Discovered nodes: {name: Node}
        logger.info(f"Federation Manager initialized as {self.node_type.name} node: '{self.node_name}'")

    async def start(self):
        if not self.config.get('enabled', False):
            logger.info("Federation is disabled in configuration. Skipping start.")
            return
            
        self.is_running = True
        await self.discovery.start(self.handle_node_update)
        asyncio.create_task(self._health_check_loop())
        logger.info("Federation services started.")

    async def stop(self):
        if not self.is_running:
            return
        self.is_running = False
        await self.discovery.stop()
        logger.info("Federation services stopped.")

    def handle_node_update(self, node_info: dict, is_removal: bool):
        """Callback from NodeDiscovery to add/update/remove nodes."""
        name = node_info.get('name')
        if not name: return

        if is_removal:
            if name in self.cluster_nodes:
                del self.cluster_nodes[name]
                logger.info(f"Federation node '{name}' removed from cluster.")
            return

        node = Node(**node_info)
        if name not in self.cluster_nodes or self.cluster_nodes[name] != node:
            self.cluster_nodes[name] = node
            logger.info(f"Federation node '{name}' discovered/updated: {node.ip_address}:{node.api_port}")

    async def _health_check_loop(self):
        """Periodically pings other nodes to check their health."""
        while self.is_running:
            await asyncio.sleep(self.config.get('health_check_interval', 60))
            
            # This is a simplified health check. In a real system, you'd make an API call.
            for name, node in list(self.cluster_nodes.items()):
                # A more robust implementation would use aiohttp to call a /api/health endpoint
                # For now, we just assume they are online if they are in the discovery list.
                # If a node goes offline, mDNS should eventually remove it.
                pass
            
    def get_cluster_status(self):
        """Returns the status of all nodes in the cluster."""
        return {name: node.dict() for name, node in self.cluster_nodes.items()}

    def get_primary_node(self):
        """Finds and returns the primary node in the cluster."""
        for node in self.cluster_nodes.values():
            if node.node_type == NodeType.PRIMARY:
                return node
        return None
