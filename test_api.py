"""
Quick test script for AgroPulse API
Run this after starting the server to verify everything works
"""

import requests
import json
from time import sleep

BASE_URL = "http://localhost:8000"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def test_endpoint(name, method, url, headers=None, data=None, expected_status=200):
    """Test an API endpoint"""
    print(f"\n{Colors.BLUE}Testing: {name}{Colors.END}")
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data)
        elif method == "PATCH":
            response = requests.patch(url, headers=headers, json=data)
        
        if response.status_code == expected_status:
            print(f"{Colors.GREEN}✓ Success - Status: {response.status_code}{Colors.END}")
            return response.json()
        else:
            print(f"{Colors.RED}✗ Failed - Status: {response.status_code}{Colors.END}")
            print(f"Response: {response.text}")
            return None
    
    except Exception as e:
        print(f"{Colors.RED}✗ Error: {str(e)}{Colors.END}")
        return None

def main():
    print(f"{Colors.YELLOW}{'='*60}")
    print("  AgroPulse API Test Suite")
    print(f"{'='*60}{Colors.END}\n")
    
    # Test 1: Health Check
    print(f"\n{Colors.YELLOW}=== Basic Tests ==={Colors.END}")
    health = test_endpoint(
        "Health Check",
        "GET",
        f"{BASE_URL}/health"
    )
    
    if not health:
        print(f"\n{Colors.RED}Server is not running! Start it with: uvicorn main:app --reload{Colors.END}")
        return
    
    # Test 2: System Info
    test_endpoint(
        "System Info",
        "GET",
        f"{BASE_URL}/api/v1/info"
    )
    
    # Test 3: Register User
    print(f"\n{Colors.YELLOW}=== Authentication Tests ==={Colors.END}")
    user_data = {
        "phone_number": "254712345678",
        "email": "test@agropulse.com",
        "full_name": "Test Farmer",
        "password": "password123"
    }
    
    register_response = test_endpoint(
        "Register User",
        "POST",
        f"{BASE_URL}/api/v1/auth/register",
        data=user_data,
        expected_status=201
    )
    
    if not register_response:
        print(f"{Colors.YELLOW}Note: User might already exist, trying login...{Colors.END}")
        
        # Try login instead
        login_response = test_endpoint(
            "Login User",
            "POST",
            f"{BASE_URL}/api/v1/auth/login",
            data={
                "phone_number": user_data["phone_number"],
                "password": user_data["password"]
            }
        )
        
        if not login_response:
            print(f"{Colors.RED}Cannot proceed without authentication!{Colors.END}")
            return
        
        access_token = login_response.get("access_token")
    else:
        access_token = register_response.get("access_token")
    
    print(f"{Colors.GREEN}✓ Got access token{Colors.END}")
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    # Test 4: Get Current User
    test_endpoint(
        "Get Current User",
        "GET",
        f"{BASE_URL}/api/v1/auth/me",
        headers=headers
    )
    
    # Test 5: Create Farm
    print(f"\n{Colors.YELLOW}=== Farm Management Tests ==={Colors.END}")
    farm_data = {
        "name": "Test Farm",
        "location": "Kiambu County",
        "latitude": -1.1743,
        "longitude": 36.8857,
        "size_acres": 5.5,
        "crop_type": "Maize"
    }
    
    farm_response = test_endpoint(
        "Create Farm",
        "POST",
        f"{BASE_URL}/api/v1/auth/farms",
        headers=headers,
        data=farm_data,
        expected_status=201
    )
    
    if not farm_response:
        # Get existing farms
        farms_response = test_endpoint(
            "Get Farms",
            "GET",
            f"{BASE_URL}/api/v1/auth/farms",
            headers=headers
        )
        if farms_response and len(farms_response) > 0:
            farm_id = farms_response[0]["id"]
            print(f"{Colors.GREEN}Using existing farm ID: {farm_id}{Colors.END}")
        else:
            print(f"{Colors.RED}Cannot proceed without farm!{Colors.END}")
            return
    else:
        farm_id = farm_response["id"]
        print(f"{Colors.GREEN}Created farm ID: {farm_id}{Colors.END}")
    
    # Test 6: Register Sensor
    print(f"\n{Colors.YELLOW}=== Sensor Tests ==={Colors.END}")
    sensor_data = {
        "device_id": "ESP32-TEST-001",
        "sensor_type": "esp32_cam",
        "name": "Test Sensor",
        "location": "North Field",
        "latitude": -1.1743,
        "longitude": 36.8857
    }
    
    sensor_response = test_endpoint(
        "Register Sensor",
        "POST",
        f"{BASE_URL}/api/v1/sensors?farm_id={farm_id}",
        headers=headers,
        data=sensor_data,
        expected_status=201
    )
    
    if sensor_response:
        sensor_api_key = sensor_response["api_key"]
        print(f"{Colors.GREEN}Sensor API Key: {sensor_api_key[:20]}...{Colors.END}")
        
        # Test 7: Create Alert
        sensor_headers = {
            "X-API-Key": sensor_api_key,
            "Content-Type": "application/json"
        }
        
        alert_data = {
            "farm_id": farm_id,
            "alert_type": "yellow_spot_detected",
            "severity": "medium",
            "description": "Test alert from automated test",
            "confidence_score": 0.75,
            "latitude": -1.1743,
            "longitude": 36.8857
        }
        
        alert_response = test_endpoint(
            "Create Alert (as Sensor)",
            "POST",
            f"{BASE_URL}/api/v1/sensors/alerts",
            headers=sensor_headers,
            data=alert_data,
            expected_status=201
        )
        
        # Test 8: Get Alerts
        test_endpoint(
            "Get Farm Alerts",
            "GET",
            f"{BASE_URL}/api/v1/sensors/alerts?farm_id={farm_id}",
            headers=headers
        )
    
    # Test 9: Payment Initiation
    print(f"\n{Colors.YELLOW}=== Payment Tests ==={Colors.END}")
    payment_data = {
        "amount": 50,
        "payment_method": "mpesa",
        "phone_number": "254712345678",
        "description": "Test payment"
    }
    
    payment_response = test_endpoint(
        "Initiate Payment",
        "POST",
        f"{BASE_URL}/api/v1/payments/initiate",
        headers=headers,
        data=payment_data,
        expected_status=201
    )
    
    # Test 10: Get Permits
    test_endpoint(
        "Get User Permits",
        "GET",
        f"{BASE_URL}/api/v1/payments/permits",
        headers=headers
    )
    
    # Summary
    print(f"\n{Colors.YELLOW}{'='*60}")
    print("  Test Suite Complete!")
    print(f"{'='*60}{Colors.END}\n")
    
    print(f"{Colors.BLUE}Next Steps:{Colors.END}")
    print("1. Visit http://localhost:8000/docs for interactive API testing")
    print("2. Configure AWS, Blockchain, and Payment services in .env")
    print("3. Test with real ESP32-CAM sensor")
    print("4. Try the mobile app integration")
    print(f"\n{Colors.GREEN}Happy Testing! 🌾{Colors.END}\n")

if __name__ == "__main__":
    main()
