"""
API Schemas for Yield Estimation
================================

This module defines the Pydantic data models used for API request and response
validation. Using Pydantic ensures that the data flowing into and out of the
API is well-structured and type-safe, which is crucial for a robust service.

These schemas serve as the public contract for the API, clearly defining what
data clients should send and what they can expect in return.

Core Schemas:
-------------
1.  **`PredictionRequest`**:
    -   **Purpose**: To validate the incoming data for a prediction request.
    -   **Fields**:
        -   `image_base64`: A Base64-encoded string representing the image. This
          is a common way to transmit binary data like images in JSON payloads.
        -   `model_path`: The path to the trained model checkpoint file to be
          used for this prediction. This allows clients to specify which model
          to use on-the-fly.
        -   `threshold`: An optional confidence threshold for filtering results,
          primarily used for detection tasks.

2.  **`DetectionResult`**:
    -   **Purpose**: To structure a single detected object's information.
    -   **Fields**:
        -   `box`: A list of four numbers representing the bounding box `[xmin, ymin, xmax, ymax]`.
        -   `label`: The integer class ID of the detected object.
        -   `score`: The confidence score of the detection.

3.  **`SegmentationResult`**:
    -   **Purpose**: To structure the result of a segmentation prediction.
    -   **Fields**:
        -   `mask_shape`: The dimensions of the output mask.
        -   `mask_base64`: A Base64-encoded string of the predicted segmentation
          mask (e.g., saved as a PNG).

4.  **`RegressionResult`**:
    -   **Purpose**: To structure the result of a regression prediction.
    -   **Fields**:
        -   `yield_value`: The predicted continuous value.

5.  **`PredictionResponse`**:
    -   **Purpose**: A flexible response model that can accommodate the results
      from any of the three task types.
    -   **Fields**:
        -   `task`: A string indicating the type of prediction performed
          ('detection', 'segmentation', 'regression').
        -   `request_id`: A unique identifier for tracking the request.
        -   `results`: A union of the possible result types. Depending on the
          `task` field, this will contain a list of `DetectionResult`, a
          `SegmentationResult`, or a `RegressionResult`.
        -   `error`: An optional field to return an error message if the
          prediction fails.

These schemas are used by FastAPI to automatically handle request validation,
data conversion, and documentation generation (in OpenAPI/Swagger UI).
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Union, Tuple

class PredictionRequest(BaseModel):
    """
    Request model for making a prediction.
    """
    image_base64: str = Field(..., description="Base64 encoded string of the input image.")
    model_path: str = Field(..., description="Path to the trained model checkpoint (.pth).")
    threshold: Optional[float] = Field(0.5, description="Confidence threshold for detection tasks.")

class DetectionResult(BaseModel):
    """
    Represents a single detected object.
    """
    box: List[float] = Field(..., description="Bounding box coordinates [xmin, ymin, xmax, ymax].")
    label: int = Field(..., description="Class label index.")
    score: float = Field(..., description="Confidence score of the detection.")

class SegmentationResult(BaseModel):
    """
    Represents the output of a segmentation task.
    The mask is encoded to be sent over JSON.
    """
    mask_shape: Tuple[int, int]
    mask_base64: str = Field(..., description="Base64 encoded string of the predicted mask (e.g., PNG).")

class RegressionResult(BaseModel):
    """
    Represents the output of a regression task.
    """
    yield_value: float = Field(..., description="Predicted yield value.")

class PredictionResponse(BaseModel):
    """
    Response model for a prediction request.
    """
    task: str = Field(..., description="The task performed (detection, segmentation, regression).")
    request_id: str = Field(..., description="Unique identifier for the request.")
    results: Optional[Union[List[DetectionResult], SegmentationResult, RegressionResult]] = None
    error: Optional[str] = None
