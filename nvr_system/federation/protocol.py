# Data models for Federation

from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional

class NodeType(str, Enum):
    PRIMARY = "PRIMARY"
    SECONDARY = "SECONDARY"
    STANDALONE = "STANDALONE"

class NodeStatus(str, Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    DEGRADED = "DEGRADED"

class Node(BaseModel):
    name: str
    node_type: NodeType
    ip_address: str
    api_port: int
    status: NodeStatus = Field(default=NodeStatus.ONLINE)
    last_seen: Optional[str] = None
