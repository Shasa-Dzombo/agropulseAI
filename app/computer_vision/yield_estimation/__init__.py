"""
Yield Estimation from Images
============================

This package contains the complete, end-to-end pipeline for estimating agricultural
yield from various forms of imagery, including drone, satellite, and ground-based
photographs. It is designed as a production-grade system, incorporating multiple
modeling approaches, advanced data processing, and a deployable API.

The module is structured to support a multi-faceted approach to yield estimation,
recognizing that no single method is universally optimal. It includes methodologies
for:
1.  **Object Detection-based Counting**: For crops where yield is determined by the
    number of countable items (e.g., fruits, vegetables, grains).
2.  **Segmentation-based Area Analysis**: For crops where yield correlates with
    canopy cover or biomass (e.g., leafy greens, forage crops).
3.  **Direct Regression**: For scenarios where a holistic view of the crop stand
    can directly predict yield, often incorporating multi-modal data.

Key Sub-packages:
-----------------
-   `api/`: A RESTful API built with FastAPI for serving model predictions and
    managing estimation tasks.
-   `data/`: Data loading, augmentation, and dataset management classes. Handles
    complex multi-modal and time-series data.
-   `models/`: Contains the implementations of various deep learning architectures
    for detection, segmentation, and regression.
-   `processing/`: Advanced pre-processing and feature extraction pipelines,
    including vegetation indices, texture analysis, and sensor fusion.
-   `utils/`: Common utilities for configuration, logging, and geospatial calculations.
-   `visualization/`: Tools for creating heatmaps, plotting results, and visualizing
    model outputs.
-   `tests/`: A comprehensive suite of unit and integration tests to ensure code
    quality and reliability.

This comprehensive structure ensures modularity, scalability, and maintainability,
allowing for future expansion and integration of new models and data sources.
"""

# This file makes the `yield_estimation` directory a Python package.

__version__ = "1.0.0"
__author__ = "AgroPulse AI Team"

# Log that the package is being initialized
import logging
logging.getLogger(__name__).info("AgroPulse Yield Estimation package initialized.")
