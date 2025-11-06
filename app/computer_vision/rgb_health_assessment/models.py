# c:\Users\Codeternal\Desktop\AgroPulse\app\computer_vision\rgb_health_assessment\models.py

"""
Machine Learning Models for RGB-Based Health Assessment
=======================================================

This module defines the machine learning models used to predict crop health
status from the feature vectors extracted by the `preprocessing` module.
Since the features are tabular (a flat vector of numbers), this module
focuses on classical machine learning models that are well-suited for such
structured data.

The primary component is the `RGBHealthModelFactory`, which provides a
standardized way to create, configure, and use different types of classifiers.
This approach allows for easy experimentation with various algorithms without
changing the core training or prediction pipelines.

Key Components:
---------------
1.  **`RGBHealthModelFactory`**:
    -   **Purpose**: A factory class that builds and returns an instance of a
      scikit-learn compatible classifier based on a configuration dictionary.
    -   **Flexibility**: It supports a range of powerful classifiers, making it
      easy to switch between them.
    -   **Configuration**: The factory takes a `model_params` dictionary that
      specifies the `type` of model and a `params` sub-dictionary containing
      the hyperparameters for the chosen model's constructor.

Supported Model Types:
----------------------
-   **`RandomForest`**: An ensemble of decision trees. Robust, good performance
    out-of-the-box, and provides feature importance scores.
-   **`GradientBoosting`**: An ensemble method that builds trees sequentially,
    with each tree correcting the errors of the previous one. Often provides
    state-of-the-art performance on tabular data.
-   **`SVC` (Support Vector Classifier)**: A powerful model that finds an optimal
    hyperplane to separate classes. Effective in high-dimensional spaces.
-   **`MLP` (Multi-layer Perceptron)**: A simple neural network classifier. Can
    capture complex non-linear relationships between features.
-   **`LogisticRegression`**: A robust and interpretable linear model, useful as
    a baseline for performance comparison.
-   **`XGBoost`**: An optimized and highly efficient implementation of gradient
    boosting. Often a top choice in machine learning competitions for its speed
    and accuracy. Requires the `xgboost` library to be installed.

Usage:
------
The factory is typically used within the training pipeline. A configuration
like the one below would create a `RandomForestClassifier` with 150 trees.

```json
{
  "model_params": {
    "type": "RandomForest",
    "params": {
      "n_estimators": 150,
      "max_depth": 20,
      "random_state": 42
    }
  }
}
```

This modular design separates the model definition from the rest of the application,
promoting clean architecture and ease of maintenance.
"""

import logging
from typing import Dict, Any, Union

# Import classifiers from scikit-learn
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.svm import SVC
from sklearn.neural_network import MLPClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.base import ClassifierMixin

# Attempt to import XGBoost, which is an optional dependency
try:
    from xgboost import XGBClassifier
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    XGBClassifier = None # Define it as None if not available

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# A type hint for any of the supported scikit-learn style classifiers
SupportedClassifiers = Union[
    RandomForestClassifier,
    GradientBoostingClassifier,
    SVC,
    MLPClassifier,
    LogisticRegression,
    XGBClassifier
]

class RGBHealthModelFactory:
    """
    A factory for creating machine learning models for RGB-based health assessment.
    """

    @staticmethod
    def create_model(model_config: Dict[str, Any]) -> ClassifierMixin:
        """
        Creates a scikit-learn compatible classifier based on the provided configuration.

        Args:
            model_config (Dict[str, Any]): A dictionary containing the model
                configuration. It must have a 'type' key specifying the model
                and an optional 'params' key for hyperparameters.
                Example:
                {
                    'type': 'RandomForest',
                    'params': {'n_estimators': 100, 'random_state': 42}
                }

        Returns:
            ClassifierMixin: An instance of a scikit-learn classifier.

        Raises:
            ValueError: If the model type is unknown or a required library
                        (like xgboost) is not installed.
        """
        model_type = model_config.get('type')
        if not model_type:
            raise ValueError("Model configuration must include a 'type' key.")

        model_params = model_config.get('params', {})
        model_type_lower = model_type.lower()
        
        logging.info(f"Creating model of type '{model_type}' with params: {model_params}")

        if model_type_lower == 'randomforest':
            return RandomForestClassifier(**model_params)
        
        elif model_type_lower == 'gradientboosting':
            return GradientBoostingClassifier(**model_params)
            
        elif model_type_lower == 'svc':
            # Ensure probability=True if we need predict_proba later
            if 'probability' not in model_params:
                model_params['probability'] = True
            return SVC(**model_params)
            
        elif model_type_lower == 'mlp':
            return MLPClassifier(**model_params)
            
        elif model_type_lower == 'logisticregression':
            return LogisticRegression(**model_params)
            
        elif model_type_lower == 'xgboost':
            if not XGBOOST_AVAILABLE:
                raise ValueError("XGBoost model type requested, but the 'xgboost' library is not installed. "
                                 "Please install it using: pip install xgboost")
            # XGBoost has a different parameter for random seed
            if 'random_state' in model_params:
                model_params['seed'] = model_params.pop('random_state')
            return XGBClassifier(**model_params)
            
        else:
            supported = ['RandomForest', 'GradientBoosting', 'SVC', 'MLP', 'LogisticRegression']
            if XGBOOST_AVAILABLE:
                supported.append('XGBoost')
            raise ValueError(f"Unknown model type '{model_type}'. Supported types are: {supported}")

# --- Example Usage ---
if __name__ == '__main__':
    print("--- RGB Health Model Factory Demo ---")

    # 1. Define configurations for different models
    configs = {
        "Random Forest": {
            "type": "RandomForest",
            "params": {"n_estimators": 50, "random_state": 42}
        },
        "Gradient Boosting": {
            "type": "GradientBoosting",
            "params": {"n_estimators": 50, "learning_rate": 0.1, "random_state": 42}
        },
        "Support Vector Machine": {
            "type": "SVC",
            "params": {"C": 1.0, "kernel": "rbf", "random_state": 42}
        },
        "MLP": {
            "type": "MLP",
            "params": {"hidden_layer_sizes": (100, 50), "max_iter": 300, "random_state": 42}
        }
    }
    
    if XGBOOST_AVAILABLE:
        configs["XGBoost"] = {
            "type": "XGBoost",
            "params": {"n_estimators": 50, "learning_rate": 0.1, "random_state": 42}
        }
    else:
        print("\nNOTE: XGBoost library not found. Skipping XGBoost demo.")
        print("To enable it, run: pip install xgboost")

    # 2. Create instances of each model using the factory
    for name, config in configs.items():
        print(f"\n--- Creating {name} ---")
        try:
            model = RGBHealthModelFactory.create_model(config)
            print(f"Successfully created model instance:")
            print(model)
            # Verify that the parameters were set correctly
            if name == "Random Forest":
                assert model.n_estimators == 50
            if name == "Support Vector Machine":
                # Check that probability was automatically enabled
                assert model.probability is True
        except (ValueError, TypeError) as e:
            print(f"Failed to create model: {e}")

    # 3. Demonstrate error handling for an unknown model type
    print("\n--- Testing Error Handling ---")
    unknown_config = {"type": "ImaginaryNet"}
    try:
        RGBHealthModelFactory.create_model(unknown_config)
    except ValueError as e:
        print(f"Successfully caught error for unknown model type: {e}")
```