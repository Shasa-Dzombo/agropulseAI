# c:\Users\Codeternal\Desktop\AgroPulse\app\computer_vision\weed_detection\taxonomy.py

"""
Weed Taxonomy and Classification
=================================

This module provides a comprehensive and structured taxonomy of common agricultural
weeds. It serves as the definitive source for weed identification, classification,
and metadata within the AgroPulse system.

The taxonomy is designed to be a rich, hierarchical, and extensible data source,
enabling the object detection model to be trained on a fine-grained set of classes
and allowing the decision support system to retrieve detailed information about
each detected weed.

Key Features:
-------------
1.  **Hierarchical Structure**:
    -   Weeds are organized by `family` -> `genus` -> `species`. This botanical
      structure is crucial for understanding relationships between weeds and for
      applying broad-spectrum treatments that might affect an entire family.

2.  **Rich Metadata**:
    -   Each species entry contains a wealth of information:
        -   `scientific_name`: The unique botanical name (e.g., 'Amaranthus retroflexus').
        -   `common_names`: A list of common names (e.g., 'red-root pigweed', 'common amaranth').
        -   `class_id`: A unique integer ID used for training the ML model.
        -   `life_cycle`: Categorizes the weed as 'annual', 'biennial', or 'perennial'.
        -   `growth_habit`: Describes its physical form (e.g., 'broadleaf', 'grass', 'sedge').
        -   `identification_features`: Detailed textual descriptions of leaves, stems,
          flowers, and roots to aid in manual verification.
        -   `reproduction_method`: How the weed spreads (e.g., 'seeds', 'rhizomes').
        -   `toxicity`: Information on whether the weed is toxic to livestock or humans.
        -   `typical_habitat`: The types of environments where it's commonly found.

3.  **Utility Functions**:
    -   `get_taxonomy_as_dict()`: Returns the entire taxonomy structure.
    -   `get_class_map()`: Generates a mapping from scientific name to `class_id`,
      essential for configuring the model's output layer.
    -   `get_reverse_class_map()`: Creates a reverse mapping from `class_id` to name,
      used in post-processing predictions.
    -   `find_weed_by_name()`: A search function to retrieve a weed's full data
      by its scientific or common name.

4.  **Scalability**:
    -   The data is stored in a clean, readable format that can be easily expanded
      with hundreds or thousands of additional species. In a production system,
      this data could be loaded from a dedicated database (e.g., PostgreSQL with
      a 'taxonomy' table) or a configuration file service.

This module is the bedrock of the advanced weed management system, ensuring that
all other components operate on a consistent and detailed understanding of
different weed species.
"""

import logging
from typing import Dict, List, Optional, Any

# --- The Core Weed Taxonomy Data Structure ---
# In a production system, this would likely be stored in a database.
# For this implementation, a comprehensive dictionary provides a clear and
# extensible structure.

WEED_TAXONOMY: Dict[str, Dict[str, Any]] = {
    "Amaranthaceae": {
        "common_name": "Amaranth Family",
        "genera": {
            "Amaranthus": {
                "species": [
                    {
                        "scientific_name": "Amaranthus retroflexus",
                        "common_names": ["red-root pigweed", "common amaranth"],
                        "class_id": 1,
                        "life_cycle": "annual",
                        "growth_habit": "broadleaf",
                        "identification_features": {
                            "leaves": "Alternate, simple, ovate to diamond-shaped with wavy margins. Undersides have prominent veins and are often reddish.",
                            "stem": "Erect, stout, freely branched, covered in fine hairs. Lower stem is often reddish.",
                            "flowers": "Small, green, inconspicuous flowers packed into dense, bristly terminal spikes.",
                            "root": "Shallow, reddish taproot.",
                        },
                        "reproduction_method": "seeds",
                        "toxicity": "Can accumulate nitrates, making it toxic to livestock if consumed in large quantities.",
                        "typical_habitat": "Cultivated fields, gardens, disturbed soils, waste areas."
                    },
                    {
                        "scientific_name": "Amaranthus palmeri",
                        "common_names": ["palmer amaranth", "carelessweed"],
                        "class_id": 2,
                        "life_cycle": "annual",
                        "growth_habit": "broadleaf",
                        "identification_features": {
                            "leaves": "Alternate, simple, lance-shaped to ovate, with a small spine at the tip. Petioles are often longer than the leaf blade.",
                            "stem": "Erect, smooth, hairless, can grow up to 10 feet tall.",
                            "flowers": "Male and female flowers on separate plants (dioecious). Female flower bracts are sharp and spiny.",
                            "root": "Deep taproot.",
                        },
                        "reproduction_method": "seeds",
                        "toxicity": "High nitrate accumulator. Known for widespread herbicide resistance.",
                        "typical_habitat": "Row crops (corn, soy, cotton), disturbed areas. Thrives in heat."
                    },
                ]
            },
            "Chenopodium": {
                "species": [
                    {
                        "scientific_name": "Chenopodium album",
                        "common_names": ["common lambsquarters", "fat-hen", "white goosefoot"],
                        "class_id": 3,
                        "life_cycle": "annual",
                        "growth_habit": "broadleaf",
                        "identification_features": {
                            "leaves": "Alternate, variable shape (diamond to lance-shaped), with toothed margins. Young leaves are covered in a white, mealy powder.",
                            "stem": "Erect, branched, often with reddish or light green vertical stripes.",
                            "flowers": "Small, greenish, non-petaled flowers in dense clusters at stem tips and leaf axils.",
                            "root": "Short taproot.",
                        },
                        "reproduction_method": "seeds",
                        "toxicity": "Can accumulate nitrates and oxalates. Generally low toxicity but can be an issue if it's the primary forage.",
                        "typical_habitat": "Extremely common in cultivated fields, gardens, and disturbed soils worldwide."
                    }
                ]
            }
        }
    },
    "Asteraceae": {
        "common_name": "Aster/Sunflower Family",
        "genera": {
            "Ambrosia": {
                "species": [
                    {
                        "scientific_name": "Ambrosia artemisiifolia",
                        "common_names": ["common ragweed"],
                        "class_id": 4,
                        "life_cycle": "annual",
                        "growth_habit": "broadleaf",
                        "identification_features": {
                            "leaves": "Opposite below, alternate above. Deeply dissected and fern-like. Hairy on both surfaces.",
                            "stem": "Erect, branched, covered in rough hairs.",
                            "flowers": "Produces copious amounts of pollen. Male flowers in long, terminal spikes; female flowers in leaf axils below.",
                            "root": "Fibrous root system.",
                        },
                        "reproduction_method": "seeds",
                        "toxicity": "Pollen is a major cause of hay fever. Not typically grazed by livestock.",
                        "typical_habitat": "Pastures, row crops, roadsides, disturbed areas."
                    },
                    {
                        "scientific_name": "Ambrosia trifida",
                        "common_names": ["giant ragweed"],
                        "class_id": 5,
                        "life_cycle": "annual",
                        "growth_habit": "broadleaf",
                        "identification_features": {
                            "leaves": "Opposite, very large. Most have 3-5 deep lobes, but upper leaves can be unlobed. Rough texture.",
                            "stem": "Thick, stout, can grow over 15 feet tall. May be branched.",
                            "flowers": "Similar to common ragweed but larger.",
                            "root": "Fibrous root system and a small taproot.",
                        },
                        "reproduction_method": "seeds",
                        "toxicity": "Pollen is a severe allergen. Competes aggressively with crops for light.",
                        "typical_habitat": "Fertile, disturbed soils. Common in corn and soybean fields."
                    }
                ]
            },
            "Cirsium": {
                "species": [
                    {
                        "scientific_name": "Cirsium arvense",
                        "common_names": ["canada thistle", "creeping thistle"],
                        "class_id": 6,
                        "life_cycle": "perennial",
                        "growth_habit": "broadleaf",
                        "identification_features": {
                            "leaves": "Alternate, oblong or lance-shaped, with spiny, crinkled margins. Can be hairless to slightly hairy underneath.",
                            "stem": "Erect, slender, ridged, and branched. Can grow up to 4-5 feet.",
                            "flowers": "Small, compact flower heads (less than 1 inch diameter), typically purple or pink. Dioecious.",
                            "root": "Extensive horizontal and vertical creeping roots (rhizomes).",
                        },
                        "reproduction_method": "rhizomes and seeds",
                        "toxicity": "Not toxic, but the spines deter grazing.",
                        "typical_habitat": "Pastures, rangeland, crops, roadsides. Very difficult to control due to root system."
                    }
                ]
            },
            "Taraxacum": {
                "species": [
                    {
                        "scientific_name": "Taraxacum officinale",
                        "common_names": ["dandelion"],
                        "class_id": 7,
                        "life_cycle": "perennial",
                        "growth_habit": "broadleaf",
                        "identification_features": {
                            "leaves": "Forms a basal rosette. Leaves are simple, deeply lobed with teeth pointing towards the base.",
                            "stem": "Flower stems are leafless, hollow, and exude a milky sap when broken.",
                            "flowers": "Iconic bright yellow composite flower heads, which mature into a white, spherical seed head ('blowball').",
                            "root": "Thick, fleshy, deep taproot.",
                        },
                        "reproduction_method": "seeds (wind-dispersed) and root fragments",
                        "toxicity": "Non-toxic. Edible for humans and palatable to livestock.",
                        "typical_habitat": "Lawns, pastures, orchards, and cultivated fields. A sign of soil compaction."
                    }
                ]
            }
        }
    },
    "Poaceae": {
        "common_name": "Grass Family",
        "genera": {
            "Digitaria": {
                "species": [
                    {
                        "scientific_name": "Digitaria sanguinalis",
                        "common_names": ["large crabgrass", "hairy crabgrass"],
                        "class_id": 8,
                        "life_cycle": "annual",
                        "growth_habit": "grass",
                        "identification_features": {
                            "leaves": "Blades are rolled in the bud, wide (5-10mm), and covered with coarse hairs. Ligule is a tall, jagged membrane.",
                            "stem": "Stems grow prostrate, rooting at the nodes, creating a dense mat. Sheaths are hairy.",
                            "flowers": "Seedhead consists of 3-10 finger-like branches (racemes) clustered at the top of the stem.",
                            "root": "Fibrous and shallow.",
                        },
                        "reproduction_method": "seeds and rooting from nodes",
                        "toxicity": "Non-toxic. Can be used as forage but is generally considered a weed.",
                        "typical_habitat": "Lawns, turf, cultivated fields, gardens. Thrives in summer heat."
                    }
                ]
            },
            "Setaria": {
                "species": [
                    {
                        "scientific_name": "Setaria viridis",
                        "common_names": ["green foxtail"],
                        "class_id": 9,
                        "life_cycle": "annual",
                        "growth_habit": "grass",
                        "identification_features": {
                            "leaves": "Blades are rolled in the bud, hairless. Ligule is a fringe of hairs.",
                            "stem": "Erect or ascending from a branching base. Lower leaf sheaths may have hairs along the margin.",
                            "flowers": "Dense, soft, bristly, spike-like panicle that resembles a fox's tail. Bristles are green.",
                            "root": "Fibrous.",
                        },
                        "reproduction_method": "seeds",
                        "toxicity": "Non-toxic.",
                        "typical_habitat": "Row crops, small grains, disturbed areas."
                    },
                    {
                        "scientific_name": "Setaria faberi",
                        "common_names": ["giant foxtail"],
                        "class_id": 10,
                        "life_cycle": "annual",
                        "growth_habit": "grass",
                        "identification_features": {
                            "leaves": "Similar to green foxtail but larger. Upper surface of the leaf blade is covered in short, fine hairs.",
                            "stem": "Can grow much taller than green foxtail, up to 7 feet.",
                            "flowers": "Seedhead is larger and distinctly drooping or nodding.",
                            "root": "Fibrous.",
                        },
                        "reproduction_method": "seeds",
                        "toxicity": "Non-toxic.",
                        "typical_habitat": "Very common and competitive in corn and soybean fields."
                    }
                ]
            },
            "Echinochloa": {
                "species": [
                    {
                        "scientific_name": "Echinochloa crus-galli",
                        "common_names": ["barnyardgrass"],
                        "class_id": 11,
                        "life_cycle": "annual",
                        "growth_habit": "grass",
                        "identification_features": {
                            "leaves": "Rolled in the bud. Key feature: lacks both a ligule and auricles.",
                            "stem": "Stems are flattened at the base, often reddish-purple. Erect or spreading.",
                            "flowers": "Coarse, compact, or open panicle with green to purplish spikelets that are often bristly.",
                            "root": "Fibrous.",
                        },
                        "reproduction_method": "seeds",
                        "toxicity": "Can accumulate nitrates.",
                        "typical_habitat": "Wet areas, irrigated crops (especially rice), cornfields, orchards."
                    }
                ]
            }
        }
    },
    "Convolvulaceae": {
        "common_name": "Morning-glory Family",
        "genera": {
            "Convolvulus": {
                "species": [
                    {
                        "scientific_name": "Convolvulus arvensis",
                        "common_names": ["field bindweed"],
                        "class_id": 12,
                        "life_cycle": "perennial",
                        "growth_habit": "broadleaf vine",
                        "identification_features": {
                            "leaves": "Alternate, arrowhead-shaped with a rounded or blunt tip and lobes at the base that point outward.",
                            "stem": "Twining, trailing vines that can grow along the ground or climb other plants. Can reach over 6 feet long.",
                            "flowers": "Funnel-shaped, about 1 inch in diameter, typically white or pink.",
                            "root": "Extremely deep and extensive root system with vertical and horizontal roots (rhizomes).",
                        },
                        "reproduction_method": "seeds and rhizomes",
                        "toxicity": "Mildly toxic to some animals, particularly horses, if consumed in large quantities.",
                        "typical_habitat": "Cultivated fields, vineyards, orchards, roadsides. Notorious for being difficult to control."
                    }
                ]
            }
        }
    },
    "Malvaceae": {
        "common_name": "Mallow Family",
        "genera": {
            "Abutilon": {
                "species": [
                    {
                        "scientific_name": "Abutilon theophrasti",
                        "common_names": ["velvetleaf", "butterprint", "pie-marker"],
                        "class_id": 13,
                        "life_cycle": "annual",
                        "growth_habit": "broadleaf",
                        "identification_features": {
                            "leaves": "Alternate, large, heart-shaped, and covered in soft, velvety hairs.",
                            "stem": "Erect, branched, covered in velvety hairs.",
                            "flowers": "Yellow-orange, 5-petaled flowers that open in the late afternoon.",
                            "root": "Fibrous taproot.",
                        },
                        "reproduction_method": "seeds",
                        "toxicity": "Non-toxic.",
                        "typical_habitat": "Corn and soybean fields, fence rows, waste areas."
                    }
                ]
            }
        }
    },
    "Brassicaceae": {
        "common_name": "Mustard Family",
        "genera": {
            "Capsella": {
                "species": [
                    {
                        "scientific_name": "Capsella bursa-pastoris",
                        "common_names": ["shepherd's purse"],
                        "class_id": 14,
                        "life_cycle": "annual/winter annual",
                        "growth_habit": "broadleaf",
                        "identification_features": {
                            "leaves": "Forms a basal rosette of lobed leaves, similar to a dandelion. Stem leaves are smaller and clasp the stem.",
                            "stem": "Erect, slender, sparsely branched.",
                            "flowers": "Tiny, white, 4-petaled flowers in a raceme that elongates as it matures.",
                            "root": "Thin taproot.",
                            "seed_pod": "Distinctive heart-shaped or triangular seed pods."
                        },
                        "reproduction_method": "seeds",
                        "toxicity": "Non-toxic.",
                        "typical_habitat": "Cultivated lands, gardens, lawns, waste areas. One of the most common weeds in the world."
                    }
                ]
            }
        }
    },
    # Add more families, genera, and species here...
}

# --- Utility Functions ---

def get_taxonomy_as_dict() -> Dict[str, Dict[str, Any]]:
    """Returns the complete, raw weed taxonomy dictionary."""
    return WEED_TAXONOMY

def get_class_map(add_background_class: bool = True) -> Dict[str, int]:
    """
    Generates a mapping of scientific_name -> class_id.

    Args:
        add_background_class (bool): If True, adds a '__background__' class with ID 0.

    Returns:
        A dictionary mapping weed names to their integer class IDs.
    """
    class_map = {}
    if add_background_class:
        class_map['__background__'] = 0
        
    for family_data in WEED_TAXONOMY.values():
        for genus_data in family_data['genera'].values():
            for species in genus_data['species']:
                if 'scientific_name' in species and 'class_id' in species:
                    class_map[species['scientific_name']] = species['class_id']
                else:
                    logging.warning(f"Skipping malformed species entry: {species}")
    return class_map

def get_reverse_class_map() -> Dict[int, str]:
    """
    Generates a mapping of class_id -> scientific_name.

    Returns:
        A dictionary mapping integer class IDs to weed names.
    """
    class_map = get_class_map(add_background_class=True)
    return {v: k for k, v in class_map.items()}

def get_all_species() -> List[Dict[str, Any]]:
    """
    Returns a flat list of all species dictionaries in the taxonomy.
    """
    all_species = []
    for family_data in WEED_TAXONOMY.values():
        for genus_data in family_data['genera'].values():
            all_species.extend(genus_data['species'])
    return all_species

def find_weed_by_name(name: str) -> Optional[Dict[str, Any]]:
    """

    Finds a weed's data by its scientific or common name.

    Args:
        name (str): The name to search for (case-insensitive).

    Returns:
        The full dictionary for the matching species, or None if not found.
    """
    name_lower = name.lower()
    for species in get_all_species():
        if species['scientific_name'].lower() == name_lower:
            return species
        if name_lower in [cn.lower() for cn in species['common_names']]:
            return species
    return None

def get_num_classes(include_background: bool = True) -> int:
    """
    Calculates the total number of distinct weed classes in the taxonomy.

    Args:
        include_background (bool): If True, adds 1 for the background class.

    Returns:
        The total number of classes.
    """
    # This is safer than just taking the max ID in case IDs are not contiguous
    num_classes = len(get_class_map(add_background_class=False))
    return num_classes + 1 if include_background else num_classes


# --- Example Usage ---
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # 1. Get the class map for model training
    model_class_map = get_class_map()
    print("--- Class Map for Model ---")
    print(model_class_map)
    print(f"\nTotal number of classes (including background): {get_num_classes()}")

    # 2. Get the reverse map for prediction output
    reverse_map = get_reverse_class_map()
    print("\n--- Reverse Class Map for Predictions ---")
    print(reverse_map)

    # 3. Find a specific weed and print its details
    print("\n--- Find Weed by Common Name ('field bindweed') ---")
    bindweed_data = find_weed_by_name("field bindweed")
    if bindweed_data:
        print(f"Scientific Name: {bindweed_data['scientific_name']}")
        print(f"Life Cycle: {bindweed_data['life_cycle']}")
        print(f"Reproduction: {bindweed_data['reproduction_method']}")
        print(f"Identification: {bindweed_data['identification_features']['stem']}")
    else:
        print("Weed not found.")

    # 4. Get a flat list of all species
    all_species_list = get_all_species()
    print(f"\n--- Total Species Defined ---")
    print(f"There are {len(all_species_list)} distinct weed species in the taxonomy.")
```