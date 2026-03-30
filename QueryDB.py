import requests

response = requests.post(
    'https://python-console-production.up.railway.app/query',
    json={'sql': "SELECT * FROM pg_tables WHERE schemaname = 'public'"}
)
print(response.json())