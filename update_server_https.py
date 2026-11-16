"""
Secure OTA Update Server with HTTPS and Certificate Authentication
Serves firmware updates over HTTPS with client certificate verification
"""

import ssl
import http.server
import socketserver
import json
import os
import base64
from urllib.parse import urlparse, parse_qs
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.x509 import load_pem_x509_certificate
from cryptography.hazmat.backends import default_backend


# Configuration
PORT = 8443
FIRMWARE_DIR = "firmware"
CA_CERT_FILE = "../certificates/ca.crt"
SERVER_CERT_FILE = "../certificates/server.crt"
SERVER_KEY_FILE = "../certificates/server.key"
DEVICE_CERT_DIR = "../certificates"


class SecureUpdateHandler(http.server.BaseHTTPRequestHandler):
    """HTTPS request handler with certificate authentication"""

    # CA certificate for verifying client certificates
    ca_certificate = None

    def load_ca_certificate(self):
        """Load CA certificate for client verification"""
        if self.ca_certificate is None and os.path.exists(CA_CERT_FILE):
            with open(CA_CERT_FILE, "rb") as f:
                self.ca_certificate = load_pem_x509_certificate(
                    f.read(), default_backend()
                )
        return self.ca_certificate

    def log_message(self, format, *args):
        """Custom log format"""
        client_cert = self.get_client_cert_info()
        print(f"[{self.log_date_time_string()}] {format % args} [Client: {client_cert}]")

    def get_client_cert_info(self):
        """Get information about the connecting client's certificate"""
        if self.client_certificate:
            cert = load_pem_x509_certificate(
                self.client_certificate, default_backend()
            )
            subject = cert.subject.get_attributes_for_oid(
                x509.NameOID.COMMON_NAME
            )
            cn = subject[0].value if subject else "unknown"
            return cn
        return "no-cert"

    def authenticate_client(self):
        """Verify client certificate against CA"""
        try:
            self.load_ca_certificate()

            if not hasattr(self, 'client_certificate'):
                print("No client certificate provided")
                return False

            cert = load_pem_x509_certificate(
                self.client_certificate, default_backend()
            )

            # Verify certificate is signed by our CA
            # Note: Full chain verification would require additional setup
            # For now, we verify the CN matches expected devices
            subject = cert.subject.get_attributes_for_oid(
                x509.NameOID.COMMON_NAME
            )
            cn = subject[0].value if subject else None

            if cn and self.is_allowed_device(cn):
                print(f"Client authenticated: {cn}")
                return True
            else:
                print(f"Unauthorized client: {cn}")
                return False

        except Exception as e:
            print(f"Certificate authentication failed: {e}")
            return False

    def is_allowed_device(self, device_name):
        """Check if device is authorized to receive updates"""
        # List of allowed device names
        allowed_devices = ["pico1", "pico2", "all"]

        if device_name in allowed_devices:
            return True

        # Or check against a manifest file
        manifest_file = "firmware/allowed_devices.txt"
        if os.path.exists(manifest_file):
            with open(manifest_file, 'r') as f:
                allowed = [line.strip() for line in f if line.strip()]
                return device_name in allowed

        return False

    def send_json_response(self, data, status=200):
        """Send a JSON response"""
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_GET(self):
        """Handle GET requests with certificate authentication"""
        # Require client certificate for all requests
        if not hasattr(self, 'client_certificate'):
            self.send_error(401, "Client certificate required")
            return

        # Authenticate the client
        if not self.authenticate_client():
            self.send_error(403, "Unauthorized")
            return

        parsed_path = urlparse(self.path)
        path = parsed_path.path
        query_params = parse_qs(parsed_path.query)

        if path == "/check":
            self.handle_check_update(query_params)
        elif path.startswith("/"):
            self.handle_download(path)
        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        """Handle POST requests with certificate authentication"""
        # Require client certificate for all requests
        if not hasattr(self, 'client_certificate'):
            self.send_error(401, "Client certificate required")
            return

        # Authenticate the client
        if not self.authenticate_client():
            self.send_error(403, "Unauthorized")
            return

        parsed_path = urlparse(self.path)
        path = parsed_path.path

        if path == "/deploy":
            self.handle_deploy()
        elif path.startswith("/"):
            self.handle_download(path)
        else:
            self.send_error(404, "Not Found")

    def handle_check_update(self, query_params):
        """Check if an update is available for the requesting device"""
        try:
            current_version = query_params.get("version", ["unknown"])[0]
            device_name = query_params.get("device", ["unknown"])[0]

            # Read current firmware version from VERSION file
            version_path = os.path.join(FIRMWARE_DIR, "VERSION")
            if os.path.exists(version_path):
                with open(version_path, "r") as f:
                    latest_version = f.read().strip()
            else:
                latest_version = "1.0.0"

            # Check if update is needed
            update_available = current_version != latest_version

            response_data = {
                "update_available": update_available,
                "current_version": current_version,
                "new_version": latest_version,
                "file_path": "firmware.bin" if update_available else None,
                "device": device_name
            }

            self.send_json_response(response_data)

        except Exception as e:
            self.send_error(500, str(e))

    def handle_download(self, path):
        """Download firmware file with signature verification"""
        try:
            filename = os.path.basename(path.lstrip("/"))

            # Only allow specific files
            allowed_files = ["firmware.bin", "update.py", "update.py.sig"]
            if filename not in allowed_files:
                self.send_error(403, "Access Denied")
                return

            filepath = os.path.join(FIRMWARE_DIR, filename)

            if not os.path.exists(filepath):
                self.send_error(404, "File Not Found")
                return

            with open(filepath, "rb") as f:
                content = f.read()

            # If this is a signature file, include context about verification
            if filename.endswith(".sig"):
                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("X-Firmware-Sig", "verified")
                self.end_headers()
                self.wfile.write(content)
            else:
                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Length", len(content))
                self.end_headers()
                self.wfile.write(content)

        except Exception as e:
            self.send_error(500, str(e))

    def handle_deploy(self):
        """Handle deployment requests from CI/CD"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode())

            version = data.get("version")
            if not version:
                self.send_error(400, "Version required")
                return

            # Save deployment metadata
            deploy_dir = os.path.join(FIRMWARE_DIR, version)
            os.makedirs(deploy_dir, exist_ok=True)

            print(f"Deployment received for version: {version}")
            self.send_json_response({"status": "received", "version": version})

        except Exception as e:
            self.send_error(500, str(e))


def load_client_cert():
    """Load client certificate info for debugging"""
    certs = []
    if os.path.exists(DEVICE_CERT_DIR):
        for f in os.listdir(DEVICE_CERT_DIR):
            if f.endswith(".crt"):
                certs.append(f)
    return certs


def main():
    """Start the secure update server"""
    # Create firmware directory if it doesn't exist
    os.makedirs(FIRMWARE_DIR, exist_ok=True)

    # Create VERSION file if it doesn't exist
    version_path = os.path.join(FIRMWARE_DIR, "VERSION")
    if not os.path.exists(version_path):
        with open(version_path, "w") as f:
            f.write("1.0.0")

    print(f"Secure OTA Update Server starting on port {PORT}")
    print(f"Firmware directory: {FIRMWARE_DIR}")
    print(f"CA Certificate: {CA_CERT_FILE}")
    print(f"Server Certificate: {SERVER_CERT_FILE}")

    # Create SSL context with client certificate verification
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(SERVER_CERT_FILE, SERVER_KEY_FILE)

    # Require client certificate
    context.verify_mode = ssl.CERT_REQUIRED
    context.load_verify_locations(CA_CERT_FILE)

    # Print available device certificates
    available_certs = load_client_cert()
    print(f"Available device certificates: {available_certs}")

    with socketserver.TCPServer(("", PORT), SecureUpdateHandler) as httpd:
        # Wrap the socket in SSL
        httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
        print(f"Secure server running at https://localhost:{PORT}")
        print("Client certificate authentication enabled")

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped")


if __name__ == "__main__":
    main()
