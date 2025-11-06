"""
API Endpoints for Yield Estimation
==================================

This module defines the FastAPI routes for the yield estimation service. It
creates the `/predict` endpoint, which serves as the main entry point for all
prediction tasks.

The design is centered around a single, powerful endpoint that can handle
different model types, making the API clean and easy to use.

Core Components:
----------------
1.  **FastAPI Router**:
    -   An `APIRouter` instance is created to organize the prediction-related
      routes. This allows for modular API design and can be easily included in
      the main FastAPI application.

2.  **`/predict` Endpoint**:
    -   **HTTP Method**: `POST`.
    -   **Purpose**: To receive an image and model information, run inference,
      and return the results.
    -   **Request Body**: The endpoint expects a JSON payload that conforms to the
      `PredictionRequest` schema defined in `api.schemas`. This includes the
      Base64-encoded image and the path to the model.
    -   **Response Body**: It returns a `PredictionResponse` object, which will
      contain the results tailored to the specific task (detection, segmentation,
      or regression).

3.  **Prediction Logic**:
    -   **Image Decoding**: The Base64 image string is decoded back into a binary
      format and then read into a NumPy array using OpenCV.
    -   **Model Loading**: A `YieldPredictor` instance is created using the
      `model_path` provided in the request. To optimize performance, predictors
      are cached in memory in a dictionary. If a predictor for a given model
      path has already been loaded, it's reused, avoiding the overhead of
      re-loading the model from disk on every request.
    -   **Inference**: The `predictor.predict()` method is called to get the
      model's predictions.
    -   **Response Formatting**: The raw predictions are formatted into the
      appropriate Pydantic response model (`DetectionResult`, `SegmentationResult`,
      etc.) before being sent back to the client.
    -   **Error Handling**: A `try...except` block wraps the entire process to
      catch any exceptions during prediction and return a clean error message
      in the `PredictionResponse`.

4.  **Caching**:
    -   A simple in-memory dictionary (`predictor_cache`) is used to store
      instances of `YieldPredictor`. This is a form of memoization that
      significantly speeds up consecutive requests that use the same model, as
      it avoids costly disk I/O and model initialization.

This endpoint provides a robust and efficient way to serve the yield estimation
models over a network.
"""

from fastapi import APIRouter, HTTPException, Body
from starlette.responses import JSONResponse
import base64
import numpy as np
import cv2
import uuid
import logging

from app.computer_vision.yield_estimation.prediction import YieldPredictor
from app.computer_vision.yield_estimation.api.schemas import (
    PredictionRequest, PredictionResponse, DetectionResult, 
    SegmentationResult, RegressionResult
)

router = APIRouter()
logger = logging.getLogger(__name__)

# In-memory cache for predictors to avoid reloading models on every request
predictor_cache = {}

@router.post("/predict", response_model=PredictionResponse)
async def predict(request: PredictionRequest = Body(...)):
    """
    Run yield estimation prediction on an input image.
    """
    request_id = str(uuid.uuid4())
    logger.info(f"Received prediction request {request_id} for model {request.model_path}")

    try:
        # --- 1. Decode Image ---
        try:
            img_bytes = base64.b64decode(request.image_base64)
            img_np = np.frombuffer(img_bytes, np.uint8)
            image = cv2.imdecode(img_np, cv2.IMREAD_COLOR)
            if image is None:
                raise ValueError("Failed to decode image. Check Base64 string and image format.")
        except Exception as e:
            logger.error(f"Request {request_id}: Image decoding failed. {e}")
            raise HTTPException(status_code=400, detail=f"Invalid image data: {e}")

        # --- 2. Load Predictor (with caching) ---
        model_path = request.model_path
        if model_path not in predictor_cache:
            logger.info(f"Request {request_id}: Creating new predictor for model '{model_path}'")
            try:
                predictor_cache[model_path] = YieldPredictor(model_path=model_path)
            except Exception as e:
                logger.error(f"Request {request_id}: Failed to load model '{model_path}'. {e}")
                raise HTTPException(status_code=500, detail=f"Could not load model: {e}")
        
        predictor = predictor_cache[model_path]

        # --- 3. Run Prediction ---
        predictions = predictor.predict(image, threshold=request.threshold)
        
        # --- 4. Format Response ---
        task = predictor.task
        results = None
        if task == 'detection':
            results = [
                DetectionResult(box=box.tolist(), label=int(label), score=float(score))
                for box, label, score in zip(predictions['boxes'], predictions['labels'], predictions['scores'])
            ]
        elif task == 'segmentation':
            mask = predictions['mask'].astype(np.uint8)
            _, buffer = cv2.imencode('.png', mask)
            mask_base64 = base64.b64encode(buffer).decode('utf-8')
            results = SegmentationResult(mask_shape=mask.shape, mask_base64=mask_base64)
        elif task == 'regression':
            results = RegressionResult(yield_value=predictions['yield'])

        logger.info(f"Request {request_id}: Prediction successful.")
        return PredictionResponse(task=task, request_id=request_id, results=results)

    except HTTPException as http_exc:
        # Re-raise HTTP exceptions to let FastAPI handle them
        raise http_exc
    except Exception as e:
        logger.error(f"Request {request_id}: An unexpected error occurred: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content=PredictionResponse(
                task="unknown",
                request_id=request_id,
                error=f"An internal error occurred: {e}"
            ).dict()
        )
