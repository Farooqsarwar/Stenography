from flask import Flask, request, send_file, jsonify
from PIL import Image
import io
import uuid
from stegano import lsb

app = Flask(__name__)

# Dictionary to store UUID to image mapping
uuid_image_map = {}

# Variable to store the most recent file UUID
latest_file_uuid = None

# Route for hiding an image within another image
@app.route('/hide_image', methods=['POST'])
def hide_image():
    cover_image_file = request.files['cover_image']
    secret_image_file = request.files['secret_image']
    password = request.form.get('password', '')  # password is currently not used

    cover_image = Image.open(cover_image_file.stream)
    secret_image = Image.open(secret_image_file.stream)

    # Ensure the images have the same size
    secret_image = secret_image.resize(cover_image.size)

    # Convert images to RGB mode
    cover_image = cover_image.convert('RGB')
    secret_image = secret_image.convert('RGB')

    # Get the pixel data from each image
    cover_pixels = list(cover_image.getdata())
    secret_pixels = list(secret_image.getdata())

    # Perform LSB algorithm to hide the secret image in the cover image
    new_pixels = []
    for cover_pixel, secret_pixel in zip(cover_pixels, secret_pixels):
        new_pixel = tuple([(cover_channel & 0b11111110) | (secret_channel >> 7) for cover_channel, secret_channel in zip(cover_pixel, secret_pixel)])
        new_pixels.append(new_pixel)

    # Create a new image with the modified pixel data
    new_image = Image.new('RGB', cover_image.size)
    new_image.putdata(new_pixels)

    # Save the image in memory
    img_io = io.BytesIO()
    new_image.save(img_io, 'PNG')
    img_io.seek(0)

    # Save UUID to image mapping and update the latest file UUID
    global latest_file_uuid
    file_uuid = str(uuid.uuid4())
    uuid_image_map[file_uuid] = img_io
    latest_file_uuid = file_uuid

    return jsonify({"encoded_image_url": request.url_root + 'processed'})

# Route for extracting an image hidden within another image
@app.route('/extract_image', methods=['POST'])
def extract_image():
    cover_image_file = request.files['cover_image']
    password = request.form.get('password', '')  # password is currently not used

    cover_image = Image.open(cover_image_file.stream)
    cover_image = cover_image.convert('RGB')

    cover_pixels = list(cover_image.getdata())

    extracted_pixels = []
    for cover_pixel in cover_pixels:
        extracted_pixel = tuple([(channel & 1) * 255 for channel in cover_pixel])
        extracted_pixels.append(extracted_pixel)

    extracted_image = Image.new('RGB', cover_image.size)
    extracted_image.putdata(extracted_pixels)

    img_io = io.BytesIO()
    extracted_image.save(img_io, 'PNG')
    img_io.seek(0)

    global latest_file_uuid
    file_uuid = str(uuid.uuid4())
    uuid_image_map[file_uuid] = img_io
    latest_file_uuid = file_uuid

    return jsonify({"extracted_image_url": request.url_root + 'processed'})

# Route for hiding a text message within an image
@app.route('/encode', methods=['POST'])
def encode_message():
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file part"})
    if 'secret_message' not in request.form:
        return jsonify({"status": "error", "message": "No secret message"})

    file = request.files['file']
    secret_message = request.form['secret_message']

    if file.filename == '':
        return jsonify({"status": "error", "message": "No selected file"})

    if file:
        image = Image.open(file.stream)

        # Encode the secret message into the image
        encoded_image = lsb.hide(image, secret_message)

        # Save encoded image to a BytesIO object
        encoded_image_bytes = io.BytesIO()
        encoded_image.save(encoded_image_bytes, format='PNG')
        encoded_image_bytes.seek(0)

        return send_file(encoded_image_bytes, mimetype='image/png')

# Route for extracting a text message hidden within an image
@app.route('/decode', methods=['POST'])
def decode_message():
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No image part"})

    image_file = request.files['file']
    image = Image.open(image_file.stream)

    decoded_message = lsb.reveal(image)
    return jsonify({"message": decoded_message})

# Route for sending the latest processed file
@app.route('/processed')
def send_latest_processed_file():
    if latest_file_uuid:
        img_io = uuid_image_map.get(latest_file_uuid)
        if img_io:
            return send_file(img_io, mimetype='image/png')
    return jsonify({"error": "No processed file found"}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
