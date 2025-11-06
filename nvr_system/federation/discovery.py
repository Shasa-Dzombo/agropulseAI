# Node Discovery using mDNS (zeroconf)

import logging
import socket
from zeroconf import ServiceInfo, Zeroconf, ServiceBrowser
import json

logger = logging.getLogger(__name__)

class NodeDiscovery:
    def __init__(self, node_name, node_type, api_port):
        self.node_name = node_name
        self.node_type = node_type
        self.api_port = api_port
        self.service_type = "_agropulse-nvr._tcp.local."
        self.zeroconf = Zeroconf()
        self.service_info = None
        self.browser = None
        self.update_callback = None

    async def start(self, update_callback):
        """Registers the local service and starts browsing for others."""
        self.update_callback = update_callback
        
        # Register this node
        properties = {
            'name': self.node_name,
            'type': self.node_type,
            'port': str(self.api_port)
        }
        
        self.service_info = ServiceInfo(
            self.service_type,
            f"{self.node_name}.{self.service_type}",
            addresses=[socket.inet_aton("127.0.0.1")], # This will be replaced by actual IPs
            port=self.api_port,
            properties={k: v.encode('utf-8') for k, v in properties.items()},
            server=f"{self.node_name}.local."
        )
        
        self.zeroconf.register_service(self.service_info)
        logger.info(f"Registered mDNS service: {self.node_name} ({self.node_type})")
        
        # Start browsing for other nodes
        self.browser = ServiceBrowser(self.zeroconf, self.service_type, listener=self)
        logger.info("Started browsing for other NVR nodes.")

    async def stop(self):
        """Unregisters the service and closes zeroconf."""
        if self.service_info:
            self.zeroconf.unregister_service(self.service_info)
        if self.browser:
            self.browser.cancel()
        self.zeroconf.close()
        logger.info("mDNS discovery stopped.")

    def remove_service(self, zeroconf, type, name):
        logger.info(f"Service {name} removed")
        info = zeroconf.get_service_info(type, name)
        if info:
            node_info = self._decode_info(info)
            self.update_callback(node_info, is_removal=True)

    def add_service(self, zeroconf, type, name):
        info = zeroconf.get_service_info(type, name)
        logger.info(f"Service {name} added, info: {info}")
        if info:
            node_info = self._decode_info(info)
            self.update_callback(node_info, is_removal=False)

    def update_service(self, zeroconf, type, name):
        info = zeroconf.get_service_info(type, name)
        logger.info(f"Service {name} updated, info: {info}")
        if info:
            node_info = self._decode_info(info)
            self.update_callback(node_info, is_removal=False)

    def _decode_info(self, info: ServiceInfo) -> dict:
        """Decodes ServiceInfo into a dictionary."""
        props = {k.decode(): v.decode() for k, v in info.properties.items()}
        return {
            "name": props.get('name'),
            "node_type": props.get('type', 'STANDALONE'),
            "ip_address": socket.inet_ntoa(info.addresses[0]),
            "api_port": info.port
        }
