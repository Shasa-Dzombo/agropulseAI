"""
Multi-provider AI service - vision-based crop disease diagnosis, treatment
recommendations, and the farmer chatbot.

LLM_PROVIDER (app/config.py) picks which backend handles all three: "openai"
(default) | "anthropic" | "ollama" | "openweight" (any OpenAI-compatible
endpoint - self-hosted vLLM, a private inference gateway, etc). Mirrors the
provider-switch pattern from the AgentCustodian project's
src/core/shared/llm.py, adapted here for vision input and JSON-schema-
constrained output, which that project's plain-text-only chat use case didn't
need. Unlike that project, Ollama is reached here through its own OpenAI-
compatible /v1 endpoint rather than a native client library, so every
non-Anthropic provider shares one `openai.OpenAI` code path instead of a
second dependency.
"""
import base64
import json
import time
from typing import Dict, List, Optional

import httpx
from anthropic import Anthropic
from openai import OpenAI

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

# For AIService.analyze_drone_photo - a wide/aerial survey shot, not a single
# close-up symptom photo (diagnose_crop_disease above), so it's a separate
# schema: estimated_count/count_notes only make sense here, and
# affected_area_percentage means "share of the visible plot", not "share of
# one leaf". Both count fields stay nullable (rather than a second schema
# variant) since a farmer can pick "health", "count", or both as survey
# goals - see app.schemas.drone.CreateManualFlightRequest.survey_goals.
_DRONE_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "primary_diagnosis": {"type": "string"},
        "category": {"type": "string", "enum": DISEASE_CATEGORIES},
        "confidence_score": {"type": "number"},
        "severity_level": {"type": "string", "enum": ["none", "mild", "moderate", "severe", "critical"]},
        "affected_area_percentage": {"type": "number"},
        "treatment_recommendations": {"type": "array", "items": {"type": "string"}},
        "preventive_measures": {"type": "array", "items": {"type": "string"}},
        "estimated_count": {"type": ["integer", "null"]},
        "count_notes": {"type": ["string", "null"]},
    },
    "required": [
        "primary_diagnosis", "category", "confidence_score", "severity_level",
        "affected_area_percentage", "treatment_recommendations", "preventive_measures",
        "estimated_count", "count_notes",
    ],
    "additionalProperties": False,
}


class AIServiceNotConfiguredError(RuntimeError):
    """Raised when the active LLM_PROVIDER has no API key/model set."""


def _provider() -> str:
    return (settings.LLM_PROVIDER or "openai").strip().lower()


def _model() -> str:
    if not settings.LLM_MODEL:
        raise AIServiceNotConfiguredError(
            f"LLM_MODEL is not set - add it to .env to enable AI diagnosis, "
            f"treatment recommendations, and chat (LLM_PROVIDER={_provider()!r})."
        )
    return settings.LLM_MODEL


def _api_key() -> str:
    provider = _provider()
    if provider == "anthropic":
        return settings.ANTHROPIC_API_KEY or ""
    if provider == "ollama":
        return settings.OLLAMA_API_KEY or ""
    if provider == "openweight":
        return settings.OPEN_WEIGHT_API_KEY or ""
    return settings.OPENAI_API_KEY or ""


def _base_url() -> Optional[str]:
    provider = _provider()
    if provider == "ollama":
        return (settings.OLLAMA_API_URL or "http://localhost:11434").rstrip("/") + "/v1"
    if provider == "openweight":
        # Already includes /v1 by convention (see app/config.py).
        return (settings.OPEN_WEIGHT_BASE_URL or "").rstrip("/") or None
    if provider == "openai":
        return (settings.OPENAI_API_URL or "").rstrip("/") or None
    return None


def _require_key() -> str:
    key = _api_key()
    provider = _provider()
    if provider == "ollama":
        return key or "ollama"  # local daemon needs no real key
    if not key:
        raise AIServiceNotConfiguredError(
            f"No API key is set for LLM_PROVIDER={provider!r} - add the matching "
            "key to .env (e.g. OPENAI_API_KEY, ANTHROPIC_API_KEY, OPEN_WEIGHT_API_KEY)."
        )
    return key


def _schema_field_desc(name: str, spec: dict) -> str:
    field_type = spec.get("type")
    if isinstance(field_type, list):
        return f'"{name}": {" or ".join(field_type)} (use null if not applicable)'
    if field_type == "array":
        item = spec["items"]
        if item.get("type") == "object":
            inner = ", ".join(f'"{k}" ({v["type"]})' for k, v in item["properties"].items())
            return f'"{name}": array of objects, each with {inner}'
        return f'"{name}": array of {item["type"]}s'
    if "enum" in spec:
        return f'"{name}": one of {", ".join(repr(v) for v in spec["enum"])}'
    return f'"{name}": {field_type}'


def _schema_prompt_block(schema: dict) -> str:
    """Renders a flat/shallow JSON schema as plain-English field instructions -
    a workaround for OpenAI-compatible endpoints (self-hosted vLLM, gateways,
    etc) that accept response_format={"type": "json_schema", ...} without
    actually enforcing it. response_format={"type": "json_object"} (just
    "return valid JSON") is far more reliably honored, so the schema has to
    be spelled out in the prompt instead of relied on as a hard constraint."""
    lines = "\n".join(f"- {_schema_field_desc(name, spec)}" for name, spec in schema["properties"].items())
    return f"Respond with ONLY a single JSON object (no markdown, no prose, no code fences) with exactly these keys:\n{lines}"


async def _fetch_image(url: str) -> tuple[bytes, str]:
    """Fetch an image (S3 URL or local path) and return (bytes, media_type)."""
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
    return data, media_type


class AIService:
    def __init__(self):
        self._anthropic_client: Optional[Anthropic] = None
        self._openai_client: Optional[OpenAI] = None

    @property
    def anthropic(self) -> Anthropic:
        if not settings.ANTHROPIC_API_KEY:
            raise AIServiceNotConfiguredError(
                "ANTHROPIC_API_KEY is not set - add it to .env, or switch "
                "LLM_PROVIDER away from 'anthropic'."
            )
        if self._anthropic_client is None:
            self._anthropic_client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        return self._anthropic_client

    @property
    def openai_compatible(self) -> OpenAI:
        if self._openai_client is None:
            self._openai_client = OpenAI(api_key=_require_key(), base_url=_base_url())
        return self._openai_client

    async def _image_block(self, url: str) -> Dict:
        """Provider-appropriate inline image content block."""
        data, media_type = await _fetch_image(url)
        b64 = base64.standard_b64encode(data).decode("utf-8")
        if _provider() == "anthropic":
            return {
                "type": "image",
                "source": {"type": "base64", "media_type": media_type, "data": b64},
            }
        return {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{b64}"}}

    async def diagnose_crop_disease(
        self,
        image_urls: List[str],
        metadata: Optional[Dict] = None,
    ) -> Dict:
        """Vision-based crop disease diagnosis. Same return shape regardless
        of provider, so callers don't need to know which one is active."""
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

            if _provider() == "anthropic":
                response = self.anthropic.messages.create(
                    model=_model(),
                    max_tokens=2048,
                    output_config={"format": {"type": "json_schema", "schema": _DIAGNOSIS_SCHEMA}},
                    messages=[{
                        "role": "user",
                        "content": [*image_blocks, {"type": "text", "text": prompt}],
                    }],
                )
                if response.stop_reason == "refusal":
                    raise RuntimeError("The model declined to process this request (safety refusal)")
                text = next(b.text for b in response.content if b.type == "text")
            else:
                completion = self.openai_compatible.chat.completions.create(
                    model=_model(),
                    max_tokens=2048,
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt + "\n\n" + _schema_prompt_block(_DIAGNOSIS_SCHEMA)},
                            *image_blocks,
                        ],
                    }],
                    response_format={"type": "json_object"},
                )
                choice = completion.choices[0]
                if choice.finish_reason == "content_filter":
                    raise RuntimeError("The model declined to process this request (content filter)")
                text = choice.message.content

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
                "ai_model_version": f"{_provider()}:{_model()}",
            }

        except AIServiceNotConfiguredError:
            raise
        except Exception as e:
            print(f"Error in AI crop diagnosis: {e}")
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
        try:
            prompt = (
                f"You are an expert agronomist advising a smallholder farmer in Kenya.\n\n"
                f"Crop: {crop_type}\nDiagnosis: {diagnosis}\nSeverity: {severity}\n\n"
                "Provide immediate treatment steps, recommended products (pesticides, "
                "fungicides, or fertilizers - prefer ones available in Kenyan agrovet "
                "shops), application method and dosage, preventive measures, expected "
                "recovery timeline, and an estimated cost range in Kenyan Shillings (KSh)."
            )

            if _provider() == "anthropic":
                response = self.anthropic.messages.create(
                    model=_model(),
                    max_tokens=2500,
                    output_config={"format": {"type": "json_schema", "schema": _RECOMMENDATIONS_SCHEMA}},
                    messages=[{"role": "user", "content": prompt}],
                )
                if response.stop_reason == "refusal":
                    return {"success": False, "error": "The model declined to process this request"}
                text = next(b.text for b in response.content if b.type == "text")
            else:
                completion = self.openai_compatible.chat.completions.create(
                    model=_model(),
                    max_tokens=2500,
                    messages=[{"role": "user", "content": prompt + "\n\n" + _schema_prompt_block(_RECOMMENDATIONS_SCHEMA)}],
                    response_format={"type": "json_object"},
                )
                choice = completion.choices[0]
                if choice.finish_reason == "content_filter":
                    return {"success": False, "error": "The model declined to process this request"}
                text = choice.message.content

            return {"success": True, "recommendations": json.loads(text)}

        except AIServiceNotConfiguredError:
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

        if _provider() == "anthropic":
            response = self.anthropic.messages.create(
                model=_model(),
                max_tokens=512,
                system=system,
                messages=[{"role": "user", "content": message}],
            )
            if response.stop_reason == "refusal":
                return "Sorry, I can't help with that request."
            return next(b.text for b in response.content if b.type == "text")

        completion = self.openai_compatible.chat.completions.create(
            model=_model(),
            max_tokens=512,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": message},
            ],
        )
        choice = completion.choices[0]
        if choice.finish_reason == "content_filter":
            return "Sorry, I can't help with that request."
        return choice.message.content

    async def analyze_drone_photo(
        self,
        image_url: str,
        survey_goals: Optional[List[str]] = None,
        survey_notes: Optional[str] = None,
        farm_context: Optional[str] = None,
    ) -> Dict:
        """Goal-aware analysis of one aerial/wide-shot drone photo - distinct
        from diagnose_crop_disease (a single close-up symptom photo). Asks
        for a health read, a rough visible-plant/tree count, or both,
        depending on survey_goals (defaults to health if unset), and folds
        in the farm's own recent input/yield history as context when given
        (see DroneAIService._build_farm_context)."""
        start_time = time.time()
        goals = survey_goals or ["health"]
        try:
            image_block = await self._image_block(image_url)

            instructions = []
            if "health" in goals:
                instructions.append(
                    "Assess plant health across the visible area: diagnose any disease, "
                    "pest damage, nutrient deficiency, or environmental stress; use "
                    "category 'healthy' if nothing is wrong. Estimate the percentage of "
                    "the visible plot that's affected."
                )
            if "count" in goals:
                instructions.append(
                    "Count the individual plants or trees clearly visible in the photo "
                    "as best you can, and use count_notes for anything that makes the "
                    "count uncertain (overlapping canopies, photo edge cutoff, etc). "
                    "Leave estimated_count/count_notes null if this wasn't requested."
                )
            if not instructions:
                instructions.append("Give a general assessment of what's visible in the photo.")

            context_lines = []
            if survey_notes:
                context_lines.append(f"Farmer's notes for this survey: {survey_notes}")
            if farm_context:
                context_lines.append(farm_context)

            prompt = (
                "You are an expert agronomist reviewing an aerial/wide-angle drone photo "
                "of a farm plot in Kenya (fruit/nut trees, or a field crop).\n\n"
                + "\n".join(instructions)
                + ("\n\n" + "\n".join(context_lines) if context_lines else "")
            )

            if _provider() == "anthropic":
                response = self.anthropic.messages.create(
                    model=_model(),
                    max_tokens=2048,
                    output_config={"format": {"type": "json_schema", "schema": _DRONE_ANALYSIS_SCHEMA}},
                    messages=[{"role": "user", "content": [image_block, {"type": "text", "text": prompt}]}],
                )
                if response.stop_reason == "refusal":
                    raise RuntimeError("The model declined to process this request (safety refusal)")
                text = next(b.text for b in response.content if b.type == "text")
            else:
                completion = self.openai_compatible.chat.completions.create(
                    model=_model(),
                    max_tokens=2048,
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt + "\n\n" + _schema_prompt_block(_DRONE_ANALYSIS_SCHEMA)},
                            image_block,
                        ],
                    }],
                    response_format={"type": "json_object"},
                )
                choice = completion.choices[0]
                if choice.finish_reason == "content_filter":
                    raise RuntimeError("The model declined to process this request (content filter)")
                text = choice.message.content

            result = json.loads(text)
            processing_time = time.time() - start_time
            return {
                "success": True,
                **result,
                "processing_time_seconds": processing_time,
                "ai_model_version": f"{_provider()}:{_model()}",
            }

        except AIServiceNotConfiguredError:
            raise
        except Exception as e:
            print(f"Error in AI drone photo analysis: {e}")
            return {
                "success": False,
                "error": str(e),
                "processing_time_seconds": time.time() - start_time,
            }


ai_service = AIService()
