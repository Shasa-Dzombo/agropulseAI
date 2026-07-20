"""
Maps AgroPulse's free-text Farm.crop_type to Kindwise's horticultural
CropType enum. Kindwise only covers 20 horticultural crops - most of this
project's seeded farms (maize, beans, wheat, sorghum, etc.) have no mapping
and must gracefully skip disease detection rather than crash or guess.
"""
from typing import Optional

from app.services._kindwise_client_loader import CropType

_CROP_TYPE_ALIASES = {
    "apple": CropType.APPLE,
    "banana": CropType.BANANA,
    "citrus": CropType.CITRUS, "orange": CropType.CITRUS, "lemon": CropType.CITRUS,
    "cucumber": CropType.CUCUMBER,
    "eggplant": CropType.EGGPLANT, "brinjal": CropType.EGGPLANT,
    "garlic": CropType.GARLIC,
    "grape": CropType.GRAPE, "grapes": CropType.GRAPE,
    "onion": CropType.ONION,
    "potato": CropType.POTATO,
    "tomato": CropType.TOMATO,
    "pepper": CropType.PEPPER, "capsicum": CropType.PEPPER, "chili": CropType.PEPPER,
    "strawberry": CropType.STRAWBERRY,
    "lettuce": CropType.LETTUCE,
    "cabbage": CropType.CABBAGE,
    "watermelon": CropType.WATERMELON,
    "coffee": CropType.COFFEE,
    "tea": CropType.TEA,
    "mango": CropType.MANGO,
    "peach": CropType.PEACH,
    "olive": CropType.OLIVE,
}


def map_farm_crop_type_to_kindwise(crop_type: Optional[str]) -> Optional[CropType]:
    """Returns None (never raises) if crop_type is missing or has no
    Kindwise mapping - caller must treat None as 'skip disease detection'."""
    if not crop_type:
        return None
    return _CROP_TYPE_ALIASES.get(crop_type.strip().lower())
