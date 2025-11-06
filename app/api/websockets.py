"""
WebSocket API endpoints for real-time communication.

This module provides WebSocket endpoints for:
1. Real-time notifications broadcasting
2. Live IoT sensor data streaming
3. Chat support for expert consultations
4. Farm monitoring updates
5. Chama activity notifications
6. General real-time updates

Features:
- WebSocket connection management
- Authentication via JWT tokens
- Room/channel management for grouped communications
- Broadcasting mechanisms for live updates
- Connection lifecycle management
- Message routing and filtering
- Reconnection handling
- Heartbeat/ping-pong for connection health
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, status
from sqlalchemy.orm import Session
from typing import Dict, Set, Optional, List, Any
from datetime import datetime
import json
import asyncio
import logging
from jwt import decode as jwt_decode, InvalidTokenError

from app.db_config import get_db
from app.repositories.user import UserRepository
from app.repositories.farm import FarmRepository

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["WebSocket"])

# JWT configuration (must match auth.py)
SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"


# ============================================================================
# Connection Manager
# ============================================================================

class ConnectionManager:
    """
    Manages WebSocket connections with support for:
    - User-specific connections
    - Room/channel management
    - Broadcasting to multiple connections
    - Connection tracking and cleanup
    """
    
    def __init__(self):
        # Active connections: {user_id: [websocket1, websocket2, ...]}
        self.active_connections: Dict[int, List[WebSocket]] = {}
        
        # Room subscriptions: {room_name: {user_id1, user_id2, ...}}
        self.rooms: Dict[str, Set[int]] = {}
        
        # Connection metadata: {websocket: {"user_id": int, "connected_at": datetime, ...}}
        self.connection_metadata: Dict[WebSocket, Dict[str, Any]] = {}
        
        # Global notification channel (all users)
        self.notification_subscribers: Set[int] = set()
        
        # IoT data subscribers: {device_id: {user_id1, user_id2, ...}}
        self.iot_subscribers: Dict[int, Set[int]] = {}
        
        # Chat room subscribers: {room_id: {user_id1, user_id2, ...}}
        self.chat_rooms: Dict[str, Set[int]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: int):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        
        # Add to active connections
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        
        # Store metadata
        self.connection_metadata[websocket] = {
            "user_id": user_id,
            "connected_at": datetime.utcnow(),
            "last_ping": datetime.utcnow()
        }
        
        logger.info(f"WebSocket connected: user_id={user_id}, total_connections={len(self.active_connections.get(user_id, []))}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection and cleanup subscriptions."""
        if websocket not in self.connection_metadata:
            return
        
        user_id = self.connection_metadata[websocket]["user_id"]
        
        # Remove from active connections
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            
            # Clean up if no more connections for this user
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
                
                # Remove from all subscriptions
                self.notification_subscribers.discard(user_id)
                
                # Remove from rooms
                for room_users in self.rooms.values():
                    room_users.discard(user_id)
                
                # Remove from IoT subscriptions
                for device_users in self.iot_subscribers.values():
                    device_users.discard(user_id)
                
                # Remove from chat rooms
                for chat_users in self.chat_rooms.values():
                    chat_users.discard(user_id)
        
        # Remove metadata
        del self.connection_metadata[websocket]
        
        logger.info(f"WebSocket disconnected: user_id={user_id}")
    
    async def send_personal_message(self, message: dict, user_id: int):
        """Send a message to all connections of a specific user."""
        if user_id not in self.active_connections:
            return
        
        message_json = json.dumps(message)
        disconnected = []
        
        for websocket in self.active_connections[user_id]:
            try:
                await websocket.send_text(message_json)
            except Exception as e:
                logger.error(f"Error sending to user {user_id}: {e}")
                disconnected.append(websocket)
        
        # Cleanup failed connections
        for websocket in disconnected:
            self.disconnect(websocket)
    
    async def broadcast_to_room(self, message: dict, room: str):
        """Broadcast a message to all users in a specific room."""
        if room not in self.rooms:
            return
        
        message_json = json.dumps(message)
        
        for user_id in self.rooms[room]:
            if user_id in self.active_connections:
                for websocket in self.active_connections[user_id]:
                    try:
                        await websocket.send_text(message_json)
                    except Exception as e:
                        logger.error(f"Error broadcasting to room {room}, user {user_id}: {e}")
    
    async def broadcast_notification(self, message: dict):
        """Broadcast a notification to all subscribed users."""
        message_json = json.dumps(message)
        
        for user_id in self.notification_subscribers:
            if user_id in self.active_connections:
                for websocket in self.active_connections[user_id]:
                    try:
                        await websocket.send_text(message_json)
                    except Exception as e:
                        logger.error(f"Error broadcasting notification to user {user_id}: {e}")
    
    async def broadcast_iot_data(self, device_id: int, message: dict):
        """Broadcast IoT sensor data to subscribed users."""
        if device_id not in self.iot_subscribers:
            return
        
        message_json = json.dumps(message)
        
        for user_id in self.iot_subscribers[device_id]:
            if user_id in self.active_connections:
                for websocket in self.active_connections[user_id]:
                    try:
                        await websocket.send_text(message_json)
                    except Exception as e:
                        logger.error(f"Error broadcasting IoT data to user {user_id}: {e}")
    
    def subscribe_to_notifications(self, user_id: int):
        """Subscribe a user to global notifications."""
        self.notification_subscribers.add(user_id)
        logger.info(f"User {user_id} subscribed to notifications")
    
    def unsubscribe_from_notifications(self, user_id: int):
        """Unsubscribe a user from global notifications."""
        self.notification_subscribers.discard(user_id)
        logger.info(f"User {user_id} unsubscribed from notifications")
    
    def join_room(self, user_id: int, room: str):
        """Add a user to a room."""
        if room not in self.rooms:
            self.rooms[room] = set()
        self.rooms[room].add(user_id)
        logger.info(f"User {user_id} joined room: {room}")
    
    def leave_room(self, user_id: int, room: str):
        """Remove a user from a room."""
        if room in self.rooms:
            self.rooms[room].discard(user_id)
            if not self.rooms[room]:
                del self.rooms[room]
        logger.info(f"User {user_id} left room: {room}")
    
    def subscribe_to_iot_device(self, user_id: int, device_id: int):
        """Subscribe a user to IoT device updates."""
        if device_id not in self.iot_subscribers:
            self.iot_subscribers[device_id] = set()
        self.iot_subscribers[device_id].add(user_id)
        logger.info(f"User {user_id} subscribed to IoT device: {device_id}")
    
    def unsubscribe_from_iot_device(self, user_id: int, device_id: int):
        """Unsubscribe a user from IoT device updates."""
        if device_id in self.iot_subscribers:
            self.iot_subscribers[device_id].discard(user_id)
            if not self.iot_subscribers[device_id]:
                del self.iot_subscribers[device_id]
        logger.info(f"User {user_id} unsubscribed from IoT device: {device_id}")
    
    def join_chat_room(self, user_id: int, chat_room_id: str):
        """Add a user to a chat room."""
        if chat_room_id not in self.chat_rooms:
            self.chat_rooms[chat_room_id] = set()
        self.chat_rooms[chat_room_id].add(user_id)
        logger.info(f"User {user_id} joined chat room: {chat_room_id}")
    
    def leave_chat_room(self, user_id: int, chat_room_id: str):
        """Remove a user from a chat room."""
        if chat_room_id in self.chat_rooms:
            self.chat_rooms[chat_room_id].discard(user_id)
            if not self.chat_rooms[chat_room_id]:
                del self.chat_rooms[chat_room_id]
        logger.info(f"User {user_id} left chat room: {chat_room_id}")
    
    async def broadcast_to_chat_room(self, chat_room_id: str, message: dict):
        """Broadcast a message to all users in a chat room."""
        if chat_room_id not in self.chat_rooms:
            return
        
        message_json = json.dumps(message)
        
        for user_id in self.chat_rooms[chat_room_id]:
            if user_id in self.active_connections:
                for websocket in self.active_connections[user_id]:
                    try:
                        await websocket.send_text(message_json)
                    except Exception as e:
                        logger.error(f"Error broadcasting to chat room {chat_room_id}, user {user_id}: {e}")
    
    def get_connection_count(self, user_id: int) -> int:
        """Get the number of active connections for a user."""
        return len(self.active_connections.get(user_id, []))
    
    def get_room_users(self, room: str) -> Set[int]:
        """Get all user IDs in a room."""
        return self.rooms.get(room, set()).copy()
    
    def get_active_user_count(self) -> int:
        """Get the total number of users with active connections."""
        return len(self.active_connections)
    
    async def send_heartbeat(self, websocket: WebSocket):
        """Send a heartbeat ping to keep the connection alive."""
        try:
            await websocket.send_json({"type": "ping", "timestamp": datetime.utcnow().isoformat()})
            if websocket in self.connection_metadata:
                self.connection_metadata[websocket]["last_ping"] = datetime.utcnow()
        except Exception as e:
            logger.error(f"Error sending heartbeat: {e}")


# Global connection manager instance
manager = ConnectionManager()


# ============================================================================
# WebSocket Authentication
# ============================================================================

async def get_websocket_user(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db)
) -> Optional[dict]:
    """
    Authenticate WebSocket connection using JWT token.
    
    Token can be provided as:
    1. Query parameter: ws://localhost:8000/ws/notifications?token=<jwt>
    2. In first message after connection: {"type": "auth", "token": "<jwt>"}
    """
    if not token:
        return None
    
    try:
        # Decode JWT token
        payload = jwt_decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        
        if not user_id:
            return None
        
        # Get user from database
        user_repo = UserRepository(db)
        user = user_repo.get_by_id(int(user_id))
        
        if not user or not user.is_active:
            return None
        
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role
        }
    
    except InvalidTokenError:
        logger.warning(f"Invalid JWT token in WebSocket authentication")
        return None
    except Exception as e:
        logger.error(f"Error authenticating WebSocket: {e}")
        return None


# ============================================================================
# WebSocket Endpoints
# ============================================================================

@router.websocket("/notifications")
async def websocket_notifications(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    WebSocket endpoint for real-time notifications.
    
    Connection: ws://localhost:8000/ws/notifications?token=<jwt_token>
    
    Messages sent by server:
    - {"type": "notification", "data": {...}} - New notification
    - {"type": "ping", "timestamp": "..."} - Heartbeat
    - {"type": "connected", "user_id": 123} - Connection confirmation
    - {"type": "error", "message": "..."} - Error message
    
    Messages accepted from client:
    - {"type": "auth", "token": "<jwt>"} - Authenticate connection
    - {"type": "pong"} - Heartbeat response
    - {"type": "subscribe"} - Subscribe to notifications
    - {"type": "unsubscribe"} - Unsubscribe from notifications
    """
    user = await get_websocket_user(websocket, token, db)
    
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication required")
        return
    
    user_id = user["id"]
    
    try:
        # Connect and send confirmation
        await manager.connect(websocket, user_id)
        await websocket.send_json({
            "type": "connected",
            "user_id": user_id,
            "message": "Connected to notifications channel"
        })
        
        # Auto-subscribe to notifications
        manager.subscribe_to_notifications(user_id)
        
        # Start heartbeat task
        async def heartbeat_loop():
            while True:
                await asyncio.sleep(30)  # Heartbeat every 30 seconds
                await manager.send_heartbeat(websocket)
        
        heartbeat_task = asyncio.create_task(heartbeat_loop())
        
        # Listen for messages
        try:
            while True:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                message_type = message.get("type")
                
                if message_type == "pong":
                    # Client responding to ping
                    continue
                
                elif message_type == "subscribe":
                    manager.subscribe_to_notifications(user_id)
                    await websocket.send_json({"type": "subscribed", "channel": "notifications"})
                
                elif message_type == "unsubscribe":
                    manager.unsubscribe_from_notifications(user_id)
                    await websocket.send_json({"type": "unsubscribed", "channel": "notifications"})
                
                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Unknown message type: {message_type}"
                    })
        
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected: user_id={user_id}")
        finally:
            heartbeat_task.cancel()
            manager.disconnect(websocket)
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


@router.websocket("/iot/{device_id}")
async def websocket_iot_device(
    websocket: WebSocket,
    device_id: int,
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    WebSocket endpoint for real-time IoT sensor data streaming.
    
    Connection: ws://localhost:8000/ws/iot/{device_id}?token=<jwt_token>
    
    Messages sent by server:
    - {"type": "sensor_data", "data": {...}} - New sensor reading
    - {"type": "device_status", "status": "online|offline"} - Device status
    - {"type": "alert", "data": {...}} - Threshold alert
    - {"type": "ping", "timestamp": "..."} - Heartbeat
    - {"type": "connected", "device_id": 123} - Connection confirmation
    
    Messages accepted from client:
    - {"type": "auth", "token": "<jwt>"} - Authenticate connection
    - {"type": "pong"} - Heartbeat response
    - {"type": "subscribe"} - Subscribe to device updates
    - {"type": "unsubscribe"} - Unsubscribe from device updates
    """
    user = await get_websocket_user(websocket, token, db)
    
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication required")
        return
    
    user_id = user["id"]
    
    try:
        # Connect and send confirmation
        await manager.connect(websocket, user_id)
        await websocket.send_json({
            "type": "connected",
            "device_id": device_id,
            "message": f"Connected to IoT device {device_id} stream"
        })
        
        # Subscribe to IoT device updates
        manager.subscribe_to_iot_device(user_id, device_id)
        
        # Start heartbeat task
        async def heartbeat_loop():
            while True:
                await asyncio.sleep(30)
                await manager.send_heartbeat(websocket)
        
        heartbeat_task = asyncio.create_task(heartbeat_loop())
        
        # Listen for messages
        try:
            while True:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                message_type = message.get("type")
                
                if message_type == "pong":
                    continue
                
                elif message_type == "subscribe":
                    manager.subscribe_to_iot_device(user_id, device_id)
                    await websocket.send_json({"type": "subscribed", "device_id": device_id})
                
                elif message_type == "unsubscribe":
                    manager.unsubscribe_from_iot_device(user_id, device_id)
                    await websocket.send_json({"type": "unsubscribed", "device_id": device_id})
                
                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Unknown message type: {message_type}"
                    })
        
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected: user_id={user_id}, device_id={device_id}")
        finally:
            heartbeat_task.cancel()
            manager.unsubscribe_from_iot_device(user_id, device_id)
            manager.disconnect(websocket)
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


@router.websocket("/chat/{room_id}")
async def websocket_chat(
    websocket: WebSocket,
    room_id: str,
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    WebSocket endpoint for real-time chat communication.
    
    Connection: ws://localhost:8000/ws/chat/{room_id}?token=<jwt_token>
    
    Room ID formats:
    - "expert_consultation_{id}" - Expert consultation room
    - "chama_{id}" - Chama group chat
    - "support" - General support chat
    
    Messages sent by server:
    - {"type": "message", "data": {...}} - New chat message
    - {"type": "user_joined", "user": {...}} - User joined room
    - {"type": "user_left", "user": {...}} - User left room
    - {"type": "typing", "user_id": 123} - User is typing
    - {"type": "ping", "timestamp": "..."} - Heartbeat
    - {"type": "connected", "room_id": "..."} - Connection confirmation
    
    Messages accepted from client:
    - {"type": "message", "content": "..."} - Send message
    - {"type": "typing", "is_typing": true/false} - Typing indicator
    - {"type": "pong"} - Heartbeat response
    """
    user = await get_websocket_user(websocket, token, db)
    
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication required")
        return
    
    user_id = user["id"]
    username = user["username"]
    
    try:
        # Connect and send confirmation
        await manager.connect(websocket, user_id)
        
        # Join chat room
        manager.join_chat_room(user_id, room_id)
        
        # Notify room about new user
        await manager.broadcast_to_chat_room(room_id, {
            "type": "user_joined",
            "user": {
                "id": user_id,
                "username": username
            },
            "timestamp": datetime.utcnow().isoformat()
        })
        
        await websocket.send_json({
            "type": "connected",
            "room_id": room_id,
            "message": f"Connected to chat room: {room_id}",
            "users_count": len(manager.chat_rooms.get(room_id, set()))
        })
        
        # Start heartbeat task
        async def heartbeat_loop():
            while True:
                await asyncio.sleep(30)
                await manager.send_heartbeat(websocket)
        
        heartbeat_task = asyncio.create_task(heartbeat_loop())
        
        # Listen for messages
        try:
            while True:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                message_type = message.get("type")
                
                if message_type == "pong":
                    continue
                
                elif message_type == "message":
                    # Broadcast message to all users in room
                    content = message.get("content", "")
                    await manager.broadcast_to_chat_room(room_id, {
                        "type": "message",
                        "data": {
                            "user_id": user_id,
                            "username": username,
                            "content": content,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    })
                
                elif message_type == "typing":
                    # Broadcast typing indicator
                    is_typing = message.get("is_typing", False)
                    await manager.broadcast_to_chat_room(room_id, {
                        "type": "typing",
                        "user_id": user_id,
                        "username": username,
                        "is_typing": is_typing
                    })
                
                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Unknown message type: {message_type}"
                    })
        
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected: user_id={user_id}, room_id={room_id}")
        finally:
            heartbeat_task.cancel()
            
            # Notify room about user leaving
            await manager.broadcast_to_chat_room(room_id, {
                "type": "user_left",
                "user": {
                    "id": user_id,
                    "username": username
                },
                "timestamp": datetime.utcnow().isoformat()
            })
            
            manager.leave_chat_room(user_id, room_id)
            manager.disconnect(websocket)
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


@router.websocket("/farm/{farm_id}")
async def websocket_farm_monitoring(
    websocket: WebSocket,
    farm_id: int,
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    WebSocket endpoint for real-time farm monitoring updates.
    
    Connection: ws://localhost:8000/ws/farm/{farm_id}?token=<jwt_token>
    
    Messages sent by server:
    - {"type": "farm_update", "data": {...}} - Farm data update
    - {"type": "crop_update", "data": {...}} - Crop status update
    - {"type": "weather_alert", "data": {...}} - Weather alert
    - {"type": "irrigation_status", "data": {...}} - Irrigation update
    - {"type": "pest_alert", "data": {...}} - Pest detection alert
    - {"type": "ping", "timestamp": "..."} - Heartbeat
    
    Messages accepted from client:
    - {"type": "pong"} - Heartbeat response
    - {"type": "request_status"} - Request current farm status
    """
    user = await get_websocket_user(websocket, token, db)
    
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication required")
        return
    
    user_id = user["id"]
    
    try:
        # Verify farm access
        farm_repo = FarmRepository(db)
        farm = farm_repo.get_by_id(farm_id)
        
        if not farm:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Farm not found")
            return
        
        if farm.owner_id != user_id:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Access denied")
            return
        
        # Connect and subscribe to farm updates
        await manager.connect(websocket, user_id)
        room_name = f"farm_{farm_id}"
        manager.join_room(user_id, room_name)
        
        await websocket.send_json({
            "type": "connected",
            "farm_id": farm_id,
            "message": f"Connected to farm {farm_id} monitoring"
        })
        
        # Start heartbeat task
        async def heartbeat_loop():
            while True:
                await asyncio.sleep(30)
                await manager.send_heartbeat(websocket)
        
        heartbeat_task = asyncio.create_task(heartbeat_loop())
        
        # Listen for messages
        try:
            while True:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                message_type = message.get("type")
                
                if message_type == "pong":
                    continue
                
                elif message_type == "request_status":
                    # Send current farm status
                    await websocket.send_json({
                        "type": "farm_status",
                        "data": {
                            "farm_id": farm.id,
                            "name": farm.name,
                            "size": farm.size,
                            "location": {
                                "latitude": farm.latitude,
                                "longitude": farm.longitude
                            },
                            "verified": farm.verified,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    })
                
                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Unknown message type: {message_type}"
                    })
        
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected: user_id={user_id}, farm_id={farm_id}")
        finally:
            heartbeat_task.cancel()
            manager.leave_room(user_id, room_name)
            manager.disconnect(websocket)
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


# ============================================================================
# Helper Functions for Broadcasting (to be called from other modules)
# ============================================================================

async def broadcast_notification_to_user(user_id: int, notification_data: dict):
    """
    Broadcast a notification to a specific user.
    To be called from notifications API when a new notification is created.
    """
    message = {
        "type": "notification",
        "data": notification_data,
        "timestamp": datetime.utcnow().isoformat()
    }
    await manager.send_personal_message(message, user_id)


async def broadcast_notification_to_all(notification_data: dict):
    """
    Broadcast a notification to all subscribed users.
    To be called for system-wide notifications.
    """
    message = {
        "type": "notification",
        "data": notification_data,
        "timestamp": datetime.utcnow().isoformat()
    }
    await manager.broadcast_notification(message)


async def broadcast_iot_sensor_data(device_id: int, sensor_data: dict):
    """
    Broadcast IoT sensor data to subscribed users.
    To be called from IoT API when new sensor data is recorded.
    """
    message = {
        "type": "sensor_data",
        "data": sensor_data,
        "timestamp": datetime.utcnow().isoformat()
    }
    await manager.broadcast_iot_data(device_id, message)


async def broadcast_farm_update(farm_id: int, update_data: dict):
    """
    Broadcast farm update to monitoring users.
    To be called when farm data changes.
    """
    message = {
        "type": "farm_update",
        "data": update_data,
        "timestamp": datetime.utcnow().isoformat()
    }
    room_name = f"farm_{farm_id}"
    await manager.broadcast_to_room(message, room_name)


async def broadcast_chat_message(room_id: str, message_data: dict):
    """
    Broadcast a chat message to a room.
    To be called from chat/messaging features.
    """
    message = {
        "type": "message",
        "data": message_data,
        "timestamp": datetime.utcnow().isoformat()
    }
    await manager.broadcast_to_chat_room(room_id, message)


# ============================================================================
# Connection Statistics (for monitoring)
# ============================================================================

def get_connection_stats() -> dict:
    """
    Get WebSocket connection statistics.
    Useful for monitoring and debugging.
    """
    return {
        "active_users": manager.get_active_user_count(),
        "total_connections": sum(len(conns) for conns in manager.active_connections.values()),
        "notification_subscribers": len(manager.notification_subscribers),
        "active_rooms": len(manager.rooms),
        "active_chat_rooms": len(manager.chat_rooms),
        "iot_subscriptions": len(manager.iot_subscribers),
        "timestamp": datetime.utcnow().isoformat()
    }
