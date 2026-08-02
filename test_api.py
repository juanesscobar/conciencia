import requests
import json

# Test desde el servidor
url = "http://localhost/api/v1/auth/login"
data = {
    "username": "admin",
    "password": "admin123"
}

response = requests.post(url, json=data)
print(f"Status: {response.status_code}")
print(f"Response: {response.text}")
