"""
Loads nvr_system/disease_detection/kindwise_api_client.py by file path,
bypassing nvr_system.disease_detection's package __init__.py - that
__init__ imports three detector modules (powdery_mildew_detector,
botrytis_detector, downy_mildew_detector) that don't exist anywhere in the
directory, so a normal `from nvr_system.disease_detection.kindwise_api_client
import ...` always fails (Python runs a package's __init__ on first import of
any of its submodules). kindwise_api_client.py itself has no relative/package
imports (only requests/numpy/cv2/stdlib), so loading it standalone is safe.

This is a reuse workaround, not a fix - nvr_system/disease_detection/ is a
separate, unrelated prototype and stays untouched.
"""

import importlib.util
import sys
from pathlib import Path

_MODULE_NAME = "_kindwise_api_client_standalone"
_CLIENT_PATH = (
    Path(__file__).resolve().parents[2] / "nvr_system" / "disease_detection" / "kindwise_api_client.py"
)


def _load() -> "object":
    if _MODULE_NAME in sys.modules:
        return sys.modules[_MODULE_NAME]

    spec = importlib.util.spec_from_file_location(_MODULE_NAME, _CLIENT_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[_MODULE_NAME] = module
    spec.loader.exec_module(module)
    return module


_kindwise = _load()

KindwiseAPIClient = _kindwise.KindwiseAPIClient
KindwiseAPIResponse = _kindwise.KindwiseAPIResponse
DiseaseIdentification = _kindwise.DiseaseIdentification
DiseaseSeverity = _kindwise.DiseaseSeverity
CropType = _kindwise.CropType
EPPOCode = _kindwise.EPPOCode
TreatmentRecommendation = _kindwise.TreatmentRecommendation
