"""
Certificate Generation Script for OTA Updates
Generates self-signed CA and device certificates for secure OTA updates
"""

import subprocess
import os
from pathlib import Path


def generate_ca():
    """Generate Certificate Authority (CA) key and certificate"""
    print("Generating CA private key...")
    subprocess.run([
        "openssl", "genrsa",
        "-out", "ca.key",
        "2048"
    ], check=True)

    print("Generating CA certificate...")
    subprocess.run([
        "openssl", "req",
        "-x509",
        "-new",
        "-nodes",
        "-key", "ca.key",
        "-sha256",
        "-days", "3650",  # 10 years
        "-out", "ca.crt",
        "-subj", "/C=US/ST=State/L=City/O=YourOrg/CN=PicoWOTA-CA"
    ], check=True)

    print("CA certificate generated: ca.crt, ca.key")


def generate_device_cert(device_name="pico1"):
    """Generate device-specific certificate signed by CA"""
    print(f"\nGenerating certificate for device: {device_name}")

    # Generate device private key
    print("Generating device private key...")
    subprocess.run([
        "openssl", "genrsa",
        "-out", f"{device_name}.key",
        "2048"
    ], check=True)

    # Generate certificate signing request (CSR)
    print("Generating CSR...")
    subprocess.run([
        "openssl", "req",
        "-new",
        "-key", f"{device_name}.key",
        "-out", f"{device_name}.csr",
        "-subj", f"/C=US/ST=State/L=City/O=YourOrg/CN={device_name}"
    ], check=True)

    # Sign the CSR with CA
    print("Signing certificate with CA...")
    subprocess.run([
        "openssl", "x509",
        "-req",
        "-in", f"{device_name}.csr",
        "-CA", "ca.crt",
        "-CAkey", "ca.key",
        "-CAcreateserial",
        "-out", f"{device_name}.crt",
        "-days", "365",
        "-sha256"
    ], check=True)

    # Remove CSR
    os.remove(f"{device_name}.csr")

    print(f"Device certificate generated: {device_name}.crt, {device_name}.key")


def generate_server_cert():
    """Generate server certificate signed by CA"""
    print("\nGenerating server certificate...")

    # Generate server private key
    subprocess.run([
        "openssl", "genrsa",
        "-out", "server.key",
        "2048"
    ], check=True)

    # Generate CSR
    subprocess.run([
        "openssl", "req",
        "-new",
        "-key", "server.key",
        "-out", "server.csr",
        "-subj", "/C=US/ST=State/L=City/O=YourOrg/CN=localhost"
    ], check=True)

    # Sign with CA (add SAN for localhost)
    # Write extension config to temp file since subprocess doesn't support bash process substitution
    ext_config = "subjectAltName=DNS:localhost,IP:127.0.0.1"
    with open("server.ext", "w") as f:
        f.write(ext_config)

    subprocess.run([
        "openssl", "x509",
        "-req",
        "-in", "server.csr",
        "-CA", "ca.crt",
        "-CAkey", "ca.key",
        "-CAcreateserial",
        "-out", "server.crt",
        "-days", "365",
        "-sha256",
        "-extfile", "server.ext"
    ], check=True)

    # Clean up temp extension file
    os.remove("server.ext")

    # Remove CSR
    os.remove("server.csr")

    print("Server certificate generated: server.crt, server.key")


def main():
    """Generate all certificates"""
    cert_dir = Path(__file__).parent.parent / "certificates"
    original_dir = os.getcwd()

    try:
        os.chdir(cert_dir)

        print("=" * 50)
        print("OTA Update Certificate Generator")
        print("=" * 50)

        # Generate CA
        generate_ca()

        # Generate server certificate
        generate_server_cert()

        # Generate a sample device certificate
        generate_device_cert("pico1")

        print("\n" + "=" * 50)
        print("All certificates generated successfully!")
        print("=" * 50)
        print("\nFiles created:")
        print("  - ca.crt, ca.key       : Certificate Authority")
        print("  - server.crt, server.key: Server certificate")
        print("  - pico1.crt, pico1.key : Sample device certificate")
        print("\nIMPORTANT: Store private keys securely!")

    finally:
        os.chdir(original_dir)


if __name__ == "__main__":
    main()
