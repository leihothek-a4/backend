from flask import Flask, request, jsonify
import numpy as np
import base64
import cv2

app = Flask(__name__)

@app.route("/", methods=["POST"])
def parse_qr():
    data = request.get_json()

    if not data or "photo" not in data:
        return jsonify({"error": "No photo provided"}), 400

    img_bytes = base64.b64decode(data["photo"])
    img_as_np = np.frombuffer(img_bytes, dtype=np.uint8)
    img = cv2.imdecode(img_as_np, flags=1)

    qcd = cv2.QRCodeDetector()
    retval, decoded_info, points, _ = qcd.detectAndDecodeMulti(img)

    if retval:
        return jsonify({"decoded": decoded_info})
    else:
        return jsonify({"decoded": "Unable to parse qr code"}), 500

if __name__ == "__main__":
    app.run(debug=True)