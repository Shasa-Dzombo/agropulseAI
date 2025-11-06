"""
Integration Tests for the API Endpoints
=======================================

This module contains integration tests for the FastAPI endpoints defined in
`api/endpoints.py`. It uses FastAPI's `TestClient` to send HTTP requests
directly to the application in memory, allowing for fast and realistic testing
of the API layer without needing a running server.

These tests verify the end-to-end flow of a prediction request, from receiving
the HTTP request to returning a JSON response.

Core Components:
----------------
1.  **`TestClient` Fixture**:
    -   **Purpose**: To provide a client for making requests to the FastAPI app.
    -   **Setup**:
        -   Imports the `app` instance from `api.main`.
        -   Creates a `TestClient` instance with this app.

2.  **Mocking `YieldPredictor`**:
    -   The `YieldPredictor` class is the core dependency of the `/predict`
      endpoint. To isolate the API logic from the actual model inference
      (which can be slow and complex), `YieldPredictor` is mocked using
      `unittest.mock.patch`.
    -   The mock predictor is configured to return predefined prediction
      dictionaries, simulating the output of a real model for each task type.
    -   This allows the tests to focus on verifying the API's behavior: request
      validation, data encoding/decoding, response formatting, and error handling.

3.  **`test_predict_endpoint` (Parameterized)**:
    -   **Purpose**: To test the `/predict` endpoint for all supported task types.
    -   **`pytest.mark.parametrize`**: This decorator runs the same test function
      multiple times with different inputs, once for each task ('detection',
      'segmentation', 'regression').
    -   **Execution for each task**:
        -   Creates a dummy image and encodes it to Base64.
        -   Constructs a request payload with the image and a mock model path.
        -   Configures the mock `YieldPredictor` to return the expected output
          for the current task.
        -   Sends a `POST` request to `/yield-estimation/predict`.
        -   **Asserts that the response status code is 200 (OK)**.
        -   Parses the JSON response.
        -   **Asserts that the response structure matches the `PredictionResponse`
          schema** and contains the correct data for the task (e.g., a list of
          `DetectionResult` for detection).

4.  **Error Handling Tests**:
    -   `test_predict_bad_image_data`: Sends a request with invalid Base64 data
      and asserts that the API returns a `400 Bad Request` status code.
    -   `test_predict_model_load_failure`: Configures the mock `YieldPredictor`
      to raise an exception during initialization and asserts that the API
      returns a `500 Internal Server Error`.

These tests ensure that the API is robust, handles different scenarios gracefully,
and adheres to its defined contract.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import base64
import numpy as np
import cv2

# The TestClient needs to import the app from the main api file
from app.computer_vision.yield_estimation.api.main import app

@pytest.fixture(scope="module")
def client():
    """Create a TestClient instance for the FastAPI app."""
    with TestClient(app) as c:
        yield c

@pytest.fixture
def mock_predictor():
    """Mocks the YieldPredictor class."""
    # This mock will replace the actual YieldPredictor in the endpoints module
    with patch('app.computer_vision.yield_estimation.api.endpoints.YieldPredictor') as mock:
        # Create an instance of the mock to be returned by the constructor
        predictor_instance = MagicMock()
        mock.return_value = predictor_instance
        yield predictor_instance

def get_base64_image():
    """Creates a dummy image and returns its base64 representation."""
    dummy_image = np.zeros((100, 100, 3), dtype=np.uint8)
    _, buffer = cv2.imencode('.jpg', dummy_image)
    return base64.b64encode(buffer).decode('utf-8')

@pytest.mark.parametrize("task, mock_output, expected_key", [
    (
        "detection", 
        {'boxes': np.array([[10, 10, 20, 20]]), 'labels': np.array([1]), 'scores': np.array([0.9])},
        'box'
    ),
    (
        "segmentation",
        {'mask': np.zeros((10, 10), dtype=np.uint8)},
        'mask_base64'
    ),
    (
        "regression",
        {'yield': 55.5},
        'yield_value'
    )
])
def test_predict_endpoint(client, mock_predictor, task, mock_output, expected_key):
    """Test the /predict endpoint for all task types."""
    # Configure the mock predictor instance for the current test case
    mock_predictor.task = task
    mock_predictor.predict.return_value = mock_output

    # Prepare request data
    image_b64 = get_base64_image()
    request_data = {
        "image_base64": image_b64,
        "model_path": f"fake/path/to/{task}_model.pth",
        "threshold": 0.5
    }

    # Make the request
    response = client.post("/yield-estimation/predict", json=request_data)

    # Assertions
    assert response.status_code == 200
    data = response.json()
    assert data['task'] == task
    assert data['error'] is None
    assert 'results' in data

    # Check if results are structured correctly
    results = data['results']
    if task == 'detection':
        assert isinstance(results, list)
        assert expected_key in results[0]
    else:
        assert isinstance(results, dict)
        assert expected_key in results

def test_predict_bad_image_data(client):
    """Test the endpoint with invalid base64 image data."""
    request_data = {
        "image_base64": "this is not a valid base64 string",
        "model_path": "fake/path/model.pth"
    }
    response = client.post("/yield-estimation/predict", json=request_data)
    assert response.status_code == 400
    assert "Invalid image data" in response.json()['detail']

@patch('app.computer_vision.yield_estimation.api.endpoints.YieldPredictor', side_effect=Exception("Model file not found"))
def test_predict_model_load_failure(mock_predictor_class, client):
    """Test the endpoint when the model fails to load."""
    request_data = {
        "image_base64": get_base64_image(),
        "model_path": "non/existent/model.pth"
    }
    response = client.post("/yield-estimation/predict", json=request_data)
    assert response.status_code == 500
    assert "Could not load model" in response.json()['detail']
