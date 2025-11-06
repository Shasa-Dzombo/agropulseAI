# Incident Manager
# Manages the lifecycle of security incidents, which group related events.

import logging
import asyncio
import uuid
from datetime import datetime
from .protocol import Incident, IncidentStatus, IncidentLogEntry

logger = logging.getLogger(__name__)

class IncidentManager:
    def __init__(self, config, db_manager, alert_manager, nvr_system):
        self.config = config.get('incident_management', {})
        self.db_manager = db_manager
        self.alert_manager = alert_manager
        self.nvr_system = nvr_system # Get access to all managers
        self.is_enabled = self.config.get('enabled', False)
        logger.info(f"Incident Manager initialized. Enabled: {self.is_enabled}")

    async def create_incident_from_event(self, event_id, event_type, camera_id, details):
        """Creates a new incident, often triggered by a critical analytics event."""
        if not self.is_enabled:
            return None

        incident_id = str(uuid.uuid4())
        incident = Incident(
            incident_id=incident_id,
            status=IncidentStatus.NEW,
            severity=self.config.get('default_severity', 'MEDIUM'),
            created_at=datetime.utcnow().isoformat(),
            title=f"New Incident from {event_type} on {camera_id}"
        )
        
        await self.db_manager.save_incident(incident)
        
        log_entry = IncidentLogEntry(
            incident_id=incident_id,
            user="SYSTEM",
            action="CREATED",
            notes=f"Automatically generated from event {event_id}. Details: {details}"
        )
        await self.db_manager.add_incident_log(log_entry)
        
        logger.info(f"New incident '{incident_id}' created from event '{event_id}'.")
        await self.alert_manager.send_alert(
            "IncidentManager", 
            f"New Incident: {incident.title}", 
            level='critical'
        )

        # New: Dispatch mobile unit if configured
        if self.config.get('auto_dispatch_drone'):
            drone_id = self.config.get('default_drone_id', 'drone_1')
            await self.nvr_system.mobile_unit_manager.dispatch_unit_to_incident(drone_id, incident)

        return incident

    async def update_incident_status(self, incident_id, new_status: IncidentStatus, user, notes):
        """Updates the status of an incident (e.g., to In Progress, Resolved)."""
        success = await self.db_manager.update_incident_status(incident_id, new_status)
        if success:
            log_entry = IncidentLogEntry(
                incident_id=incident_id,
                user=user,
                action=f"STATUS_CHANGED_TO_{new_status.name}",
                notes=notes
            )
            await self.db_manager.add_incident_log(log_entry)
            logger.info(f"Incident '{incident_id}' status updated to {new_status.name} by {user}.")
        return success

    async def get_incident_details(self, incident_id):
        """Retrieves full details for an incident, including its events and logs."""
        return await self.db_manager.get_incident_with_details(incident_id)

    async def get_open_incidents(self):
        """Retrieves all incidents that are not resolved or false alarms."""
        return await self.db_manager.get_open_incidents()
