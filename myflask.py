from flask import Flask, request, jsonify
import easyocr
import os
from werkzeug.utils import secure_filename
import logging
from PIL import Image
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configure upload settings
UPLOAD_FOLDER = '/tmp/ocr_uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

# Create upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize EasyOCR reader
try:
    reader = easyocr.Reader(['en'])
    logger.info("EasyOCR initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize EasyOCR: {str(e)}")
    raise

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/ocr', methods=['POST'])
def ocr():
    try:
        # Check if image file is present in request
        if 'image' not in request.files:
            return jsonify({"error": "No image file provided"}), 400
        
        image_file = request.files['image']
        
        # Check if a valid file was submitted
        if image_file.filename == '':
            return jsonify({"error": "No selected file"}), 400
            
        if not allowed_file(image_file.filename):
            return jsonify({"error": "File type not allowed"}), 400

        # Save the file with secure filename
        filename = secure_filename(image_file.filename)
        timestamp = int(time.time())
        unique_filename = f"{timestamp}_{filename}"
        image_path = os.path.join(UPLOAD_FOLDER, unique_filename)
        
        image_file.save(image_path)
        logger.info(f"Image saved to {image_path}")

        try:
            # Perform OCR
            result = reader.readtext(image_path)
            text = ' '.join([res[1] for res in result])
            word_count = len(text.split())
            
            # Clean up - delete the temporary file
            os.remove(image_path)
            
            return jsonify({
                "text": text,
                "word_count": word_count,
                "status": "success"
            })

        except Exception as e:
            logger.error(f"OCR processing error: {str(e)}")
            return jsonify({
                "error": "OCR processing failed",
                "details": str(e)
            }), 500

    except Exception as e:
        logger.error(f"Server error: {str(e)}")
        return jsonify({
            "error": "Server error",
            "details": str(e)
        }), 500

    finally:
        # Ensure cleanup of temporary file in case of errors
        if 'image_path' in locals() and os.path.exists(image_path):
            try:
                os.remove(image_path)
            except Exception as e:
                logger.error(f"Failed to remove temporary file: {str(e)}")

if __name__ == '__main__':
    # Set Flask server timeout to 5 minutes
    app.config['TIMEOUT'] = 300
    app.run(host='0.0.0.0', port=5000, threaded=True)