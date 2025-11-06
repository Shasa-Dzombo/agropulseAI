# AI-Powered Event Search Engine

import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class EventSearchEngine:
    def __init__(self, db_manager):
        self.db_manager = db_manager
        logger.info("AI Event Search Engine initialized.")

    async def search_events(self, camera_id=None, object_class=None, start_time_utc=None, end_time_utc=None, min_confidence=0.0):
        """
        Searches for events in the database based on AI metadata.
        """
        logger.info(f"Performing AI search with criteria: camera={camera_id}, class={object_class}, start={start_time_utc}, end={end_time_utc}")
        
        query = """
            SELECT DISTINCT e.event_id, e.timestamp_utc, e.camera_id, e.video_clip_path, e.blockchain_tx
            FROM events e
            JOIN detections d ON e.event_id = d.event_id
            WHERE 1=1
        """
        params = []

        if camera_id:
            query += " AND e.camera_id = ?"
            params.append(camera_id)
        
        if object_class:
            query += " AND d.class_name = ?"
            params.append(object_class)
            
        if start_time_utc:
            query += " AND e.timestamp_utc >= ?"
            params.append(start_time_utc)

        if end_time_utc:
            query += " AND e.timestamp_utc <= ?"
            params.append(end_time_utc)
            
        if min_confidence > 0.0:
            query += " AND d.confidence >= ?"
            params.append(min_confidence)
            
        query += " ORDER BY e.timestamp_utc DESC LIMIT 100"

        try:
            conn = await self.db_manager.get_connection()
            cursor = await conn.execute(query, tuple(params))
            rows = await cursor.fetchall()
            await cursor.close()
            
            results = [dict(row) for row in rows]
            return results
            
        except Exception as e:
            logger.error(f"Database search failed: {e}", exc_info=True)
            return []

    async def get_distinct_classes(self):
        """Gets a list of all object classes that have been detected."""
        query = "SELECT DISTINCT class_name FROM detections ORDER BY class_name ASC"
        try:
            conn = await self.db_manager.get_connection()
            cursor = await conn.execute(query)
            rows = await cursor.fetchall()
            await cursor.close()
            return [row['class_name'] for row in rows]
        except Exception as e:
            logger.error(f"Failed to get distinct classes from DB: {e}", exc_info=True)
            return []
