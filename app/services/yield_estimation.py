"""
A small, honest yield estimate: reference_yield_per_acre * farm_size_acres.

No weather adjustment yet, deliberately. The existing weather integration
(app.integrations.weather.openweather.get_agricultural_alerts) only produces
alerts from *current conditions + a 5-day forecast* - there's no
season-accumulated rainfall tracking in this app yet. Multiplying by a
"weather factor" built from a snapshot rather than the whole growing season
would overstate precision this app doesn't actually have. Revisit once
season-long rainfall accumulation exists.

Reference yields are real, sourced, national averages - not per-county
(KNBS's own site has a broken TLS certificate blocking automated access to
their county-level tables as of 2026-09; the numbers below come from
figures the report itself publishes at the national level):

- Maize: KNBS National Agriculture Production Report 2024 - 4,028,320
  tonnes over 2,414,536 ha nationally = 18.5 bags (90kg) per hectare
  = 1,665 kg/ha = ~674 kg/acre.
  https://www.knbs.or.ke/wp-content/uploads/2025/01/National-Agriculture-Production-Report-2024.pdf
- Beans: same report - 759,006 tonnes over 1,229,611 ha nationally
  = ~617 kg/ha = ~250 kg/acre.

Only these two crops are covered today. Anything else returns None rather
than a guessed number.
"""

from dataclasses import dataclass
from typing import Optional

REFERENCE_YIELD_KG_PER_ACRE = {
    "maize": 674.0,
    "beans": 250.0,
}

REFERENCE_YIELD_SOURCE = "KNBS National Agriculture Production Report 2024 (national average, not county-adjusted)"


@dataclass
class YieldEstimate:
    estimated_yield_kg: float
    source: str


def estimate_yield_kg(crop: str, farm_size_acres: Optional[float]) -> Optional[YieldEstimate]:
    """None when the crop isn't in the reference table or the farm has no
    recorded size - never a fabricated fallback number."""
    if not crop or not farm_size_acres or farm_size_acres <= 0:
        return None
    per_acre = REFERENCE_YIELD_KG_PER_ACRE.get(crop.strip().lower())
    if per_acre is None:
        return None
    return YieldEstimate(estimated_yield_kg=round(per_acre * farm_size_acres, 1), source=REFERENCE_YIELD_SOURCE)


# KALRO (Kenya Agricultural & Livestock Research Organization) trial figures
# for specific improved varieties under good management - NOT a realized
# average like REFERENCE_YIELD_KG_PER_ACRE above, so never used as the
# estimate baseline (that would overstate what a typical farm actually
# gets). Surfaced only as an informational tip: real, cited, named
# varieties, framed as "under good management" rather than a promise.
#
# - Maize: KALRO's newer MLN/fall-armyworm-tolerant and highland varieties
#   (e.g. UKAMEZ, FAWTH2002, H614D) - 25-42 bags (90kg) per acre = ~2,250-
#   3,780 kg/acre, vs the ~7.5 bags/acre (674 kg/acre) national average.
#   https://scienceafrica.co.ke/2023/04/03/kalro-new-maize-varieties-to-mitigate-against-climate-pests-and-diseases/
# - Beans: KALRO's Nyota variety - 1.4-2.0 t/ha (~567-810 kg/acre) vs the
#   ~250 kg/acre national average.
#   https://agrificsapp.kalro.org/file_uploads/Nyota%20bean%20production%20manual.pdf
KALRO_VARIETY_TIPS = {
    "maize": (
        "KALRO's newer improved maize varieties (e.g. UKAMEZ, FAWTH2002) have shown "
        "25-42 bags (90kg) per acre in trials under good management - well above the "
        "national average. Worth asking your local agrovet whether they're available."
    ),
    "beans": (
        "KALRO's Nyota bean variety has shown 1.4-2.0 tonnes per hectare in trials "
        "under good management - well above the national average. Worth asking your "
        "local agrovet whether it's available."
    ),
}


def kalro_variety_tip(crop: str) -> Optional[str]:
    if not crop:
        return None
    return KALRO_VARIETY_TIPS.get(crop.strip().lower())
