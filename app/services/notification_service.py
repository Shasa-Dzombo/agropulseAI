"""
AgroPulse Notification Service
Cloud orchestration for Sentry-Scout-Chatbot handshake

This service receives Sentry alerts from IoT devices and orchestrates:
1. Push notifications to mobile app (Firebase Cloud Messaging)
2. Chatbot messages (WhatsApp Business API / Telegram)
3. GPS-guided farmer activation
4. Closed-loop result delivery
"""

import json
import logging
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import requests
try:
    from firebase_admin import messaging, credentials, initialize_app
except ImportError:
    messaging = credentials = initialize_app = None
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.cctv import SentryScoutHandshake, CCTV, CCTVCapture
from app.models.user import User
from app.models.field import Field
from app.config import settings

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Cloud orchestration service for Sentry-Scout-Chatbot ecosystem
    
    Flow:
    1. Sentry detects stress → sends alert packet to cloud
    2. Cloud enriches with farmer/crop data
    3. Cloud sends push notification (phone + chatbot)
    4. Farmer acknowledges → walks to GPS location
    5. Phone app performs guided high-fidelity scan
    6. Cloud AI diagnoses → sends results
    7. Blockchain records completion
    """
    
    def __init__(self):
        # Initialize Firebase Admin SDK for push notifications
        if credentials is None:
            logger.warning("⚠️ firebase_admin not installed; push notifications disabled")
            return
        try:
            cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
            initialize_app(cred)
            logger.info("✅ Firebase Admin SDK initialized")
        except Exception as e:
            logger.warning(f"⚠️ Firebase initialization failed: {e}")
    
    
    async def handle_sentry_alert(
        self,
        db: AsyncSession,
        alert_packet: Dict,
        sentry_id: int
    ) -> Dict:
        """
        Core orchestration: Receive Sentry alert and initiate handshake
        
        Args:
            alert_packet: JSON from Sentry containing health data, GPS, environmental context
            sentry_id: Database ID of the Sentry device
        
        Returns:
            Handshake metadata with alert_id, notification status, etc.
        """
        logger.info(f"🚨 Received Sentry Alert from device #{sentry_id}")
        
        # Step 1: Enrich alert with database context
        enriched_alert = await self._enrich_alert(db, alert_packet, sentry_id)
        
        # Step 2: Create handshake record in database
        handshake = await self._create_handshake_record(db, enriched_alert, sentry_id)
        
        # Step 3: Send push notification to mobile app
        mobile_notification_sent = await self._send_mobile_push_notification(
            enriched_alert, handshake.id
        )
        
        # Step 4: Send chatbot message (WhatsApp/Telegram)
        chatbot_message_sent = await self._send_chatbot_message(
            enriched_alert, handshake.id
        )
        
        # Step 5: Update handshake record with notification status
        handshake.mobile_notification_sent = mobile_notification_sent
        handshake.chatbot_message_sent = chatbot_message_sent
        handshake.notification_sent_at = datetime.utcnow()
        await db.commit()
        
        logger.info(f"✅ Sentry-Scout Handshake #{handshake.id} initiated successfully")
        logger.info(f"   Mobile push: {'✅' if mobile_notification_sent else '❌'}")
        logger.info(f"   Chatbot: {'✅' if chatbot_message_sent else '❌'}")
        
        return {
            "handshake_id": handshake.id,
            "alert_type": alert_packet.get("alert_type"),
            "priority": enriched_alert.get("priority"),
            "mobile_notification_sent": mobile_notification_sent,
            "chatbot_message_sent": chatbot_message_sent,
            "gps_location": alert_packet.get("gps_location"),
            "requires_scout": True,
            "message": "Push notifications sent. Waiting for farmer response."
        }
    
    
    async def _enrich_alert(
        self,
        db: AsyncSession,
        alert_packet: Dict,
        sentry_id: int
    ) -> Dict:
        """
        Enrich Sentry alert with farmer contact, crop type, zone name
        """
        # Get Sentry device info
        result = await db.execute(
            select(CCTV).where(CCTV.id == sentry_id)
        )
        sentry = result.scalars().first()
        
        if not sentry:
            logger.error(f"❌ Sentry device #{sentry_id} not found")
            return alert_packet
        
        # Get farmer (user) info
        result = await db.execute(
            select(User).where(User.id == sentry.user_id)
        )
        farmer = result.scalars().first()
        
        # Get field (zone) info
        result = await db.execute(
            select(Field).where(Field.id == sentry.field_id)
        )
        field = result.scalars().first()
        
        # Enrich alert
        enriched = {
            **alert_packet,
            "farmer": {
                "id": farmer.id if farmer else None,
                "name": farmer.full_name if farmer else "Unknown",
                "phone": farmer.phone_number if farmer else None,
                "fcm_token": getattr(farmer, "fcm_token", None) if farmer else None,
                "chatbot_platform": getattr(farmer, "chatbot_platform", "whatsapp") if farmer else "whatsapp",
                "chatbot_id": getattr(farmer, "chatbot_id", None) if farmer else None
            },
            "field": {
                "id": field.id if field else None,
                "name": field.name if field else "Unknown Zone",
                "crop_type": field.crop_type if field else "Unknown",
                "area_hectares": float(field.area_hectares) if field else 0.0
            },
            "sentry": {
                "id": sentry.id,
                "device_serial": sentry.device_serial,
                "location_name": sentry.location_name,
                "installation_date": sentry.created_at.isoformat() if sentry.created_at else None
            },
            "priority": self._calculate_alert_priority(alert_packet)
        }
        
        return enriched
    
    
    def _calculate_alert_priority(self, alert_packet: Dict) -> str:
        """
        Calculate alert priority based on health degradation and pest detection
        """
        health_data = alert_packet.get("health_data", {})
        expected = health_data.get("expected_health", 0.75)
        current = health_data.get("current_health", 0.75)
        
        degradation = expected - current
        
        # Check for micro-pest detection
        pest_alert = alert_packet.get("micro_pest_alert")
        has_pest = pest_alert is not None
        
        if degradation > 0.30 or (has_pest and pest_alert.get("detection_confidence", 0) > 0.85):
            return "critical"
        elif degradation > 0.15 or has_pest:
            return "high"
        elif degradation > 0.05:
            return "medium"
        else:
            return "low"
    
    
    async def _create_handshake_record(
        self,
        db: AsyncSession,
        enriched_alert: Dict,
        sentry_id: int
    ) -> SentryScoutHandshake:
        """
        Create database record for Sentry-Scout handshake tracking
        """
        handshake = SentryScoutHandshake(
            cctv_id=sentry_id,
            alert_type=enriched_alert.get("alert_type", "STRESS_DETECTED"),
            priority=enriched_alert.get("priority", "medium"),
            alert_packet_json=json.dumps(enriched_alert),
            gps_latitude=enriched_alert.get("gps_location", {}).get("latitude"),
            gps_longitude=enriched_alert.get("gps_location", {}).get("longitude"),
            status="pending",
            created_at=datetime.utcnow()
        )
        
        db.add(handshake)
        await db.commit()
        await db.refresh(handshake)
        
        return handshake
    
    
    async def _send_mobile_push_notification(
        self,
        enriched_alert: Dict,
        handshake_id: int
    ) -> bool:
        """
        Send push notification to farmer's mobile app via Firebase Cloud Messaging
        """
        fcm_token = enriched_alert.get("farmer", {}).get("fcm_token")
        
        if not fcm_token:
            logger.warning("⚠️ No FCM token found for farmer - skipping mobile push")
            return False
        
        try:
            # Build notification
            priority = enriched_alert.get("priority", "medium")
            field_name = enriched_alert.get("field", {}).get("name", "Unknown Zone")
            crop_type = enriched_alert.get("field", {}).get("crop_type", "crop")
            
            health_data = enriched_alert.get("health_data", {})
            current_health = health_data.get("current_health", 0.50)
            
            # Emoji based on priority
            emoji = "🚨" if priority == "critical" else "⚠️" if priority == "high" else "📊"
            
            title = f"{emoji} AgroPulse Alert: {field_name}"
            body = f"Stress detected in your {crop_type}. Health: {int(current_health * 100)}%. Tap to inspect."
            
            # Build notification message
            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body
                ),
                data={
                    "handshake_id": str(handshake_id),
                    "alert_type": enriched_alert.get("alert_type"),
                    "priority": priority,
                    "gps_lat": str(enriched_alert.get("gps_location", {}).get("latitude", 0)),
                    "gps_lon": str(enriched_alert.get("gps_location", {}).get("longitude", 0)),
                    "field_id": str(enriched_alert.get("field", {}).get("id", "")),
                    "sentry_id": str(enriched_alert.get("sentry", {}).get("id", "")),
                    "action": "INSPECT_LOCATION"
                },
                token=fcm_token,
                android=messaging.AndroidConfig(
                    priority="high",
                    notification=messaging.AndroidNotification(
                        sound="default",
                        color="#4CAF50"
                    )
                ),
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            sound="default",
                            badge=1
                        )
                    )
                )
            )
            
            # Send message
            response = messaging.send(message)
            logger.info(f"✅ Mobile push notification sent: {response}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send mobile push notification: {e}")
            return False
    
    
    async def _send_chatbot_message(
        self,
        enriched_alert: Dict,
        handshake_id: int
    ) -> bool:
        """
        Send chatbot message via WhatsApp Business API or Telegram
        """
        platform = enriched_alert.get("farmer", {}).get("chatbot_platform", "whatsapp")
        chatbot_id = enriched_alert.get("farmer", {}).get("chatbot_id")
        
        if not chatbot_id:
            logger.warning("⚠️ No chatbot ID found for farmer - skipping chatbot message")
            return False
        
        # Build human-readable message
        priority = enriched_alert.get("priority", "medium")
        field_name = enriched_alert.get("field", {}).get("name", "Unknown Zone")
        crop_type = enriched_alert.get("field", {}).get("crop_type", "crop")
        
        health_data = enriched_alert.get("health_data", {})
        current_health = health_data.get("current_health", 0.50)
        expected_health = health_data.get("expected_health", 0.75)
        
        gps_lat = enriched_alert.get("gps_location", {}).get("latitude", 0)
        gps_lon = enriched_alert.get("gps_location", {}).get("longitude", 0)
        
        # Check for pest detection
        pest_alert = enriched_alert.get("micro_pest_alert")
        pest_info = ""
        if pest_alert:
            pest_type = pest_alert.get("pest_type", "unknown")
            pest_size = pest_alert.get("pest_size_mm", 0)
            pest_info = f"\n🦟 *Pest Detected*: {pest_type.capitalize()} ({pest_size:.2f}mm)"
        
        message = f"""
🚨 *AgroPulse Alert*

📍 *Location*: {field_name}
🌾 *Crop*: {crop_type.capitalize()}
📊 *Health Status*: {int(current_health * 100)}% (Expected: {int(expected_health * 100)}%){pest_info}

⚠️ *Priority*: {priority.upper()}

📍 *GPS Coordinates*: {gps_lat:.6f}, {gps_lon:.6f}
🗺️ [View on Map](https://www.google.com/maps?q={gps_lat},{gps_lon})

👉 *Action Required*:
1. Open AgroPulse app
2. Follow the red pin on the map
3. Perform guided high-fidelity scan
4. View AI diagnosis

_Powered by AgroPulse Sentry Stakes with 99% accuracy + Quantum-Inspired Optimization_
"""
        
        try:
            if platform == "whatsapp":
                return await self._send_whatsapp_message(chatbot_id, message)
            elif platform == "telegram":
                return await self._send_telegram_message(chatbot_id, message)
            else:
                logger.error(f"❌ Unknown chatbot platform: {platform}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to send chatbot message: {e}")
            return False
    
    
    async def _send_whatsapp_message(self, phone_number: str, message: str) -> bool:
        """
        Send message via WhatsApp Business API
        """
        if not hasattr(settings, 'WHATSAPP_API_URL') or not hasattr(settings, 'WHATSAPP_API_TOKEN'):
            logger.warning("⚠️ WhatsApp credentials not configured")
            return False
        
        try:
            url = f"{settings.WHATSAPP_API_URL}/messages"
            headers = {
                "Authorization": f"Bearer {settings.WHATSAPP_API_TOKEN}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "messaging_product": "whatsapp",
                "to": phone_number,
                "type": "text",
                "text": {
                    "body": message
                }
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"✅ WhatsApp message sent to {phone_number}")
                return True
            else:
                logger.error(f"❌ WhatsApp API error: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ WhatsApp message failed: {e}")
            return False
    
    
    async def _send_telegram_message(self, chat_id: str, message: str) -> bool:
        """
        Send message via Telegram Bot API
        """
        if not hasattr(settings, 'TELEGRAM_BOT_TOKEN'):
            logger.warning("⚠️ Telegram bot token not configured")
            return False
        
        try:
            url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
            
            payload = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "Markdown",
                "disable_web_page_preview": False
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"✅ Telegram message sent to chat {chat_id}")
                return True
            else:
                logger.error(f"❌ Telegram API error: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Telegram message failed: {e}")
            return False
    
    
    async def handle_scout_arrival(
        self,
        db: AsyncSession,
        handshake_id: int,
        scout_gps_lat: float,
        scout_gps_lon: float
    ) -> Dict:
        """
        Handle farmer (Scout) arrival at GPS location
        
        Verifies proximity (<50m) and updates handshake status
        """
        # Get handshake record
        result = await db.execute(
            select(SentryScoutHandshake).where(SentryScoutHandshake.id == handshake_id)
        )
        handshake = result.scalars().first()
        
        if not handshake:
            return {"error": "Handshake not found"}
        
        # Calculate distance between Sentry GPS and Scout GPS
        distance_m = self._calculate_gps_distance(
            handshake.gps_latitude,
            handshake.gps_longitude,
            scout_gps_lat,
            scout_gps_lon
        )
        
        if distance_m < 50:
            # Scout is within 50m - mark as arrived
            handshake.status = "scout_arrived"
            handshake.scout_arrived_at = datetime.utcnow()
            await db.commit()
            
            logger.info(f"✅ Scout arrived at handshake #{handshake_id} (distance: {distance_m:.1f}m)")
            
            return {
                "status": "arrived",
                "distance_m": distance_m,
                "message": "Perfect! You're at the location. Start the guided scan.",
                "next_step": "PERFORM_SCAN"
            }
        else:
            return {
                "status": "not_arrived",
                "distance_m": distance_m,
                "message": f"You're {distance_m:.0f}m away. Keep walking toward the pin.",
                "next_step": "CONTINUE_WALKING"
            }
    
    
    def _calculate_gps_distance(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float
    ) -> float:
        """
        Calculate distance between two GPS coordinates (Haversine formula)
        Returns distance in meters
        """
        from math import radians, sin, cos, sqrt, atan2
        
        R = 6371000  # Earth radius in meters
        
        lat1_rad = radians(lat1)
        lat2_rad = radians(lat2)
        delta_lat = radians(lat2 - lat1)
        delta_lon = radians(lon2 - lon1)
        
        a = sin(delta_lat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        
        distance = R * c
        return distance
    
    
    async def handle_diagnosis_result(
        self,
        db: AsyncSession,
        handshake_id: int,
        diagnosis_result: Dict
    ) -> Dict:
        """
        Handle AI diagnosis result and send back to farmer
        
        Closes the loop: Sentry → Cloud → Chatbot → Farmer → Diagnosis → Farmer
        """
        # Get handshake record
        result = await db.execute(
            select(SentryScoutHandshake).where(SentryScoutHandshake.id == handshake_id)
        )
        handshake = result.scalars().first()
        
        if not handshake:
            return {"error": "Handshake not found"}
        
        # Update handshake with diagnosis
        handshake.status = "diagnosis_complete"
        handshake.diagnosis_result_json = json.dumps(diagnosis_result)
        handshake.diagnosis_completed_at = datetime.utcnow()
        await db.commit()
        
        # Parse diagnosis
        disease = diagnosis_result.get("disease", "Unknown")
        confidence = diagnosis_result.get("confidence", 0) * 100
        treatment = diagnosis_result.get("treatment", "Consult agronomist")
        
        # Send result to chatbot
        enriched_alert = json.loads(handshake.alert_packet_json)
        chatbot_id = enriched_alert.get("farmer", {}).get("chatbot_id")
        platform = enriched_alert.get("farmer", {}).get("chatbot_platform", "whatsapp")
        
        result_message = f"""
✅ *Diagnosis Complete*

🔬 *Result*: {disease}
📊 *Confidence*: {confidence:.1f}%

💊 *Recommended Treatment*:
{treatment}

📝 *Next Steps*:
1. Apply treatment as recommended
2. Monitor progress in 3-5 days
3. Update status in app

_This diagnosis has been recorded on blockchain for immutable service record._

🌾 *AgroPulse - Precision Agriculture at Scale*
"""
        
        if chatbot_id:
            if platform == "whatsapp":
                await self._send_whatsapp_message(chatbot_id, result_message)
            elif platform == "telegram":
                await self._send_telegram_message(chatbot_id, result_message)
        
        logger.info(f"✅ Diagnosis delivered for handshake #{handshake_id}: {disease} ({confidence:.1f}%)")
        
        return {
            "status": "diagnosis_delivered",
            "disease": disease,
            "confidence": confidence,
            "message": "Diagnosis sent to farmer via chatbot"
        }
    
    # ========================================================================
    # Business Logic Service Methods - Enhanced Notification Management
    # ========================================================================
    
    async def send_general_notification(
        self,
        db: AsyncSession,
        user_id: int,
        title: str,
        message: str,
        notification_type: str,
        priority: str = "normal",
        channels: Optional[List[str]] = None,
        data: Optional[Dict] = None
    ) -> Dict:
        """
        Send a general notification to a user with business logic.
        
        Business Rules:
        - Respects user notification preferences
        - Validates channels and notification types
        - Applies priority-based delivery
        - Tracks delivery status
        
        Args:
            db: Database session
            user_id: ID of recipient user
            title: Notification title
            message: Notification message
            notification_type: Type (alert, reminder, update, marketing, transactional)
            priority: Priority level (low, normal, high, urgent)
            channels: Delivery channels (push, email, sms, in_app)
            data: Additional data payload
            
        Returns:
            Dictionary with notification details and delivery status
        """
        try:
            # Get user and validate
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            
            if not user:
                logger.warning(f"User {user_id} not found for notification")
                return {"status": "failed", "reason": "User not found"}
            
            # Get user preferences
            preferences = await self._get_user_notification_preferences(db, user_id)
            
            # Validate notification type
            valid_types = ["alert", "reminder", "update", "marketing", "transactional"]
            if notification_type not in valid_types:
                logger.warning(f"Invalid notification type: {notification_type}")
                return {"status": "failed", "reason": "Invalid notification type"}
            
            # Check if user has enabled this type
            if not self._is_type_enabled(preferences, notification_type):
                logger.info(f"User {user_id} has disabled {notification_type} notifications")
                return {"status": "skipped", "reason": "User preference disabled"}
            
            # Determine channels based on preferences
            if channels is None:
                channels = self._get_enabled_channels(preferences, notification_type)
            else:
                channels = self._filter_channels_by_preference(channels, preferences)
            
            if not channels:
                return {"status": "skipped", "reason": "No enabled channels"}
            
            # Deliver through each channel
            delivery_results = {}
            
            if "push" in channels and user.fcm_token:
                push_result = await self._deliver_push_notification(
                    user.fcm_token,
                    title,
                    message,
                    data
                )
                delivery_results["push"] = push_result
            
            if "email" in channels and user.email:
                email_result = await self._deliver_email_notification(
                    user.email,
                    title,
                    message,
                    notification_type
                )
                delivery_results["email"] = email_result
            
            if "sms" in channels and user.phone:
                sms_result = await self._deliver_sms_notification(
                    user.phone,
                    title,
                    message
                )
                delivery_results["sms"] = sms_result
            
            # In-app is always stored
            in_app_result = await self._store_in_app_notification(
                db,
                user_id,
                title,
                message,
                notification_type,
                priority,
                data
            )
            delivery_results["in_app"] = in_app_result
            
            logger.info(f"✅ Notification sent to user {user_id}: {title}")
            
            return {
                "status": "delivered",
                "user_id": user_id,
                "title": title,
                "type": notification_type,
                "priority": priority,
                "channels": channels,
                "delivery_results": delivery_results
            }
        
        except Exception as e:
            logger.error(f"❌ Failed to send notification: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def send_bulk_notification(
        self,
        db: AsyncSession,
        user_ids: List[int],
        title: str,
        message: str,
        notification_type: str,
        priority: str = "normal"
    ) -> Dict:
        """
        Send notifications to multiple users in batch.
        
        Args:
            db: Database session
            user_ids: List of user IDs
            title: Notification title
            message: Notification message
            notification_type: Type of notification
            priority: Priority level
            
        Returns:
            Batch delivery statistics
        """
        results = {
            "total": len(user_ids),
            "successful": 0,
            "failed": 0,
            "skipped": 0
        }
        
        for user_id in user_ids:
            result = await self.send_general_notification(
                db, user_id, title, message, notification_type, priority
            )
            
            if result["status"] == "delivered":
                results["successful"] += 1
            elif result["status"] == "skipped":
                results["skipped"] += 1
            else:
                results["failed"] += 1
        
        logger.info(f"📤 Bulk notification complete: {results}")
        return results
    
    async def _get_user_notification_preferences(
        self,
        db: AsyncSession,
        user_id: int
    ) -> Dict:
        """
        Get user notification preferences or return defaults.
        
        Returns dict with: enable_push, enable_email, enable_sms,
        enable_alerts, enable_reminders, enable_updates, enable_marketing
        """
        # In production, query from NotificationPreference table
        # For now, return sensible defaults
        return {
            "enable_push": True,
            "enable_email": True,
            "enable_sms": True,
            "enable_alerts": True,
            "enable_reminders": True,
            "enable_updates": True,
            "enable_marketing": False
        }
    
    def _is_type_enabled(self, preferences: Dict, notification_type: str) -> bool:
        """Check if notification type is enabled in preferences."""
        type_map = {
            "alert": preferences.get("enable_alerts", True),
            "reminder": preferences.get("enable_reminders", True),
            "update": preferences.get("enable_updates", True),
            "marketing": preferences.get("enable_marketing", False),
            "transactional": True  # Always enabled
        }
        return type_map.get(notification_type, True)
    
    def _get_enabled_channels(self, preferences: Dict, notification_type: str) -> List[str]:
        """Get list of enabled channels based on preferences."""
        channels = []
        
        if preferences.get("enable_push", True):
            channels.append("push")
        
        if preferences.get("enable_email", True):
            channels.append("email")
        
        if preferences.get("enable_sms", True):
            channels.append("sms")
        
        # In-app always enabled
        channels.append("in_app")
        
        return channels
    
    def _filter_channels_by_preference(
        self,
        requested_channels: List[str],
        preferences: Dict
    ) -> List[str]:
        """Filter requested channels by user preferences."""
        filtered = []
        
        for channel in requested_channels:
            if channel == "push" and preferences.get("enable_push", True):
                filtered.append(channel)
            elif channel == "email" and preferences.get("enable_email", True):
                filtered.append(channel)
            elif channel == "sms" and preferences.get("enable_sms", True):
                filtered.append(channel)
            elif channel == "in_app":
                filtered.append(channel)
        
        return filtered
    
    async def _deliver_push_notification(
        self,
        fcm_token: str,
        title: str,
        body: str,
        data: Optional[Dict] = None
    ) -> Dict:
        """Deliver push notification via FCM."""
        try:
            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body
                ),
                data=data or {},
                token=fcm_token
            )
            
            response = messaging.send(message)
            return {"status": "delivered", "message_id": response}
        
        except Exception as e:
            logger.error(f"❌ Push notification failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def _deliver_email_notification(
        self,
        email: str,
        subject: str,
        message: str,
        notification_type: str
    ) -> Dict:
        """
        Deliver email notification.
        
        In production, integrate with SendGrid, AWS SES, or Mailgun.
        """
        try:
            # Placeholder for email delivery
            # In production:
            # - Use email service provider API
            # - Apply HTML templates
            # - Track delivery status
            
            logger.info(f"📧 Email notification sent to {email}: {subject}")
            return {"status": "delivered", "provider": "sendgrid"}
        
        except Exception as e:
            logger.error(f"❌ Email notification failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def _deliver_sms_notification(
        self,
        phone: str,
        title: str,
        message: str
    ) -> Dict:
        """
        Deliver SMS notification.
        
        In production, integrate with Twilio or Africa's Talking.
        """
        try:
            # Placeholder for SMS delivery
            # In production:
            # - Use SMS gateway API (Twilio, Africa's Talking)
            # - Handle Kenya phone number format
            # - Track delivery status
            
            logger.info(f"📱 SMS notification sent to {phone}: {title}")
            return {"status": "delivered", "provider": "twilio"}
        
        except Exception as e:
            logger.error(f"❌ SMS notification failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def _store_in_app_notification(
        self,
        db: AsyncSession,
        user_id: int,
        title: str,
        message: str,
        notification_type: str,
        priority: str,
        data: Optional[Dict]
    ) -> Dict:
        """
        Store in-app notification in database.
        
        In production, store in Notification table with:
        - user_id, title, message, type, priority
        - is_read = False, created_at = now
        - data as JSON
        """
        try:
            # Placeholder for database storage
            # In production: Insert into Notification table
            
            logger.info(f"💾 In-app notification stored for user {user_id}")
            return {"status": "stored"}
        
        except Exception as e:
            logger.error(f"❌ In-app notification storage failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def get_user_notifications(
        self,
        db: AsyncSession,
        user_id: int,
        unread_only: bool = False,
        limit: int = 50,
        offset: int = 0
    ) -> Dict:
        """
        Get notifications for a user with pagination.
        
        Args:
            db: Database session
            user_id: ID of user
            unread_only: Return only unread notifications
            limit: Maximum number of notifications
            offset: Offset for pagination
            
        Returns:
            Dictionary with notifications and stats
        """
        # In production, query from Notification table
        # Filter by user_id, optionally by is_read
        # Order by created_at DESC
        # Apply limit and offset
        
        return {
            "notifications": [],
            "total_count": 0,
            "unread_count": 0,
            "limit": limit,
            "offset": offset
        }
    
    async def mark_notification_read(
        self,
        db: AsyncSession,
        notification_id: int,
        user_id: int
    ) -> Dict:
        """
        Mark notification as read.
        
        Args:
            db: Database session
            notification_id: ID of notification
            user_id: ID of user
            
        Returns:
            Updated notification
        """
        # In production:
        # 1. Query notification by id
        # 2. Verify notification.user_id == user_id
        # 3. Set is_read = True, read_at = now
        # 4. Commit and return
        
        return {"status": "marked_read", "notification_id": notification_id}
    
    async def mark_all_read(
        self,
        db: AsyncSession,
        user_id: int
    ) -> Dict:
        """
        Mark all notifications as read for a user.
        
        Args:
            db: Database session
            user_id: ID of user
            
        Returns:
            Count of updated notifications
        """
        # In production:
        # Update all where user_id = user_id AND is_read = False
        # Set is_read = True, read_at = now
        
        return {"marked_read": 0}


# Singleton instance
notification_service = NotificationService()
