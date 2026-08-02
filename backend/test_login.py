import requests
import json

url = "http://backend:8000/api/v1/auth/login"
data = {
    "username": "admin",
    "password": "admin123"
}

response = requests.post(url, json=data)
print(f"Status: {response.status_code}")
print(f"Response: {response.text}")
