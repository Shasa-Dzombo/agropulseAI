"""
Direct Anthropic Claude API integration (not via AWS Bedrock).

AWSAIService.diagnose_crop_disease() depends on an AWS SageMaker endpoint
that isn't deployed (AWS_SAGEMAKER_ENDPOINT is unset in this environment),
and its generate_treatment_recommendations() targets the retired Claude 2
Bedrock text-completion API ("\\n\\nHuman: ... \\n\\nAssistant:"). This module
gives the same two capabilities using the current Anthropic Messages API and
a plain ANTHROPIC_API_KEY, so they work without AWS at all.
"""
import base64
import json
import time
from typing import Dict, List, Optional

import httpx
from anthropic import Anthropic, APIStatusError

from app.config import settings

DISEASE_CATEGORIES = [
    "fungal", "bacterial", "viral", "pest",
    "nutrient_deficiency", "environmental", "healthy",
]

_DIAGNOSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "primary_diagnosis": {"type": "string"},
        "category": {"type": "string", "enum": DISEASE_CATEGORIES},
        "confidence_score": {"type": "number"},
        "alternative_diagnoses": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "diagnosis": {"type": "string"},
                    "confidence": {"type": "number"},
                },
                "required": ["diagnosis", "confidence"],
                "additionalProperties": False,
            },
        },
        "affected_area_percentage": {"type": "number"},
        "severity_level": {
            "type": "string",
            "enum": ["none", "mild", "moderate", "severe", "critical"],
        },
        "treatment_recommendations": {"type": "array", "items": {"type": "string"}},
        "preventive_measures": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "primary_diagnosis", "category", "confidence_score",
        "alternative_diagnoses", "affected_area_percentage", "severity_level",
        "treatment_recommendations", "preventive_measures",
    ],
    "additionalProperties": False,
}

_RECOMMENDATIONS_SCHEMA = {
    "type": "object",
    "properties": {
        "immediate_steps": {"type": "array", "items": {"type": "string"}},
        "recommended_products": {"type": "array", "items": {"type": "string"}},
        "application_method_and_dosage": {"type": "string"},
        "preventive_measures": {"type": "array", "items": {"type": "string"}},
        "expected_recovery_timeline": {"type": "string"},
        "estimated_cost_ksh": {"type": "string"},
    },
    "required": [
        "immediate_steps", "recommended_products",
        "application_method_and_dosage", "preventive_measures",
        "expected_recovery_timeline", "estimated_cost_ksh",
    ],
    "additionalProperties": False,
}


class ClaudeNotConfiguredError(RuntimeError):
    """Raised when ANTHROPIC_API_KEY is unset."""


class ClaudeAIService:
    def __init__(self):
        self._client: Optional[Anthropic] = None

    @property
    def client(self) -> Anthropic:
        if not settings.ANTHROPIC_API_KEY:
            raise ClaudeNotConfiguredError(
                "ANTHROPIC_API_KEY is not set - add it to .env to enable "
                "Claude-powered diagnosis, treatment recommendations, and chat."
            )
        if self._client is None:
            self._client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        return self._client

    async def _image_block(self, url: str) -> Dict:
        """Fetch an image (S3 URL or local path) and return an inline base64 content block.

        Fetching and inlining (rather than passing image URLs straight through
        as {"type": "url", ...}) works regardless of whether the URL is a
        real public S3 object or a private/local path the Claude API can't
        reach itself.
        """
        media_type = "image/jpeg"
        if url.startswith("http://") or url.startswith("https://"):
            async with httpx.AsyncClient(timeout=30.0) as http_client:
                resp = await http_client.get(url)
                resp.raise_for_status()
                data = resp.content
                media_type = resp.headers.get("content-type", media_type).split(";")[0] or media_type
        else:
            with open(url, "rb") as f:
                data = f.read()
            if url.lower().endswith(".png"):
                media_type = "image/png"
            elif url.lower().endswith(".webp"):
                media_type = "image/webp"

        return {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": base64.standard_b64encode(data).decode("utf-8"),
            },
        }

    async def diagnose_crop_disease(
        self,
        image_urls: List[str],
        metadata: Optional[Dict] = None,
    ) -> Dict:
        """
        Vision-based crop disease diagnosis via Claude. Same return shape as
        AWSAIService.diagnose_crop_disease() so it's a drop-in replacement.
        """
        start_time = time.time()
        try:
            image_blocks = [await self._image_block(u) for u in image_urls]

            metadata_note = f"\n\nAdditional context: {json.dumps(metadata)}" if metadata else ""
            prompt = (
                "You are an expert plant pathologist reviewing photos of a greenhouse "
                "crop (tomatoes, lettuce, peppers, cucumbers, herbs, or ornamentals) "
                "submitted by a farmer in Kenya. Examine the image(s) and diagnose any "
                "disease, pest damage, nutrient deficiency, or environmental stress "
                "visible. If the plant looks healthy, say so with category 'healthy'. "
                "Give practical treatment recommendations a smallholder farmer can act "
                "on locally." + metadata_note
            )

            response = self.client.messages.create(
                model=settings.ANTHROPIC_MODEL,
                max_tokens=2048,
                output_config={"format": {"type": "json_schema", "schema": _DIAGNOSIS_SCHEMA}},
                messages=[{
                    "role": "user",
                    "content": [*image_blocks, {"type": "text", "text": prompt}],
                }],
            )

            if response.stop_reason == "refusal":
                raise RuntimeError("Claude declined to process this request (safety refusal)")

            text = next(b.text for b in response.content if b.type == "text")
            result = json.loads(text)
            processing_time = time.time() - start_time

            return {
                "success": True,
                "primary_diagnosis": result["primary_diagnosis"],
                "confidence_score": result["confidence_score"],
                "category": result["category"],
                "alternative_diagnoses": result["alternative_diagnoses"],
                "affected_area_percentage": result["affected_area_percentage"],
                "severity_level": result["severity_level"],
                "treatment_recommendations": result["treatment_recommendations"],
                "preventive_measures": result["preventive_measures"],
                "processing_time_seconds": processing_time,
                "ai_model_version": settings.ANTHROPIC_MODEL,
            }

        except ClaudeNotConfiguredError:
            raise
        except Exception as e:
            print(f"Error in Claude crop diagnosis: {e}")
            return {
                "success": False,
                "error": str(e),
                "processing_time_seconds": time.time() - start_time,
            }

    async def generate_treatment_recommendations(
        self,
        diagnosis: str,
        crop_type: str,
        severity: str,
    ) -> Dict:
        """Modern replacement for AWSAIService.generate_treatment_recommendations()."""
        try:
            prompt = (
                f"You are an expert agronomist advising a smallholder farmer in Kenya.\n\n"
                f"Crop: {crop_type}\nDiagnosis: {diagnosis}\nSeverity: {severity}\n\n"
                "Provide immediate treatment steps, recommended products (pesticides, "
                "fungicides, or fertilizers - prefer ones available in Kenyan agrovet "
                "shops), application method and dosage, preventive measures, expected "
                "recovery timeline, and an estimated cost range in Kenyan Shillings (KSh)."
            )

            response = self.client.messages.create(
                model=settings.ANTHROPIC_MODEL,
                max_tokens=1500,
                output_config={"format": {"type": "json_schema", "schema": _RECOMMENDATIONS_SCHEMA}},
                messages=[{"role": "user", "content": prompt}],
            )

            if response.stop_reason == "refusal":
                return {"success": False, "error": "Claude declined to process this request"}

            text = next(b.text for b in response.content if b.type == "text")
            return {"success": True, "recommendations": json.loads(text)}

        except ClaudeNotConfiguredError:
            raise
        except Exception as e:
            print(f"Error generating recommendations: {e}")
            return {"success": False, "error": str(e)}

    async def chat(self, message: str, context: Optional[str] = None) -> str:
        """Free-form farmer assistant reply, used as the chatbot's fallback
        for anything the keyword-routed logic in app/api/optimization.py
        doesn't handle."""
        system = (
            "You are AgroPulse's farming assistant, helping smallholder farmers in "
            "Kenya manage crop health, scouting, and diagnoses. Be concise and "
            "practical. If the farmer needs to take an action the app supports "
            "(buying a diagnosis permit, creating a scouting plan, viewing alerts), "
            "tell them plainly what to do."
        )
        if context:
            system += f"\n\nContext: {context}"

        response = self.client.messages.create(
            model=settings.ANTHROPIC_MODEL,
            max_tokens=512,
            system=system,
            messages=[{"role": "user", "content": message}],
        )
        if response.stop_reason == "refusal":
            return "Sorry, I can't help with that request."
        return next(b.text for b in response.content if b.type == "text")


claude_ai_service = ClaudeAIService()
