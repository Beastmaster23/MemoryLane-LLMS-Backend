import requests

id = 'test'
data = {'key': 'value'}
r = requests.get('http://localhost:9000/prompt')
print(f'Status code: {r.status_code} and text: {r.text}')