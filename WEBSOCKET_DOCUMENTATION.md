# 🌐 WebSocket API Documentation

**Module**: `app/api/websockets.py`  
**Lines**: 852  
**Endpoints**: 4 WebSocket connections  
**Helper Functions**: 5 broadcasting utilities

---

## 📡 Overview

The WebSocket API provides real-time, bidirectional communication between the server and clients. It enables instant updates for notifications, IoT sensor data, chat messages, and farm monitoring.

### Key Features
- ✅ Real-time notifications broadcasting
- ✅ Live IoT sensor data streaming
- ✅ Chat support for expert consultations
- ✅ Farm monitoring with live updates
- ✅ JWT-based authentication
- ✅ Room/channel management
- ✅ Connection health monitoring (heartbeat)
- ✅ Automatic reconnection support
- ✅ Multi-device connections per user

---

## 🔌 WebSocket Endpoints

### 1. Notifications WebSocket

**Endpoint**: `ws://localhost:8000/ws/notifications?token=<jwt_token>`

**Purpose**: Real-time notification delivery to users

**Connection**:
```javascript
const token = localStorage.getItem('access_token');
const ws = new WebSocket(`ws://localhost:8000/ws/notifications?token=${token}`);

ws.onopen = () => {
    console.log('Connected to notifications');
};

ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    console.log('Received:', message);
    
    switch(message.type) {
        case 'connected':
            console.log('Connected:', message.user_id);
            break;
        case 'notification':
            displayNotification(message.data);
            break;
        case 'ping':
            ws.send(JSON.stringify({type: 'pong'}));
            break;
    }
};
```

**Messages from Server**:
```json
// Connection confirmation
{
    "type": "connected",
    "user_id": 123,
    "message": "Connected to notifications channel"
}

// New notification
{
    "type": "notification",
    "data": {
        "id": 456,
        "title": "New Message",
        "message": "You have a new message",
        "priority": "high",
        "created_at": "2025-11-01T10:30:00"
    },
    "timestamp": "2025-11-01T10:30:00"
}

// Heartbeat ping
{
    "type": "ping",
    "timestamp": "2025-11-01T10:30:30"
}
```

**Messages to Server**:
```json
// Heartbeat response
{
    "type": "pong"
}

// Subscribe to notifications
{
    "type": "subscribe"
}

// Unsubscribe from notifications
{
    "type": "unsubscribe"
}
```

---

### 2. IoT Device WebSocket

**Endpoint**: `ws://localhost:8000/ws/iot/{device_id}?token=<jwt_token>`

**Purpose**: Real-time IoT sensor data streaming

**Connection**:
```javascript
const token = localStorage.getItem('access_token');
const deviceId = 42;
const ws = new WebSocket(`ws://localhost:8000/ws/iot/${deviceId}?token=${token}`);

ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    
    switch(message.type) {
        case 'sensor_data':
            updateSensorChart(message.data);
            break;
        case 'device_status':
            updateDeviceStatus(message.status);
            break;
        case 'alert':
            showAlert(message.data);
            break;
    }
};
```

**Messages from Server**:
```json
// Connection confirmation
{
    "type": "connected",
    "device_id": 42,
    "message": "Connected to IoT device 42 stream"
}

// New sensor data
{
    "type": "sensor_data",
    "data": {
        "device_id": 42,
        "sensor_type": "soil_moisture",
        "value": 45.2,
        "unit": "percentage",
        "timestamp": "2025-11-01T10:35:00"
    },
    "timestamp": "2025-11-01T10:35:00"
}

// Device status change
{
    "type": "device_status",
    "status": "online",
    "timestamp": "2025-11-01T10:35:00"
}

// Threshold alert
{
    "type": "alert",
    "data": {
        "device_id": 42,
        "alert_type": "low_moisture",
        "message": "Soil moisture below threshold (45.2% < 50%)",
        "severity": "warning"
    },
    "timestamp": "2025-11-01T10:35:00"
}
```

**Messages to Server**:
```json
// Subscribe to device updates
{
    "type": "subscribe"
}

// Unsubscribe from device updates
{
    "type": "unsubscribe"
}

// Heartbeat response
{
    "type": "pong"
}
```

---

### 3. Chat WebSocket

**Endpoint**: `ws://localhost:8000/ws/chat/{room_id}?token=<jwt_token>`

**Purpose**: Real-time chat communication

**Room ID Formats**:
- `expert_consultation_{id}` - Expert consultation room
- `chama_{id}` - Chama group chat
- `support` - General support chat

**Connection**:
```javascript
const token = localStorage.getItem('access_token');
const roomId = 'expert_consultation_7';
const ws = new WebSocket(`ws://localhost:8000/ws/chat/${roomId}?token=${token}`);

ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    
    switch(message.type) {
        case 'connected':
            console.log('Connected to chat:', message.room_id);
            updateUserCount(message.users_count);
            break;
        case 'message':
            displayMessage(message.data);
            break;
        case 'user_joined':
            showUserJoined(message.user);
            break;
        case 'user_left':
            showUserLeft(message.user);
            break;
        case 'typing':
            showTypingIndicator(message.username, message.is_typing);
            break;
    }
};

// Send message
function sendMessage(content) {
    ws.send(JSON.stringify({
        type: 'message',
        content: content
    }));
}

// Send typing indicator
function sendTyping(isTyping) {
    ws.send(JSON.stringify({
        type: 'typing',
        is_typing: isTyping
    }));
}
```

**Messages from Server**:
```json
// Connection confirmation
{
    "type": "connected",
    "room_id": "expert_consultation_7",
    "message": "Connected to chat room: expert_consultation_7",
    "users_count": 3
}

// New message
{
    "type": "message",
    "data": {
        "user_id": 123,
        "username": "farmer_john",
        "content": "How do I treat leaf rust?",
        "timestamp": "2025-11-01T10:40:00"
    }
}

// User joined
{
    "type": "user_joined",
    "user": {
        "id": 456,
        "username": "agronomist_sarah"
    },
    "timestamp": "2025-11-01T10:40:30"
}

// User left
{
    "type": "user_left",
    "user": {
        "id": 456,
        "username": "agronomist_sarah"
    },
    "timestamp": "2025-11-01T10:50:00"
}

// Typing indicator
{
    "type": "typing",
    "user_id": 456,
    "username": "agronomist_sarah",
    "is_typing": true
}
```

**Messages to Server**:
```json
// Send message
{
    "type": "message",
    "content": "Apply fungicide containing copper"
}

// Typing indicator
{
    "type": "typing",
    "is_typing": true
}

// Stop typing
{
    "type": "typing",
    "is_typing": false
}

// Heartbeat response
{
    "type": "pong"
}
```

---

### 4. Farm Monitoring WebSocket

**Endpoint**: `ws://localhost:8000/ws/farm/{farm_id}?token=<jwt_token>`

**Purpose**: Real-time farm monitoring and updates

**Connection**:
```javascript
const token = localStorage.getItem('access_token');
const farmId = 15;
const ws = new WebSocket(`ws://localhost:8000/ws/farm/${farmId}?token=${token}`);

ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    
    switch(message.type) {
        case 'farm_update':
            updateFarmData(message.data);
            break;
        case 'crop_update':
            updateCropStatus(message.data);
            break;
        case 'weather_alert':
            showWeatherAlert(message.data);
            break;
        case 'irrigation_status':
            updateIrrigationStatus(message.data);
            break;
        case 'pest_alert':
            showPestAlert(message.data);
            break;
    }
};

// Request current status
function requestStatus() {
    ws.send(JSON.stringify({
        type: 'request_status'
    }));
}
```

**Messages from Server**:
```json
// Connection confirmation
{
    "type": "connected",
    "farm_id": 15,
    "message": "Connected to farm 15 monitoring"
}

// Farm update
{
    "type": "farm_update",
    "data": {
        "farm_id": 15,
        "name": "Green Valley Farm",
        "size": 50.5,
        "location": {
            "latitude": -1.2921,
            "longitude": 36.8219
        }
    },
    "timestamp": "2025-11-01T10:45:00"
}

// Crop update
{
    "type": "crop_update",
    "data": {
        "field_id": 3,
        "crop_name": "Maize",
        "growth_stage": "Flowering",
        "health_status": "Good"
    },
    "timestamp": "2025-11-01T10:45:00"
}

// Weather alert
{
    "type": "weather_alert",
    "data": {
        "alert_type": "heavy_rain",
        "message": "Heavy rain expected in the next 2 hours",
        "severity": "warning"
    },
    "timestamp": "2025-11-01T10:45:00"
}

// Irrigation status
{
    "type": "irrigation_status",
    "data": {
        "zone_id": 1,
        "status": "active",
        "duration": 120,
        "water_used": 500
    },
    "timestamp": "2025-11-01T10:45:00"
}

// Farm status response
{
    "type": "farm_status",
    "data": {
        "farm_id": 15,
        "name": "Green Valley Farm",
        "size": 50.5,
        "location": {
            "latitude": -1.2921,
            "longitude": 36.8219
        },
        "verified": true,
        "timestamp": "2025-11-01T10:45:00"
    }
}
```

**Messages to Server**:
```json
// Request current status
{
    "type": "request_status"
}

// Heartbeat response
{
    "type": "pong"
}
```

---

## 🛠️ Helper Functions (For Other APIs)

These functions can be called from other API modules to broadcast messages via WebSocket:

### 1. Broadcast to User

```python
from app.api.websockets import broadcast_notification_to_user

# In notifications API
async def send_notification(user_id: int, notification_data: dict):
    # Save to database
    notification = create_notification(user_id, notification_data)
    
    # Broadcast via WebSocket
    await broadcast_notification_to_user(user_id, {
        "id": notification.id,
        "title": notification.title,
        "message": notification.message,
        "priority": notification.priority,
        "created_at": notification.created_at.isoformat()
    })
```

### 2. Broadcast to All Users

```python
from app.api.websockets import broadcast_notification_to_all

# Broadcast system-wide notification
await broadcast_notification_to_all({
    "title": "System Maintenance",
    "message": "Scheduled maintenance at 2 AM",
    "priority": "high"
})
```

### 3. Broadcast IoT Data

```python
from app.api.websockets import broadcast_iot_sensor_data

# In IoT API when new sensor data is recorded
await broadcast_iot_sensor_data(device_id, {
    "device_id": device_id,
    "sensor_type": "temperature",
    "value": 25.5,
    "unit": "celsius",
    "timestamp": datetime.utcnow().isoformat()
})
```

### 4. Broadcast Farm Update

```python
from app.api.websockets import broadcast_farm_update

# When farm data changes
await broadcast_farm_update(farm_id, {
    "farm_id": farm_id,
    "field": "size",
    "old_value": 50,
    "new_value": 55,
    "updated_by": user_id
})
```

### 5. Broadcast Chat Message

```python
from app.api.websockets import broadcast_chat_message

# Send chat message to room
await broadcast_chat_message(room_id, {
    "user_id": user_id,
    "username": username,
    "content": message_content,
    "timestamp": datetime.utcnow().isoformat()
})
```

---

## 📊 Connection Manager

The `ConnectionManager` class handles all WebSocket connections:

### Key Methods

```python
# Connect user
await manager.connect(websocket, user_id)

# Disconnect user
manager.disconnect(websocket)

# Send to specific user
await manager.send_personal_message(message, user_id)

# Broadcast to room
await manager.broadcast_to_room(message, room_name)

# Broadcast notification to all
await manager.broadcast_notification(message)

# Subscribe to notifications
manager.subscribe_to_notifications(user_id)

# Join room
manager.join_room(user_id, room_name)

# Subscribe to IoT device
manager.subscribe_to_iot_device(user_id, device_id)

# Join chat room
manager.join_chat_room(user_id, room_id)

# Get statistics
stats = get_connection_stats()
```

### Connection Statistics

```python
from app.api.websockets import get_connection_stats

stats = get_connection_stats()
# Returns:
{
    "active_users": 45,
    "total_connections": 52,
    "notification_subscribers": 40,
    "active_rooms": 5,
    "active_chat_rooms": 3,
    "iot_subscriptions": 12,
    "timestamp": "2025-11-01T10:50:00"
}
```

---

## 🔒 Authentication

All WebSocket connections require JWT authentication:

### Query Parameter Method
```javascript
const token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...';
const ws = new WebSocket(`ws://localhost:8000/ws/notifications?token=${token}`);
```

### First Message Method (Alternative)
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/notifications');

ws.onopen = () => {
    ws.send(JSON.stringify({
        type: 'auth',
        token: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'
    }));
};
```

**Note**: Query parameter method is recommended and implemented.

---

## ⚡ Heartbeat / Keep-Alive

The server sends heartbeat pings every 30 seconds to keep connections alive:

```javascript
ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    
    if (message.type === 'ping') {
        // Respond to heartbeat
        ws.send(JSON.stringify({type: 'pong'}));
    }
};
```

**Why Heartbeat?**
- Keeps connection alive through proxies/firewalls
- Detects dead connections
- Prevents timeout disconnections

---

## 🔄 Reconnection Handling

Implement automatic reconnection in your client:

```javascript
class WebSocketClient {
    constructor(url, token) {
        this.url = url;
        this.token = token;
        this.reconnectDelay = 1000;
        this.maxReconnectDelay = 30000;
        this.connect();
    }
    
    connect() {
        this.ws = new WebSocket(`${this.url}?token=${this.token}`);
        
        this.ws.onopen = () => {
            console.log('Connected');
            this.reconnectDelay = 1000; // Reset delay
        };
        
        this.ws.onmessage = (event) => {
            this.handleMessage(JSON.parse(event.data));
        };
        
        this.ws.onclose = () => {
            console.log('Disconnected. Reconnecting...');
            this.reconnect();
        };
        
        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
    }
    
    reconnect() {
        setTimeout(() => {
            this.connect();
            this.reconnectDelay = Math.min(
                this.reconnectDelay * 2,
                this.maxReconnectDelay
            );
        }, this.reconnectDelay);
    }
    
    handleMessage(message) {
        if (message.type === 'ping') {
            this.ws.send(JSON.stringify({type: 'pong'}));
        } else {
            // Handle other messages
            console.log('Received:', message);
        }
    }
}

// Usage
const notificationClient = new WebSocketClient(
    'ws://localhost:8000/ws/notifications',
    localStorage.getItem('access_token')
);
```

---

## 📱 React Example

```jsx
import { useEffect, useState, useRef } from 'react';

function NotificationsComponent() {
    const [notifications, setNotifications] = useState([]);
    const ws = useRef(null);
    
    useEffect(() => {
        const token = localStorage.getItem('access_token');
        ws.current = new WebSocket(
            `ws://localhost:8000/ws/notifications?token=${token}`
        );
        
        ws.current.onopen = () => {
            console.log('WebSocket connected');
        };
        
        ws.current.onmessage = (event) => {
            const message = JSON.parse(event.data);
            
            if (message.type === 'notification') {
                setNotifications(prev => [message.data, ...prev]);
            } else if (message.type === 'ping') {
                ws.current.send(JSON.stringify({type: 'pong'}));
            }
        };
        
        ws.current.onclose = () => {
            console.log('WebSocket disconnected');
        };
        
        return () => {
            ws.current.close();
        };
    }, []);
    
    return (
        <div>
            <h2>Real-time Notifications</h2>
            {notifications.map(notif => (
                <div key={notif.id}>
                    <h3>{notif.title}</h3>
                    <p>{notif.message}</p>
                </div>
            ))}
        </div>
    );
}
```

---

## 🧪 Testing WebSocket Endpoints

### Using JavaScript Console

```javascript
// Connect
const token = 'your_jwt_token';
const ws = new WebSocket(`ws://localhost:8000/ws/notifications?token=${token}`);

// Log all messages
ws.onmessage = (e) => console.log(JSON.parse(e.data));

// Send message
ws.send(JSON.stringify({type: 'subscribe'}));

// Close
ws.close();
```

### Using Python

```python
import asyncio
import websockets
import json

async def test_websocket():
    token = "your_jwt_token"
    uri = f"ws://localhost:8000/ws/notifications?token={token}"
    
    async with websockets.connect(uri) as websocket:
        # Receive messages
        while True:
            message = await websocket.recv()
            print(f"Received: {message}")
            
            data = json.loads(message)
            
            # Respond to ping
            if data['type'] == 'ping':
                await websocket.send(json.dumps({'type': 'pong'}))

asyncio.run(test_websocket())
```

---

## 📖 Best Practices

### 1. Always Handle Disconnections
```javascript
ws.onclose = () => {
    // Implement reconnection logic
    reconnect();
};
```

### 2. Respond to Heartbeats
```javascript
if (message.type === 'ping') {
    ws.send(JSON.stringify({type: 'pong'}));
}
```

### 3. Handle Errors Gracefully
```javascript
ws.onerror = (error) => {
    console.error('WebSocket error:', error);
    // Show user-friendly error message
};
```

### 4. Clean Up Connections
```javascript
// In React useEffect or component unmount
return () => {
    ws.close();
};
```

### 5. Use Connection Pooling
- Allow multiple connections per user
- Different connections for different features
- Example: One for notifications, one for IoT

---

## 🎯 Common Use Cases

### 1. Real-time Dashboard
```javascript
// Connect to multiple WebSocket endpoints
const notifWs = new WebSocket(`ws://localhost:8000/ws/notifications?token=${token}`);
const iotWs = new WebSocket(`ws://localhost:8000/ws/iot/42?token=${token}`);
const farmWs = new WebSocket(`ws://localhost:8000/ws/farm/15?token=${token}`);

// Update dashboard in real-time
notifWs.onmessage = updateNotificationBadge;
iotWs.onmessage = updateSensorCharts;
farmWs.onmessage = updateFarmStatus;
```

### 2. Live Chat Support
```javascript
const chatWs = new WebSocket(`ws://localhost:8000/ws/chat/support?token=${token}`);

// Send message
function sendMessage(content) {
    chatWs.send(JSON.stringify({
        type: 'message',
        content: content
    }));
}

// Show typing
function setTyping(isTyping) {
    chatWs.send(JSON.stringify({
        type: 'typing',
        is_typing: isTyping
    }));
}
```

### 3. IoT Monitoring
```javascript
// Connect to device
const deviceWs = new WebSocket(`ws://localhost:8000/ws/iot/42?token=${token}`);

// Real-time sensor chart
deviceWs.onmessage = (event) => {
    const message = JSON.parse(event.data);
    if (message.type === 'sensor_data') {
        updateChart(message.data);
        
        // Check thresholds
        if (message.data.value < threshold) {
            showAlert('Low moisture detected!');
        }
    }
};
```

---

## 📚 Additional Resources

- **FastAPI WebSocket Docs**: https://fastapi.tiangolo.com/advanced/websockets/
- **MDN WebSocket API**: https://developer.mozilla.org/en-US/docs/Web/API/WebSocket
- **WebSocket Protocol RFC**: https://tools.ietf.org/html/rfc6455

---

**WebSocket API is production-ready and fully functional!** 🎉
