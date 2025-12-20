"""
Check available endpoints
"""
import requests

response = requests.get("http://127.0.0.1:8000/openapi.json")
data = response.json()

print("Available endpoints:")
for path in sorted(data["paths"].keys()):
    methods = list(data["paths"][path].keys())
    print(f"  {path} [{', '.join(methods).upper()}]")
