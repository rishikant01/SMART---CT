# save_all_lessons.py
import json
import requests

# Your 50 lessons data
with open('lessons_data.json', 'r') as f:
    lessons_data = json.load(f)

response = requests.post(
    'http://localhost:5000/api/admin/lessons/bulk',
    headers={
        'Content-Type': 'application/json',
        'X-Admin-Key': 'setu-admin-2026'
    },
    json=lessons_data
)

print(f"Status: {response.status_code}")
print(response.json())
