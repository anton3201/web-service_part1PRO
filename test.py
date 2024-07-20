import requests

payload={"text":"Расскажи про субекты страхования? "}
response = requests.post("http://127.0.0.1:5000/api/get_answer", json=payload)
print(response.text)

response = requests.get("http://127.0.0.1:5000/count")
print(response.text)