from flask import Flask, request, send_file, jsonify
from PIL import Image
import io
import uuid
import hashlib
from stegano import lsb

app = Flask(__name__)

# Dictionary to store UUID to image mapping and password hash
uuid_image_map = {}
uuid_password_map = {}

# Variable to store the most recent file UUID
latest_file_uuid = None

def hide_image_with_more_bits(cover_image, secret_image, bits=4):
    secret_image = secret_image.resize(cover_image.size)
    cover_pixels = list(cover_image.getdata())
    secret_pixels = list(secret_image.getdata())

    mask = (1 << bits) - 1  # Mask to keep the last `bits` bits

    new_pixels = []
    for cover_pixel, secret_pixel in zip(cover_pixels, secret_pixels):
        new_pixel = tuple([
            (cover_channel & ~mask) | (secret_channel >> (8 - bits))
            for cover_channel, secret_channel in zip(cover_pixel, secret_pixel)
        ])
        new_pixels.append(new_pixel)

    new_image = Image.new(cover_image.mode, cover_image.size)
    new_image.putdata(new_pixels)
    return new_image

def hide_password_in_image(image, password, bits=4):
    pixels = list(image.getdata())

    password_bin = ''.join(format(ord(c), '08b') for c in password)
    password_bin += '00000000'  # Null terminator for the password

    mask = (1 << bits) - 1  # Mask to keep the last `bits` bits

    new_pixels = []
    password_idx = 0

    for pixel in pixels:
        new_pixel = []
        for channel in pixel:
            if password_idx < len(password_bin):
                new_channel = (channel & ~mask) | int(password_bin[password_idx:password_idx+bits], 2)
                password_idx += bits
            else:
                new_channel = channel
            new_pixel.append(new_channel)
        new_pixels.append(tuple(new_pixel))

    new_image = Image.new(image.mode, image.size)
    new_image.putdata(new_pixels)
    return new_image

def extract_password_from_image(image, bits=4):
    pixels = list(image.getdata())

    password_bin = ''
    mask = (1 << bits) - 1

    for pixel in pixels:
        for channel in pixel:
            password_bin += format(channel & mask, f'0{bits}b')
            if len(password_bin) % 8 == 0 and password_bin[-8:] == '00000000':
                return ''.join(chr(int(password_bin[i:i+8], 2)) for i in range(0, len(password_bin) - 8, 8))

    return ''.join(chr(int(password_bin[i:i+8], 2)) for i in range(0, len(password_bin), 8))

@app.route('/hide_image', methods=['POST'])
def hide_image():
    cover_image_file = request.files['cover_image']
    secret_image_file = request.files['secret_image']
    password = request.form.get('password', '')

    if not password:
        return jsonify({"status": "error", "message": "Password is required"}), 400

    cover_image = Image.open(cover_image_file.stream)
    secret_image = Image.open(secret_image_file.stream)

    new_image = hide_image_with_more_bits(cover_image, secret_image, bits=4)
    new_image = hide_password_in_image(new_image, password, bits=4)

    img_io = io.BytesIO()
    new_image.save(img_io, 'PNG')
    img_io.seek(0)

    global latest_file_uuid
    file_uuid = str(uuid.uuid4())
    uuid_image_map[file_uuid] = img_io
    latest_file_uuid = file_uuid

    return jsonify({"encoded_image_url": request.url_root + 'processed'})

@app.route('/extract_image', methods=['POST'])
def extract_image():
    cover_image_file = request.files['cover_image']
    password = request.form.get('password', '')

    if not password:
        return jsonify({"status": "error", "message": "Password is required"}), 400

    cover_image = Image.open(cover_image_file.stream)

    extracted_password = extract_password_from_image(cover_image, bits=4)
    if extracted_password != password:
        return jsonify({"status": "error", "message": "Invalid password"}), 401

    cover_pixels = list(cover_image.getdata())

    extracted_pixels = []
    for cover_pixel in cover_pixels:
        extracted_pixel = tuple([(channel & 15) * 17 for channel in cover_pixel])  # Using 4 bits for extraction
        extracted_pixels.append(extracted_pixel)

    extracted_image = Image.new(cover_image.mode, cover_image.size)
    extracted_image.putdata(extracted_pixels)

    img_io = io.BytesIO()
    extracted_image.save(img_io, 'PNG')
    img_io.seek(0)

    global latest_file_uuid
    file_uuid = str(uuid.uuid4())
    uuid_image_map[file_uuid] = img_io
    latest_file_uuid = file_uuid

    return jsonify({"extracted_image_url": request.url_root + 'processed'})

@app.route('/encode', methods=['POST'])
def encode_message():
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file part"}), 400
    if 'secret_message' not in request.form:
        return jsonify({"status": "error", "message": "No secret message"}), 400
    if 'password' not in request.form:
        return jsonify({"status": "error", "message": "Password is required"}), 400

    file = request.files['file']
    secret_message = request.form['secret_message']
    password = request.form['password']

    if file.filename == '':
        return jsonify({"status": "error", "message": "No selected file"}), 400

    try:
        image = Image.open(file.stream)
        secret_message_with_password = f"{secret_message}||{hashlib.sha256(password.encode()).hexdigest()}"
        encoded_image = lsb.hide(image, secret_message_with_password)
        encoded_image_bytes = io.BytesIO()
        encoded_image.save(encoded_image_bytes, format='PNG')
        encoded_image_bytes.seek(0)

        global latest_file_uuid
        file_uuid = str(uuid.uuid4())
        uuid_image_map[file_uuid] = encoded_image_bytes
        latest_file_uuid = file_uuid

        return send_file(encoded_image_bytes, mimetype='image/png')
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/decode', methods=['POST'])
def decode_message():
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No image part"}), 400
    if 'password' not in request.form:
        return jsonify({"status": "error", "message": "Password is required"}), 400

    image_file = request.files['file']
    password = request.form['password']

    try:
        image = Image.open(image_file.stream)
        decoded_message_with_password = lsb.reveal(image)
        if decoded_message_with_password is None:
            return jsonify({"status": "error", "message": "No hidden message found"}), 400
        secret_message, stored_password_hash = decoded_message_with_password.rsplit('||', 1)
        if hashlib.sha256(password.encode()).hexdigest() == stored_password_hash:
            return jsonify({"message": secret_message})
        else:
            return jsonify({"status": "error", "message": "Invalid password"}), 401
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
@app.route('/processed')
def send_latest_processed_file():
    if latest_file_uuid:
        img_io = uuid_image_map.get(latest_file_uuid)
        if img_io:
            img_io.seek(0)  # Ensure the stream is at the beginning
            return send_file(img_io, mimetype='image/png')
    return jsonify({"error": "No processed file found"}), 404
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
