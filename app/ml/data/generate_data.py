import pandas as pd
import numpy as np
import os

def generate_synthetic_data(num_rows=30000, file_path='raw_data.csv'):
    """
    Generates a large, complex, and realistic synthetic dataset for crop recommendation.
    The dataset includes soil sensor data, weather data, and historical crop success.
    """
    print(f"Generating {num_rows} rows of synthetic data...")

    # Define crops and their ideal conditions
    crops = {
        'wheat': {'n_min': 80, 'n_max': 120, 'p_min': 40, 'p_max': 60, 'k_min': 40, 'k_max': 60, 'temp_min': 10, 'temp_max': 25, 'ph_min': 6.0, 'ph_max': 7.5},
        'maize': {'n_min': 100, 'n_max': 140, 'p_min': 50, 'p_max': 70, 'k_min': 50, 'k_max': 70, 'temp_min': 20, 'temp_max': 32, 'ph_min': 6.5, 'ph_max': 7.5},
        'rice': {'n_min': 70, 'n_max': 100, 'p_min': 45, 'p_max': 65, 'k_min': 45, 'k_max': 65, 'temp_min': 20, 'temp_max': 37, 'ph_min': 5.5, 'ph_max': 7.0},
        'soybean': {'n_min': 20, 'n_max': 40, 'p_min': 60, 'p_max': 80, 'k_min': 80, 'k_max': 100, 'temp_min': 25, 'temp_max': 35, 'ph_min': 6.0, 'ph_max': 7.0},
        'cotton': {'n_min': 120, 'n_max': 150, 'p_min': 50, 'p_max': 70, 'k_min': 50, 'k_max': 70, 'temp_min': 21, 'temp_max': 36, 'ph_min': 5.8, 'ph_max': 8.0},
        'sugarcane': {'n_min': 150, 'n_max': 200, 'p_min': 60, 'p_max': 80, 'k_min': 100, 'k_max': 120, 'temp_min': 20, 'temp_max': 35, 'ph_min': 6.5, 'ph_max': 7.5},
        'potato': {'n_min': 100, 'n_max': 150, 'p_min': 80, 'p_max': 120, 'k_min': 150, 'k_max': 200, 'temp_min': 15, 'temp_max': 20, 'ph_min': 5.0, 'ph_max': 6.5},
    }
    
    data = []
    crop_names = list(crops.keys())

    for _ in range(num_rows):
        # Choose a crop to base the data on, with some randomness
        crop_name = np.random.choice(crop_names)
        conditions = crops[crop_name]

        # Generate data points around the ideal conditions for the chosen crop
        n = np.random.normal(loc=(conditions['n_min'] + conditions['n_max']) / 2, scale=20)
        p = np.random.normal(loc=(conditions['p_min'] + conditions['p_max']) / 2, scale=15)
        k = np.random.normal(loc=(conditions['k_min'] + conditions['k_max']) / 2, scale=15)
        temperature = np.random.normal(loc=(conditions['temp_min'] + conditions['temp_max']) / 2, scale=5)
        humidity = np.random.uniform(30, 90)
        ph = np.random.normal(loc=(conditions['ph_min'] + conditions['ph_max']) / 2, scale=0.5)
        rainfall = np.random.uniform(20, 300)
        soil_moisture = np.random.uniform(20, 80)
        
        # Add some noise and outliers
        if np.random.rand() < 0.1:
            n += np.random.uniform(-50, 50)
            p += np.random.uniform(-30, 30)
            k += np.random.uniform(-30, 30)
            temperature += np.random.uniform(-10, 10)
            ph += np.random.uniform(-1, 1)

        # Clip values to be within a reasonable range
        n = np.clip(n, 0, 250)
        p = np.clip(p, 0, 150)
        k = np.clip(k, 0, 250)
        temperature = np.clip(temperature, -5, 50)
        ph = np.clip(ph, 3, 10)

        data.append([n, p, k, temperature, humidity, ph, rainfall, soil_moisture, crop_name])

    df = pd.DataFrame(data, columns=['nitrogen', 'phosphorus', 'potassium', 'temperature', 'humidity', 'ph', 'rainfall', 'soil_moisture', 'crop'])
    
    # Introduce some missing values
    for col in df.columns[:-1]:
        df.loc[df.sample(frac=0.05).index, col] = np.nan

    # Save to CSV
    output_path = os.path.join(os.path.dirname(__file__), file_path)
    df.to_csv(output_path, index=False)
    print(f"Successfully generated and saved data to {output_path}")

if __name__ == '__main__':
    generate_synthetic_data()
