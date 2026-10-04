import os
import sys
import zlib
import io

sys.set_int_max_str_digits(50000)
import cv2
import numpy as np
import qrcode
from PIL import Image, ImageDraw, ImageFont
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
UIDAI_DIR = os.path.join(REPO_ROOT, "models", "uidai")
OUTPUT_DIR = os.path.join(REPO_ROOT, "data", "demo_samples", "identity")
ID_PHOTO_PATH = os.path.join(OUTPUT_DIR, "id_photo.jpg")

PRIVATE_KEY_PATH = os.path.join(UIDAI_DIR, "test_key.pem")
PUBLIC_KEY_PATH = os.path.join(UIDAI_DIR, "test_pubkey.pem")


def ensure_test_keys():
    """Generates an RSA-2048 keypair for signing demo Secure QRs."""
    os.makedirs(UIDAI_DIR, exist_ok=True)
    if os.path.exists(PRIVATE_KEY_PATH) and os.path.exists(PUBLIC_KEY_PATH):
        with open(PRIVATE_KEY_PATH, "rb") as f:
            priv_key = serialization.load_pem_private_key(f.read(), password=None)
        return priv_key

    print("Generating RSA-2048 test keypair for Aadhaar Secure QR demo...")
    priv_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    
    with open(PRIVATE_KEY_PATH, "wb") as f:
        f.write(priv_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))

    pub_key = priv_key.public_key()
    with open(PUBLIC_KEY_PATH, "wb") as f:
        f.write(pub_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ))

    print(f"Saved test keys to {UIDAI_DIR}")
    return priv_key


def create_secure_qr_string(fields_dict, photo_bytes, private_key, corrupt_signature=False):
    """
    Encodes and signs a UIDAI Secure-QR-compatible payload:
    Text fields separated by 0xFF, followed by photo bytes, signed with RSA-2048 SHA-256.
    Compressed with zlib and converted to a big decimal integer string.
    """
    fields = [
        fields_dict.get("email_mobile_present", "3"),
        fields_dict.get("reference_id", "8821202610031234"),
        fields_dict.get("name", "Ravi Kumar"),
        fields_dict.get("dob", "15-08-1988"),
        fields_dict.get("gender", "M"),
        fields_dict.get("care_of", "S/O Suresh Kumar"),
        fields_dict.get("district", "Gurugram"),
        fields_dict.get("landmark", "Near IFFCO Chowk"),
        fields_dict.get("house", "Flat 402, Tower B"),
        fields_dict.get("location", "Sector 29"),
        fields_dict.get("pincode", "122001"),
        fields_dict.get("post_office", "DLF Phase 2"),
        fields_dict.get("state", "Haryana"),
        fields_dict.get("street", "MG Road"),
        fields_dict.get("sub_district", "Gurgaon"),
        fields_dict.get("vtc", "Gurugram")
    ]

    text_part = b"\xff".join(f.encode("utf-8") for f in fields) + b"\xff"
    data_to_sign = text_part + photo_bytes

    signature = private_key.sign(
        data_to_sign,
        padding.PKCS1v15(),
        hashes.SHA256()
    )

    if corrupt_signature:
        # Flip bits to invalidate signature
        signature = bytes([b ^ 0xAA for b in signature])

    full_payload = data_to_sign + signature
    compressed = zlib.compress(full_payload, level=9)
    qr_int = int.from_bytes(compressed, byteorder="big")
    return str(qr_int)


def generate_qr_image(qr_data_str: str) -> Image.Image:
    """Generates a high-density QR code image."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=4,
        border=2
    )
    qr.add_data(qr_data_str)
    qr.make(fit=True)
    return qr.make_image(fill_color="black", back_color="white").convert("RGB")


def render_aadhaar_card(
    printed_name: str,
    printed_dob: str,
    printed_gender: str,
    qr_img: Image.Image,
    photo_path: str,
    output_path: str
):
    """Renders a clean synthetic Aadhaar card image."""
    card_w, card_h = 860, 540
    card = Image.new("RGB", (card_w, card_h), (255, 255, 255))
    draw = ImageDraw.Draw(card)

    # Outer border and subtle background
    draw.rectangle([0, 0, card_w - 1, card_h - 1], outline=(200, 200, 200), width=3)
    draw.rectangle([10, 10, card_w - 10, card_h - 10], outline=(220, 220, 220), width=1)

    # Top Header Banner
    draw.rectangle([10, 10, card_w - 10, 75], fill=(245, 247, 250))
    # Tricolor accent strip
    draw.rectangle([10, 70, card_w - 10, 73], fill=(255, 153, 51))  # Saffron
    draw.rectangle([10, 73, card_w - 10, 76], fill=(19, 136, 8))    # Green

    # Header text
    draw.text((30, 22), "भारत सरकार  |  GOVERNMENT OF INDIA", fill=(20, 30, 60))
    draw.text((30, 45), "भारतीय विशिष्ट पहचान प्राधिकरण  |  UIDAI", fill=(100, 110, 130))

    # Photo (left side)
    if os.path.exists(photo_path):
        photo = Image.open(photo_path).convert("RGB")
        photo = photo.resize((150, 180))
        card.paste(photo, (40, 110))
        draw.rectangle([39, 109, 191, 291], outline=(180, 180, 180), width=2)
    else:
        draw.rectangle([40, 110, 190, 290], fill=(230, 230, 230), outline=(180, 180, 180), width=2)

    # Printed details (center)
    y_text = 120
    draw.text((220, y_text), "नाम / Name", fill=(110, 120, 135))
    draw.text((220, y_text + 20), printed_name, fill=(15, 23, 42))

    draw.text((220, y_text + 60), "जन्म तिथि / DOB", fill=(110, 120, 135))
    draw.text((220, y_text + 80), printed_dob, fill=(15, 23, 42))

    draw.text((220, y_text + 120), "लिंग / Gender", fill=(110, 120, 135))
    draw.text((220, y_text + 140), printed_gender, fill=(15, 23, 42))

    # Aadhaar Number Banner at bottom
    draw.rectangle([10, 420, card_w - 10, 520], fill=(248, 250, 252))
    draw.text((card_w // 2 - 140, 450), "XXXX  XXXX  8821", fill=(15, 23, 42))
    draw.text((card_w // 2 - 100, 485), "मेरा आधार, मेरी पहचान", fill=(120, 130, 145))

    # Secure QR Code (right side)
    qr_resized = qr_img.resize((240, 240))
    card.paste(qr_resized, (580, 105))
    draw.rectangle([579, 104, 821, 346], outline=(210, 210, 210), width=1)
    draw.text((615, 355), "UIDAI SECURE QR", fill=(130, 140, 155))

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    card.save(output_path, "PNG")
    print(f"Generated card: {output_path}")


def main():
    priv_key = ensure_test_keys()

    # Small 80x80 portrait JPEG for embedding inside QR
    if os.path.exists(ID_PHOTO_PATH):
        thumb = Image.open(ID_PHOTO_PATH).convert("RGB").resize((80, 80))
        bio = io.BytesIO()
        thumb.save(bio, "JPEG", quality=80)
        qr_photo_bytes = bio.getvalue()
    else:
        # Dummy bytes
        qr_photo_bytes = b"\x00" * 200

    fields_valid = {
        "name": "Ravi Kumar",
        "dob": "15-08-1988",
        "gender": "M",
        "reference_id": "8821202610031234"
    }

    # 1. Valid Secure QR
    qr_valid_str = create_secure_qr_string(fields_valid, qr_photo_bytes, priv_key, corrupt_signature=False)
    qr_valid_img = generate_qr_image(qr_valid_str)

    p1 = os.path.join(OUTPUT_DIR, "01_valid_aadhaar_card.png")
    render_aadhaar_card(
        printed_name="Ravi Kumar",
        printed_dob="15/08/1988",
        printed_gender="MALE / पुरुष",
        qr_img=qr_valid_img,
        photo_path=ID_PHOTO_PATH,
        output_path=p1
    )

    # 2. Tampered printed name ("Rajesh Sharma" vs signed "Ravi Kumar")
    p2 = os.path.join(OUTPUT_DIR, "02_tampered_printed_aadhaar.png")
    render_aadhaar_card(
        printed_name="Rajesh Sharma",
        printed_dob="15/08/1988",
        printed_gender="MALE / पुरुष",
        qr_img=qr_valid_img,  # Valid signed QR, but printed text doesn't match!
        photo_path=ID_PHOTO_PATH,
        output_path=p2
    )

    # 3. Invalid signature QR
    qr_corrupt_str = create_secure_qr_string(fields_valid, qr_photo_bytes, priv_key, corrupt_signature=True)
    qr_corrupt_img = generate_qr_image(qr_corrupt_str)

    p3 = os.path.join(OUTPUT_DIR, "03_invalid_signature_aadhaar.png")
    render_aadhaar_card(
        printed_name="Ravi Kumar",
        printed_dob="15/08/1988",
        printed_gender="MALE / पुरुष",
        qr_img=qr_corrupt_img,
        photo_path=ID_PHOTO_PATH,
        output_path=p3
    )

    print("All synthetic Aadhaar test cards created successfully!")


if __name__ == "__main__":
    main()
