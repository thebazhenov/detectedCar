import requests

response = requests.post(
    "http://localhost:8081/nomer",
    files={"file": ("test.jpg", open("data/test.jpg", "rb"), "image/jpg")}
)

assert response.status_code == 200, response.json()
print(response.json())