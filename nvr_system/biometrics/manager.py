# Biometrics Manager
# Manages facial profiles and voiceprints.

import logging
import asyncio
from .voice_recognition import VoiceRecognizer

logger = logging.getLogger(__name__)

class BiometricsManager:
    def __init__(self, config, db_manager):
        self.config = config.get('biometrics', {})
        self.db_manager = db_manager
        self.is_enabled = self.config.get('enabled', False)
        self.voice_recognizer = VoiceRecognizer(self.config)
        logger.info(f"Biometrics Manager initialized. Enabled: {self.is_enabled}")

    async def enroll_face(self, user_id, face_embedding):
        """Enrolls a new face embedding for a user."""
        if not self.is_enabled: return None
        return await self.db_manager.save_face_profile(user_id, face_embedding)

    async def enroll_voice(self, user_id, audio_sample_path):
        """Enrolls a new voiceprint from an audio sample."""
        if not self.is_enabled: return None
        voiceprint = self.voice_recognizer.create_voiceprint(audio_sample_path)
        if voiceprint:
            return await self.db_manager.save_voice_profile(user_id, voiceprint)
        return None

    async def identify_face(self, unknown_embedding):
        """Identifies a user from a face embedding."""
        if not self.is_enabled: return None
        return await self.db_manager.find_matching_face(unknown_embedding)

    async def verify_voice(self, user_id, audio_sample_path):
        """Verifies an audio sample against a user's enrolled voiceprint."""
        if not self.is_enabled: return False
        user_voiceprint = await self.db_manager.get_voice_profile(user_id)
        if user_voiceprint:
            return self.voice_recognizer.verify_voice(user_voiceprint, audio_sample_path)
        return False
