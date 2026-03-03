import qrcode
import base64
import requests
from io import BytesIO

data = "Test qr"
qr = qrcode.make(data)

qr.save("qr.png")

buffer = BytesIO()
qr.save(buffer, format="PNG")
img_bytes = buffer.getvalue()
img_base64 = base64.b64encode(img_bytes).decode("utf-8")

url = "http://127.0.0.1:5000/"

payload = {
    "photo": img_base64
}

response = requests.post(url, json=payload)

print("Status code:", response.status_code)
print("Response:", response.text)