"""
OTA Update Server for Raspberry Pi Pico W MicroPython
HTTP server that serves firmware updates to devices
"""

import http.server
import socketserver
import json
import os
from urllib.parse import urlparse, parse_qs

# Configuration
PORT = 8080
FIRMWARE_DIR = "firmware"
VERSION_FILE = "firmware/VERSION"

class UpdateHandler(http.server.BaseHTTPRequestHandler):
    """HTTP request handler for OTA updates"""

    def log_message(self, format, *args):
        """Custom log format"""
        print(f"[{self.log_date_time_string()}] {format % args}")

    def send_json_response(self, data, status=200):
        """Send a JSON response"""
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_GET(self):
        """Handle GET requests"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        query_params = parse_qs(parsed_path.query)

        if path == "/check":
            self.handle_check_update(query_params)
        elif path.startswith("/"):
            self.handle_download(path)
        else:
            self.send_error(404, "Not Found")

    def handle_check_update(self, query_params):
        """Check if an update is available for the requesting device"""
        try:
            current_version = query_params.get("version", ["unknown"])[0]

            # Read current firmware version from VERSION file
            if os.path.exists(VERSION_FILE):
                with open(VERSION_FILE, "r") as f:
                    latest_version = f.read().strip()
            else:
                latest_version = "1.0.0"

            # Check if update is needed
            update_available = current_version != latest_version

            response_data = {
                "update_available": update_available,
                "current_version": current_version,
                "new_version": latest_version,
                "file_path": "firmware.bin" if update_available else None
            }

            self.send_json_response(response_data)

        except Exception as e:
            self.send_error(500, str(e))

    def handle_download(self, path):
        """Download firmware file"""
        try:
            # Sanitize the path to prevent directory traversal attacks
            filename = os.path.basename(path.lstrip("/"))

            # Only allow specific files from firmware directory
            allowed_files = ["firmware.bin", "update.py"]
            if filename not in allowed_files:
                self.send_error(403, "Access Denied")
                return

            filepath = os.path.join(FIRMWARE_DIR, filename)

            if not os.path.exists(filepath):
                self.send_error(404, "File Not Found")
                return

            with open(filepath, "rb") as f:
                content = f.read()

            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", len(content))
            self.end_headers()
            self.wfile.write(content)

        except Exception as e:
            self.send_error(500, str(e))


def main():
    """Start the update server"""
    # Create firmware directory if it doesn't exist
    os.makedirs(FIRMWARE_DIR, exist_ok=True)

    # Create VERSION file if it doesn't exist
    version_path = os.path.join(FIRMWARE_DIR, "VERSION")
    if not os.path.exists(version_path):
        with open(version_path, "w") as f:
            f.write("1.0.0")

    print(f"OTA Update Server starting on port {PORT}")
    print(f"Firmware directory: {FIRMWARE_DIR}")

    with socketserver.TCPServer(("", PORT), UpdateHandler) as httpd:
        print(f"Serving updates at http://localhost:{PORT}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped")


if __name__ == "__main__":
    main()
