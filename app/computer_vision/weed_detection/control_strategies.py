# c:\Users\Codeternal\Desktop\AgroPulse\app\computer_vision\weed_detection\control_strategies.py

"""
Weed Control Strategy Database
==============================

This module provides a comprehensive database of control strategies for the
weeds defined in the `taxonomy` module. It acts as a decision-support system,
recommending chemical, mechanical, and organic control methods based on the
identified weed species.

The database is structured to provide actionable, multi-faceted advice,
considering factors like application timing, effectiveness, and environmental impact.

Key Features:
-------------
1.  **Structured Strategy Data**:
    -   The core data is a dictionary (`CONTROL_STRATEGIES`) keyed by the weed's
      scientific name.
    -   Each entry contains three main categories of control: `chemical`,
      `mechanical`, and `organic`.

2.  **Detailed Chemical Control Information**:
    -   **`active_ingredients`**: Lists effective chemical compounds.
    -   **`trade_names`**: Provides example product names (e.g., 'Roundup', '2,4-D Amine').
    -   **`application_timing`**: Specifies the optimal growth stage for application
      (e.g., 'post-emergence', 'pre-emergence').
    -   **`effectiveness`**: A qualitative rating (e.g., 'Good' to 'Excellent').
    -   **`resistance_notes`**: Crucial information about known herbicide resistance
      for that species (e.g., glyphosate resistance in Palmer Amaranth).

3.  **Mechanical Control Methods**:
    -   Lists physical removal techniques like `tillage`, `mowing`, `hand-pulling`,
      and `cultivation`.
    -   Includes notes on the effectiveness and best practices for each method,
      such as the timing of tillage to disrupt the weed's life cycle.

4.  **Organic and Cultural Control Methods**:
    -   Provides sustainable and non-chemical alternatives.
    -   **`mulching`**: Using materials like straw or plastic to block light.
    -   **`cover_crops`**: Planting dense crops like rye or clover to out-compete weeds.
    -   **`biological_control`**: Mentioning the use of insects or pathogens (where applicable).
    -   **`soil_management`**: Advice on improving soil health to favor crop growth.
    -   **`flame_weeding`**: Using targeted heat to kill young weeds.

5.  **`WeedControlAdvisor` Class**:
    -   A high-level service that provides an easy-to-use interface for querying
      the strategy database.
    -   **`get_strategy_for_weed()`**: Retrieves all control information for a given
      weed species by its scientific name.
    -   **`recommend_best_strategy()`**: A more advanced method that suggests the
      "best" strategy based on user preferences (e.g., 'organic_only', 'integrated').
      This demonstrates how the system can provide tailored recommendations.

This module transforms the weed detection system from a simple identification tool
into a powerful decision-making aid for precision agriculture, enabling users to
take immediate and informed action on weed infestations.
"""

import logging
from typing import Dict, List, Optional, Any, Literal

from .taxonomy import find_weed_by_name

# --- The Core Control Strategy Database ---
# This database links weed scientific names to control methods.
# In a production system, this would be a relational database.

CONTROL_STRATEGIES: Dict[str, Dict[str, Any]] = {
    "Amaranthus retroflexus": {
        "chemical": [
            {
                "active_ingredients": ["Glyphosate", "Dicamba", "2,4-D", "Atrazine"],
                "trade_names": ["Roundup", "Clarity", "2,4-D Amine", "Aatrex"],
                "application_timing": "Post-emergence, when weeds are small (less than 4 inches). Atrazine can be pre-emergence.",
                "effectiveness": "Good to Excellent, but check for local resistance.",
                "resistance_notes": "Some populations have developed resistance to glyphosate and ALS inhibitors."
            }
        ],
        "mechanical": [
            {
                "method": "Cultivation/Tillage",
                "description": "Shallow cultivation is very effective on young seedlings. Tillage can bury seeds, but also bring dormant seeds to the surface.",
                "effectiveness": "Excellent on young plants."
            },
            {
                "method": "Hand-pulling",
                "description": "Effective in small areas or gardens, especially after rain when the soil is moist.",
                "effectiveness": "Good for small infestations."
            }
        ],
        "organic": [
            {
                "method": "Mulching",
                "description": "Apply a thick layer of organic mulch (straw, wood chips) or use plastic mulch to block light.",
                "effectiveness": "Very Good."
            },
            {
                "method": "Flame Weeding",
                "description": "Effective on very young seedlings. The goal is to heat the plant to rupture cell walls, not to burn it.",
                "effectiveness": "Good on small plants."
            },
            {
                "method": "Cover Crops",
                "description": "A dense stand of a competitive cover crop like cereal rye can suppress germination and growth.",
                "effectiveness": "Good."
            }
        ]
    },
    "Amaranthus palmeri": {
        "chemical": [
            {
                "active_ingredients": ["Glufosinate", "Dicamba", "2,4-D", "PPO inhibitors (e.g., Fomesafen)"],
                "trade_names": ["Liberty", "XtendiMax", "Enlist Duo", "Flexstar"],
                "application_timing": "Crucial to spray when weeds are less than 3 inches tall. Use multiple modes of action and residual herbicides.",
                "effectiveness": "Variable due to widespread resistance.",
                "resistance_notes": "Widespread and severe resistance to glyphosate (Group 9) and ALS inhibitors (Group 2). Resistance to PPO inhibitors (Group 14) and HPPD inhibitors (Group 27) is also documented. A multi-pronged approach is mandatory."
            }
        ],
        "mechanical": [
            {
                "method": "Deep Tillage",
                "description": "One-time deep tillage can bury the seed bank, as Palmer Amaranth seeds do not emerge from deep in the soil profile.",
                "effectiveness": "Fair to Good (as part of a larger strategy)."
            },
            {
                "method": "Hand-weeding / Chopping",
                "description": "Often necessary to remove escaped plants before they go to seed. A single female plant can produce over 500,000 seeds.",
                "effectiveness": "Essential for escapes."
            }
        ],
        "organic": [
            {
                "method": "Cover Crops + Roller-Crimper",
                "description": "Planting a high-biomass cereal rye cover crop and then rolling it down to create a thick mulch mat is one of the most effective organic strategies.",
                "effectiveness": "Very Good."
            },
            {
                "method": "Tarping",
                "description": "Occultation (using black tarps to block all light) can kill existing plants and exhaust the shallow seed bank.",
                "effectiveness": "Excellent for small to medium-scale organic farms."
            }
        ]
    },
    "Chenopodium album": {
        "chemical": [
            {
                "active_ingredients": ["Glyphosate", "Dicamba", "Clopyralid", "Bromoxynil"],
                "trade_names": ["Roundup", "Clarity", "Stinger", "Buctril"],
                "application_timing": "Most effective on young, actively growing plants.",
                "effectiveness": "Good.",
                "resistance_notes": "Some populations show resistance to triazine (e.g., Atrazine) and ALS-inhibiting herbicides."
            }
        ],
        "mechanical": [
            {
                "method": "Cultivation/Hoeing",
                "description": "Very effective at controlling seedlings.",
                "effectiveness": "Excellent."
            }
        ],
        "organic": [
            {
                "method": "Stale Seed Bed",
                "description": "Prepare the seedbed, allow weeds to germinate, then kill them with shallow cultivation or flame weeding right before planting the crop.",
                "effectiveness": "Good."
            },
            {
                "method": "Vinegar (Acetic Acid)",
                "description": "Horticultural vinegar (20-30% acetic acid) can be used as a non-selective burndown herbicide on young seedlings. It is non-systemic.",
                "effectiveness": "Fair to Good on very small plants."
            }
        ]
    },
    "Cirsium arvense": {
        "chemical": [
            {
                "active_ingredients": ["Clopyralid", "Aminopyralid", "Dicamba", "Glyphosate"],
                "trade_names": ["Stinger", "Milestone", "Clarity", "Roundup"],
                "application_timing": "Most effective when applied at the bud to early flower stage or to rosettes in the fall. This timing allows the herbicide to translocate to the extensive root system.",
                "effectiveness": "Good to Excellent.",
                "resistance_notes": "Generally susceptible, but repeated applications are necessary due to the root system."
            }
        ],
        "mechanical": [
            {
                "method": "Tillage",
                "description": "Repeated, intensive tillage can eventually deplete the root system's energy reserves. However, infrequent tillage can break up roots and spread the infestation.",
                "effectiveness": "Fair (requires persistence)."
            },
            {
                "method": "Mowing",
                "description": "Repeated mowing at the bud stage can reduce seed production and slowly weaken the plant, but will not eliminate it.",
                "effectiveness": "Poor to Fair (for control), Good (for preventing seed spread)."
            }
        ],
        "organic": [
            {
                "method": "Biological Control",
                "description": "The thistle stem weevil (Ceutorhynchus litura) and the thistle head weevil (Rhinocyllus conicus) have been used with some success to reduce vigor and seed production.",
                "effectiveness": "Fair (long-term suppression)."
            },
            {
                "method": "Competitive Planting",
                "description": "Establishing a dense, healthy stand of perennial pasture grasses or alfalfa can effectively suppress Canada thistle.",
                "effectiveness": "Good (long-term)."
            }
        ]
    },
    "Convolvulus arvensis": {
        "chemical": [
            {
                "active_ingredients": ["Dicamba + 2,4-D", "Quinclorac", "Glyphosate"],
                "trade_names": ["Spectracide Weed Stop", "Drive XLR8", "Roundup"],
                "application_timing": "Most effective when applied at full bloom or in the fall before a frost. The plant must be actively growing to translocate herbicide to the roots.",
                "effectiveness": "Fair to Good. Requires repeated applications over several years.",
                "resistance_notes": "Not known for herbicide resistance, but its deep root system makes it difficult to kill."
            }
        ],
        "mechanical": [
            {
                "method": "Tillage",
                "description": "Must be done repeatedly (every 2-3 weeks) to exhaust root reserves. Infrequent tillage will worsen the problem by spreading root fragments.",
                "effectiveness": "Fair (if done correctly and persistently)."
            }
        ],
        "organic": [
            {
                "method": "Light Deprivation",
                "description": "Covering the infested area with heavy-duty black plastic or landscape fabric for at least 2-3 growing seasons can kill the plant and its root system.",
                "effectiveness": "Excellent (but slow and only practical for smaller areas)."
            },
            {
                "method": "Solarization",
                "description": "Covering moist soil with clear plastic during the hottest part of the summer can heat the soil and kill roots in the upper profile.",
                "effectiveness": "Fair."
            }
        ]
    },
    # Add more strategies for other weeds...
}

class WeedControlAdvisor:
    """
    A service to provide control strategy recommendations for identified weeds.
    """
    def __init__(self):
        self._strategies = CONTROL_STRATEGIES
        logging.info("WeedControlAdvisor initialized.")

    def get_strategy_for_weed(self, scientific_name: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves all available control strategies for a given weed.

        Args:
            scientific_name (str): The scientific name of the weed.

        Returns:
            A dictionary containing chemical, mechanical, and organic strategies, or None.
        """
        strategy = self._strategies.get(scientific_name)
        if not strategy:
            logging.warning(f"No control strategy found for '{scientific_name}'.")
        return strategy

    def recommend_best_strategy(
        self,
        scientific_name: str,
        preference: Literal['integrated', 'chemical_only', 'organic_only'] = 'integrated'
    ) -> Dict[str, Any]:
        """
        Provides a tailored recommendation based on user preference.

        Args:
            scientific_name (str): The scientific name of the weed.
            preference (str): The desired control approach.

        Returns:
            A dictionary with the recommended strategies.
        """
        full_strategy = self.get_strategy_for_weed(scientific_name)
        if not full_strategy:
            return {"error": f"No strategies found for {scientific_name}."}

        weed_info = find_weed_by_name(scientific_name)
        if not weed_info:
             return {"error": f"No taxonomy info found for {scientific_name}."}

        recommendation = {
            "weed": weed_info,
            "recommendation_preference": preference,
            "strategies": {}
        }

        if preference == 'integrated':
            # Integrated Pest Management (IPM) approach: combine methods
            recommendation['summary'] = f"An integrated approach is recommended for '{scientific_name}'. Combine mechanical or cultural methods with targeted chemical application for best results."
            recommendation['strategies'] = full_strategy
        
        elif preference == 'chemical_only':
            recommendation['summary'] = f"Chemical-only approach for '{scientific_name}'. Pay close attention to application timing and resistance notes."
            recommendation['strategies']['chemical'] = full_strategy.get('chemical')

        elif preference == 'organic_only':
            recommendation['summary'] = f"Organic-only approach for '{scientific_name}'. This requires persistence and often a combination of methods like mulching and cultivation."
            recommendation['strategies']['mechanical'] = full_strategy.get('mechanical')
            recommendation['strategies']['organic'] = full_strategy.get('organic')
        
        return recommendation

# --- Global Instance ---
advisor = WeedControlAdvisor()

# --- Example Usage ---
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # 1. Get strategy for a common weed
    print("\n--- Full Strategy for Palmer Amaranth ---")
    palmer_strategy = advisor.get_strategy_for_weed("Amaranthus palmeri")
    if palmer_strategy:
        print("Chemical Notes:", palmer_strategy['chemical'][0]['resistance_notes'])
        print("Organic Method:", palmer_strategy['organic'][0]['description'])

    # 2. Get a tailored recommendation for an organic-only approach
    print("\n--- Organic-Only Recommendation for Field Bindweed ---")
    bindweed_organic_rec = advisor.recommend_best_strategy("Convolvulus arvensis", preference='organic_only')
    print("Summary:", bindweed_organic_rec['summary'])
    print("Recommended Mechanical Method:", bindweed_organic_rec['strategies']['mechanical'][0]['method'])
    print("Recommended Organic Method:", bindweed_organic_rec['strategies']['organic'][0]['method'])
    print("Description:", bindweed_organic_rec['strategies']['organic'][0]['description'])

    # 3. Get an integrated recommendation for a perennial with a strong root system
    print("\n--- Integrated Recommendation for Canada Thistle ---")
    thistle_integrated_rec = advisor.recommend_best_strategy("Cirsium arvense", preference='integrated')
    print("Summary:", thistle_integrated_rec['summary'])
    print("Chemical Timing:", thistle_integrated_rec['strategies']['chemical'][0]['application_timing'])
    print("Mechanical Warning:", thistle_integrated_rec['strategies']['mechanical'][0]['description'])
```