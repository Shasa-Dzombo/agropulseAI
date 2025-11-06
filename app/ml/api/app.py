from flask import Flask, request, jsonify
from app.ml.models.predict_model import predict_crop
import traceback

app = Flask(__name__)

@app.route('/predict', methods=['POST'])
def predict():
    """
    API endpoint to get a crop recommendation.
    Expects a JSON payload with sensor data.
    """
    try:
        data = request.get_json()
        
        # Basic validation
        required_keys = ['nitrogen', 'phosphorus', 'potassium', 'temperature', 'humidity', 'ph', 'rainfall', 'soil_moisture']
        if not all(key in data for key in required_keys):
            return jsonify({'error': 'Missing required input features.'}), 400

        # Get prediction
        recommendation = predict_crop(data)
        
        return jsonify({'recommended_crop': recommendation})

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': 'An error occurred during prediction.'}), 500

if __name__ == '__main__':
    # To run this API:
    # 1. Make sure you have Flask installed: pip install Flask
    # 2. From the root directory of AgroPulse, run: python -m app.ml.api.app
    app.run(debug=True, port=5001)
