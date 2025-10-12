import sys
import requests

pr_url = sys.argv[1]
API_URL = "http://127.0.0.1:8000/analyze-pr"

response = requests.get(API_URL, params={"pr_url": pr_url})
data = response.json()

print("=== PR Analysis Result ===")
print(data)
