# Image Steganography Flask App

This Flask application allows you to hide an image or a text message within another image using steganography techniques. The application provides endpoints to hide and extract images, as well as encode and decode text messages within images.

## Features

- Hide an image within another image
- Extract an image hidden within another image
- Encode a text message within an image
- Decode a text message hidden within an image

## Installation

1. Clone the repository:
    ```bash
    git clone https://github.com/Farooqsarwar/Stenography.git
    cd Stenography
    ```

2. Create a virtual environment:
    ```bash
    python -m venv venv
    ```

3. Activate the virtual environment:
    - On Windows:
        ```bash
        venv\Scripts\activate
        ```
    - On macOS/Linux:
        ```bash
        source venv/bin/activate
        ```

4. Install the dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

1. Start the Flask application:
    ```bash
    python app.py
    ```

2. Use the following endpoints to interact with the application:

### Hide an image within another image

- **URL:** `/hide_image`
- **Method:** `POST`
- **Parameters:**
    - `cover_image`: The cover image file.
    - `secret_image`: The secret image file.
    - `password`: Optional password (currently not used).
- **Response:**
    ```json
    {
        "encoded_image_url": "http://<your-domain>/processed"
    }
    ```

### Extract an image hidden within another image

- **URL:** `/extract_image`
- **Method:** `POST`
- **Parameters:**
    - `cover_image`: The cover image file with hidden image.
    - `password`: Optional password (currently not used).
- **Response:**
    ```json
    {
        "extracted_image_url": "http://<your-domain>/processed"
    }
    ```

### Encode a text message within an image

- **URL:** `/encode`
- **Method:** `POST`
- **Parameters:**
    - `file`: The image file.
    - `secret_message`: The text message to be hidden.
- **Response:** Returns the image file with the encoded message.

### Decode a text message hidden within an image

- **URL:** `/decode`
- **Method:** `POST`
- **Parameters:**
    - `file`: The image file with hidden text message.
- **Response:**
    ```json
    {
        "message": "The hidden message"
    }
    ```

### Get the latest processed file

- **URL:** `/processed`
- **Method:** `GET`
- **Response:** Returns the latest processed image file.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

**Author**: Farooqsarwar
**Repository**: [Image Steganography Flask App](https://github.com/Farooqsarwar/Stenography.git)
