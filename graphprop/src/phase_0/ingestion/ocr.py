import pytesseract
from PIL import Image
import io

def extract_text_from_images(images):
    text = ""

    for img_bytes in images:
        image = Image.open(io.BytesIO(img_bytes))
        text += pytesseract.image_to_string(image)

    return text