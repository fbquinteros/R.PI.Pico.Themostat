#!/usr/bin/env python3
"""Sign firmware.bin with CA private key"""

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
import os

FIRMWARE_DIR = "firmware"
CA_KEY_FILE = "../certificates/ca.key"


def sign_firmware():
    """Sign firmware.bin with CA private key"""
    ca_key_path = os.path.join(os.path.dirname(__file__), CA_KEY_FILE)
    firmware_path = os.path.join(FIRMWARE_DIR, "firmware.bin")
    signature_path = os.path.join(FIRMWARE_DIR, "firmware.bin.sig")

    if not os.path.exists(firmware_path):
        print("Firmware file not found - nothing to sign")
        return False

    if not os.path.exists(ca_key_path):
        print("CA private key not found - cannot sign firmware")
        return False

    # Read firmware
    with open(firmware_path, "rb") as f:
        firmware_data = f.read()

    # Read CA private key
    with open(ca_key_path, "rb") as f:
        ca_key = serialization.load_pem_private_key(
            f.read(),
            password=None,
            backend=default_backend()
        )

    # Sign firmware using RSA-PKCS1v15 with SHA256
    signature = ca_key.sign(
        firmware_data,
        padding.PKCS1v15(),
        hashes.SHA256()
    )

    # Save signature
    with open(signature_path, "wb") as f:
        f.write(signature)

    print(f"Firmware signed successfully: {signature_path}")
    return True


if __name__ == "__main__":
    sign_firmware()
