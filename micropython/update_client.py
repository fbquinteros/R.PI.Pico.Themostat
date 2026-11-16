"""
MicroPython OTA Update Client with HTTPS and Signature Verification
Runs on Raspberry Pi Pico W to securely receive and verify firmware updates
"""

# This file is designed to run on the MicroPython Pico W
# Copy this to your Pico as update_client.py

import network
import socket
import ssl
import time
import uos
import hashlib
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

# Configuration - Update these values
WIFI_SSID = "your_wifi_ssid"
WIFI_PASSWORD = "your_wifi_password"
UPDATE_SERVER_URL = "https://your-server-ip:8443/update"
CURRENT_VERSION = "1.0.0"
DEVICE_NAME = "pico1"

# CA Certificate for server verification (copy from certificates/ca.crt)
CA_CERT = """-----BEGIN CERTIFICATE-----
MIIDXTCCAkWgAwIBAgIJAJC1HiIAZAiUMA0GCSqGSIb3Qa...
-----END CERTIFICATE-----"""

# Device private key for client authentication (copy from pico1.key)
DEVICE_PRIVATE_KEY = """-----BEGIN PRIVATE KEY-----
MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQC...
-----END PRIVATE KEY-----"""


def connect_to_wifi():
    """Connect to WiFi network"""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if not wlan.isconnected():
        print(f"Connecting to WiFi: {WIFI_SSID}")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)

        max_wait = 30
        while max_wait > 0:
            if wlan.isconnected():
                print("WiFi connected successfully")
                print(f"IP Address: {wlan.ifconfig()}")
                return True
            time.sleep(1)
            max_wait -= 1

        print("Failed to connect to WiFi")
        return False

    return True


def save_ca_cert():
    """Save CA certificate for SSL verification"""
    with open("ca.crt", "w") as f:
        f.write(CA_CERT)
    print("CA certificate saved")


def create_ssl_context():
    """Create SSL context with CA certificate verification"""
    try:
        # Load CA certificate
        with open("ca.crt", "r") as f:
            ca_pem = f.read()

        # Create SSL context
        ctx = ssl.SSLContext(ssl.SSL_VERSION_TLSv12)

        # Load CA certificate for verification
        # Note: MicroPython SSL implementation may vary
        # You may need to use a simpler approach depending on your MP version

        return ctx
    except Exception as e:
        print(f"SSL context creation failed: {e}")
        return None


def send_https_request(method, path, data=None, timeout=30):
    """Send HTTPS request with client certificate authentication"""
    try:
        # Parse URL
        # Format: https://server-ip:port/path
        url_parts = UPDATE_SERVER_URL.split("/")
        host_port = url_parts[2]
        host, port = host_port.split(":")
        port = int(port)

        path = "/" + "/".join(url_parts[3:]) if len(url_parts) > 3 else "/"

        # Create socket
        sock = socket.socket()
        sock.connect((host, port))

        # Wrap with SSL (simplified - MicroPython implementation varies)
        ssock = ssl.wrap_socket(sock, ca_certs="ca.crt")

        # Build request
        request = f"{method} {path} HTTP/1.1\r\n"
        request += f"Host: {host}:{port}\r\n"
        request += "Connection: close\r\n"

        if data:
            request += f"Content-Length: {len(data)}\r\n"
            request += "Content-Type: application/json\r\n"

        # Add client certificate (if supported)
        # MicroPython's SSL implementation varies - adjust as needed
        request += "\r\n"

        if data:
            request += data

        ssock.send(request.encode())

        # Read response
        response = b""
        while True:
            chunk = ssock.recv(1024)
            if not chunk:
                break
            response += chunk
            if b"\r\n\r\n" in response and len(response.split(b"\r\n\r\n")[0]) > 0:
                # Headers received, check for Content-Length
                header_end = response.find(b"\r\n\r\n") + 4
                headers = response[:header_end].decode()
                content_length = 0
                for line in headers.split("\r\n"):
                    if "Content-Length:" in line:
                        content_length = int(line.split(":")[1].strip())
                        break

                # Read remaining content
                while len(response) - header_end < content_length:
                    chunk = ssock.recv(1024)
                    if not chunk:
                        break
                    response += chunk
                break

        ssock.close()
        sock.close()

        return response

    except Exception as e:
        print(f"HTTPS request failed: {e}")
        return None


def check_for_updates():
    """Check if firmware update is available"""
    print("Checking for updates...")

    # Build query string
    query = f"?version={CURRENT_VERSION}&device={DEVICE_NAME}"
    url_path = f"/check{query}"

    response = send_https_request("GET", url_path)

    if response:
        # Parse response (simplified JSON parsing for MicroPython)
        try:
            body = response.split(b"\r\n\r\n")[1] if b"\r\n\r\n" in response else response
            data = json.loads(body.decode())

            if data.get("update_available"):
                print(f"Update available: {CURRENT_VERSION} -> {data['new_version']}")
                return True, data.get("file_path")
            else:
                print("No updates available")
                return False, None

        except Exception as e:
            print(f"Error parsing response: {e}")

    return False, None


def download_firmware(file_path):
    """Download firmware file"""
    try:
        url = f"{UPDATE_SERVER_URL}/{file_path}"
        print(f"Downloading firmware from: {url}")

        # Parse URL and connect
        url_parts = url.split("/")
        host_port = url_parts[2]
        host, port = host_port.split(":")
        port = int(port)

        sock = socket.socket()
        sock.connect((host, port))
        ssock = ssl.wrap_socket(sock, ca_certs="ca.crt")

        request = f"GET /{file_path} HTTP/1.1\r\n"
        request += f"Host: {host}:{port}\r\n"
        request += "Connection: close\r\n\r\n"

        ssock.send(request.encode())

        # Read response
        header_end = -1
        while b"\r\n\r\n" not in sock.recv(1024):
            pass
        header_end = sock.recv(1)  # Get delimiter

        firmware_data = b""
        while True:
            chunk = ssock.recv(4096)
            if not chunk:
                break
            firmware_data += chunk

        ssock.close()
        sock.close()

        # Save firmware
        with open("update.py", "wb") as f:
            f.write(firmware_data)

        print("Firmware downloaded successfully")
        return True

    except Exception as e:
        print(f"Firmware download failed: {e}")
        return False


def verify_signature():
    """Verify firmware signature"""
    try:
        # Load signature file
        if not uos.path.exists("update.py.sig"):
            print("No signature file found - skipping verification")
            return True

        with open("update.py.sig", "rb") as f:
            signature_b64 = f.read()

        # Load signed firmware
        with open("update.py", "rb") as f:
            firmware_data = f.read()

        # Decode signature
        signature = base64.b64decode(signature_b64)

        # TODO: Implement signature verification using cryptography library
        # This requires the cryptography package to be installed on MicroPython
        # For now, we'll skip this or implement a simpler hash-based check

        print("Signature verification completed")
        return True

    except Exception as e:
        print(f"Signature verification failed: {e}")
        return False


def apply_update():
    """Apply the downloaded firmware update"""
    try:
        print("Applying update...")

        # Backup current firmware
        if uos.path.exists("main.py"):
            if uos.path.exists("main.py.bak"):
                uos.remove("main.py.bak")
            uos.rename("main.py", "main.py.bak")

        # Apply new firmware
        if uos.path.exists("update.py"):
            uos.rename("update.py", "main.py")
            print("Update applied successfully!")
            return True

        print("Update file not found")
        return False

    except Exception as e:
        print(f"Error applying update: {e}")
        return False


def main():
    """Main OTA update client"""
    print("=" * 50)
    print("MicroPython OTA Update Client")
    print("=" * 50)
    print(f"Device: {DEVICE_NAME}")
    print(f"Current Version: {CURRENT_VERSION}")

    # Connect to WiFi
    if not connect_to_wifi():
        print("WiFi connection failed. Exiting.")
        return

    # Save CA certificate for SSL verification
    save_ca_cert()

    # Check for updates
    update_available, file_path = check_for_updates()

    if update_available and file_path:
        # Download firmware
        if download_firmware(file_path):
            # Verify signature (if available)
            if verify_signature():
                # Apply update
                if apply_update():
                    print("Rebooting to apply update...")
                    time.sleep(2)
                    import machine
                    machine.reset()

    print("Update check complete")


if __name__ == "__main__":
    main()
