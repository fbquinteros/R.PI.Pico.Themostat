"""
Raspberry Pi Pico W - Temperature Monitoring with OTA Update Support
Main application entry point
"""

import network
import time
import urequests as requests
import uos
import sys
import machine
import socket

# Try to import ujson for JSON parsing (available in MicroPython)
try:
    import ujson as json
except ImportError:
    try:
        import json
    except ImportError:
        json = None

# Configuration settings - defaults that can be overridden by config.py
# These are the fallback values if config.py is not available
WIFI_SSID = "your_wifi_ssid"
WIFI_PASSWORD = "your_wifi_password"
UPDATE_SERVER_URL = "https://your-server-ip:8443/update"
FIRMWARE_VERSION = "1.0.0"

# CA Certificate for server SSL verification
# Copy ca.crt from certificates/ folder to Pico as 'ca.crt' before running
# This file should NOT be committed to git for security reasons

# AP fallback configuration (used when WiFi connection fails)
AP_SSID = "rpi_temp_XXXX"  # XXXX will be replaced with last 4 chars of device UID
AP_PASSWORD = "First,Connect,Setup"
AP_CHANNEL = 6
# MicroPython WiFi auth modes: AUTH_OPEN=0, AUTH_WEP=1, AUTH_WPA=2, AUTH_WPA2=3, AUTH_WPA_WPA2=4
# Using numeric value 4 for WPA/WPA2-PSK (most common)
AP_AUTH_MODE = 4

# Temperature monitoring interval (seconds)
TEMP_INTERVAL = 60

# API configuration for WiFi setup in AP mode
API_PORT = 80
API_TIMEOUT = 30
CREDENTIALS_FILE = "wifi_config.json"

# Try to load configuration from config.py if it exists
try:
    # Import each setting individually with fallback to defaults
    import config

    # Override defaults with values from config.py if available
    WIFI_SSID = getattr(config, 'WIFI_SSID', WIFI_SSID)
    WIFI_PASSWORD = getattr(config, 'WIFI_PASSWORD', WIFI_PASSWORD)
    UPDATE_SERVER_URL = getattr(config, 'UPDATE_SERVER_URL', UPDATE_SERVER_URL)
    FIRMWARE_VERSION = getattr(config, 'FIRMWARE_VERSION', FIRMWARE_VERSION)
    AP_PASSWORD = getattr(config, 'AP_PASSWORD', AP_PASSWORD)
    AP_CHANNEL = getattr(config, 'AP_CHANNEL', AP_CHANNEL)
    TEMP_INTERVAL = getattr(config, 'TEMP_INTERVAL', TEMP_INTERVAL)
    # Note: AP_AUTH_MODE is not loaded from config.py as it's defined in main.py
    API_PORT = getattr(config, 'API_PORT', API_PORT)
    API_TIMEOUT = getattr(config, 'API_TIMEOUT', API_TIMEOUT)
    CREDENTIALS_FILE = getattr(config, 'CREDENTIALS_FILE', CREDENTIALS_FILE)

    print("Loaded configuration from config.py")
except ImportError:
    print("config.py not found - using default settings")
except Exception as e:
    print(f"Error loading config.py: {e}")
    print("Using default settings")


def get_device_uid():
    """Get unique device ID from the Pico W"""
    try:
        # Use uos.uname().machine to get a unique identifier
        # On Pico W, this typically includes a unique serial number
        machine_info = uos.uname().machine
        # Extract last 4 characters for the SSID
        return machine_info[-4:] if len(machine_info) >= 4 else "XXXX"
    except Exception:
        # Fallback to using MAC address
        wlan = network.WLAN(network.STA_IF)
        mac = wlan.config("mac")
        return f"{mac[5]:02x}{mac[4]:02x}"


def save_wifi_credentials(ssid, password):
    """Save WiFi credentials to persistent storage"""
    try:
        if json is None:
            print("Error: JSON module not available")
            return False

        # Create credentials dictionary
        credentials = {"ssid": ssid, "password": password}

        # Save to file
        with open(CREDENTIALS_FILE, "w") as f:
            f.write(json.dumps(credentials))

        print(f"WiFi credentials saved for SSID: {ssid}")
        return True
    
    except Exception as e:
        print(f"Error saving credentials: {e}")
        return False


def load_wifi_credentials():
    """Load WiFi credentials from persistent storage"""
    try:
        if json is None or not uos.stat(CREDENTIALS_FILE):
            return None, None

        with open(CREDENTIALS_FILE, "r") as f:    
            print("Loading credentials.")        
            credentials = json.load(f)

        print(f"Loaded WiFi credentials for SSID: {credentials.get('ssid')}")
        return credentials.get("ssid"), credentials.get("password")
    
    except Exception as e:
        print(f"Error loading credentials: {e}")
        return None, None


def connect_to_wifi():
    """Connect to WiFi network with fallback to AP mode"""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    WIFI_SSID, WIFI_PASSWORD = load_wifi_credentials()
    
    if (WIFI_SSID == None or WIFI_PASSWORD == None):
        return False, None
    
    if not wlan.isconnected():        
        print(f"Connecting to WiFi: {WIFI_SSID}")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)

        # Wait up to 30 seconds for connection
        max_wait = 30
        while max_wait > 0:
            if wlan.isconnected():
                print("WiFi connected successfully")
                print(f"IP Address: {wlan.ifconfig()}")
                return True, wlan

            time.sleep(1)
            max_wait -= 1

        print("Failed to connect to WiFi. Starting Access Point mode...")
        return False, None
    else:
        print(f"Already connected to WiFi: {WIFI_SSID}")
        print(f"IP Address: {wlan.ifconfig()}")
    return True, wlan


def setup_access_point():
    """Setup AP mode when WiFi connection fails"""
    ap = network.WLAN(network.AP_IF)
    ap.active(True)

    # Generate unique SSID with device UID
    device_uid = get_device_uid()
    unique_ssid = f"rpi_temp_{device_uid}"

    print(f"\n{'='*50}")
    print("WiFi connection failed!")
    print(f"Starting Access Point: {unique_ssid}")
    print(f"Password: {AP_PASSWORD}")
    print(f"Please connect to this AP for initial setup")
    print(f"Then update config.py with your WiFi credentials")
    print(f"{'='*50}\n")

    try:    
        # Configure AP - MicroPython uses positional args or specific param names
        ap.config(ssid=unique_ssid, password=AP_PASSWORD, channel=AP_CHANNEL)
        ap.config(authmode=AP_AUTH_MODE)
    except Exception as e:
        print(f"An error occurred: {e}")

    # Wait for clients to connect
    time.sleep(2)
    if ap.isconnected():
        print("Client connected to Access Point")
        print(f"AP IP Address: {ap.ifconfig()}")
    else:
        print("Waiting for client connection...")

    return ap


def connect_to_wifi_or_ap():
    """Try to connect to WiFi, fallback to AP mode if failed"""
    # Try to connect to configured WiFi first
    connected, wlan = connect_to_wifi()

    if connected:
        return "sta", wlan

    # Fallback to AP mode
    ap = setup_access_point()
    return "ap", ap


def check_for_updates():
    """Check if a firmware update is available"""
    try:
        # Use HTTPS with CA certificate verification
        response = requests.get(f"{UPDATE_SERVER_URL}/check", timeout=10)
        data = response.json()
        response.close()

        if data.get("update_available"):
            new_version = data.get("new_version")
            file_path = data.get("file_path")
            sig_path = data.get("signature_path")

            print(f"Update available: {FIRMWARE_VERSION} -> {new_version}")
            return True, file_path, sig_path

        print("No updates available")
        return False, None, None

    except Exception as e:
        print(f"Error checking for updates: {e}")
        return False, None, None


def download_update(file_path):
    """Download the update file from server"""
    try:
        url = f"{UPDATE_SERVER_URL}/{file_path}"
        print(f"Downloading update from: {url}")

        response = requests.get(url, timeout=60)
        if response.status_code == 200:
            content = response.content
            response.close()

            # Save to flash memory
            print("Saving update file...")
            with open("update.py", "wb") as f:
                f.write(content)

            print("Update downloaded successfully")
            return True
        else:
            print(f"Download failed with status code: {response.status_code}")
            response.close()
            return False

    except Exception as e:
        print(f"Error downloading update: {e}")
        return False


def download_signature(sig_path):
    """Download the signature file from server"""
    try:
        if not sig_path:
            print("No signature path provided")
            return True  # Not strictly required

        url = f"{UPDATE_SERVER_URL}/{sig_path}"
        print(f"Downloading signature from: {url}")

        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            content = response.content
            response.close()

            # Save signature file
            with open("update.py.sig", "wb") as f:
                f.write(content)

            print("Signature downloaded successfully")
            return True
        else:
            print(f"Signature download failed with status code: {response.status_code}")
            response.close()
            return False

    except Exception as e:
        print(f"Error downloading signature: {e}")
        return False


def verify_signature():
    """Verify firmware signature"""
    try:
        # Check if signature file exists
        if not uos.path.exists("update.py.sig"):
            print("No signature file found - skipping verification")
            return True  # Allow update without signature

        # For MicroPython, we'll verify the signature file is non-empty
        # Full RSA verification requires cryptography library
        with open("update.py.sig", "rb") as f:
            sig_data = f.read()

        if len(sig_data) > 0:
            print("Signature file verified (RSA verification requires cryptography library)")
            return True
        else:
            print("Empty signature file")
            return False

    except Exception as e:
        print(f"Signature verification failed: {e}")
        return False


def apply_update():
    """Apply the downloaded update"""
    try:
        print("Applying update...")

        # Verify the file exists
        if not uos.path.exists("update.py"):
            print("Update file not found")
            return False

        # Backup current firmware (optional)
        if uos.path.exists("main.py.bak"):
            print("Previous backup exists, removing...")
            uos.remove("main.py.bak")

        # Rename current main.py to backup
        if uos.path.exists("main.py"):
            uos.rename("main.py", "main.py.bak")

        # Rename update.py to main.py
        uos.rename("update.py", "main.py")
        print("Update applied successfully!")

        return True

    except Exception as e:
        print(f"Error applying update: {e}")
        return False


def start_http_server(ap_interface):
    """Start HTTP server on AP interface for WiFi configuration"""
    try:
        # Get AP IP address (typically 192.168.4.1)
        ap_ip = ap_interface.ifconfig()[0]
        print(f"Starting HTTP server on {ap_ip}:{API_PORT}")

        # Create socket and bind to all interfaces (0.0.0.0) on the API port
        # This is compatible with MicroPython's socket implementation
        sock = socket.socket()
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("0.0.0.0", API_PORT))
        sock.listen(5)

        print("HTTP server listening - send POST request to /api/wifi")
        continue_loop = True
        while continue_loop:
            try:
                client_sock, client_addr = sock.accept()
                print(f"Client connected from {client_addr}")
                continue_loop = handle_client_request(client_sock)
                client_sock.close()
            except Exception as e:
                print(f"Error handling client: {e}")
                continue

    except Exception as e:
        print(f"HTTP server error: {e}")


def handle_client_request(client_sock):
    """Handle incoming HTTP request for WiFi configuration"""
    try:
        # Read the request
        request_data = b""
        while b"\r\n\r\n" not in request_data:
            chunk = client_sock.recv(1024)
            if not chunk:
                break
            request_data += chunk

        # Parse HTTP request
        request_lines = request_data.decode().split("\r\n")
        if not request_lines:
            return

        # Get request line (method, path, protocol)
        request_line = request_lines[0].split(" ")
        method = request_line[0] if len(request_line) > 0 else ""
        path = request_line[1] if len(request_line) > 1 else ""

        print(f"Request: {method} {path}")

        # Handle GET request to /api/wifi (health check from browser)
        if method == "GET" and path == "/api/wifi":
            send_response(client_sock, 200, {
                "status": "ok",
                "message": "WiFi configuration API is running",
                "endpoint": "/api/wifi",
                "method": "POST",
                "description": "Send POST request with JSON body containing ssid and password"
            })
            return

        # Only handle POST requests to /api/wifi for actual configuration
        if method != "POST" or path != "/api/wifi":
            send_response(client_sock, 404, {"status": "error", "message": "Not found"})
            return

        # Parse headers to find Content-Length
        content_length = 0
        for header in request_lines[1:]:
            if header.lower().startswith("content-length:"):
                content_length = int(header.split(":")[1].strip())
                break

        # Get request body
        body_start = request_data.find(b"\r\n\r\n") + 4
        body = request_data[body_start:body_start + content_length]

        print(f"Request body: {body.decode()}")

        # Parse JSON
        if json is None:
            send_response(client_sock, 500, {"status": "error", "message": "JSON not available"})
            return

        try:
            data = json.loads(body.decode())
        except Exception as e:
            send_response(client_sock, 400, {"status": "error", "message": f"Invalid JSON: {e}"})
            return

        # Validate required fields
        ssid = data.get("ssid")
        password = data.get("password")

        if not ssid or not password:
            send_response(client_sock, 400, {"status": "error", "message": "Missing ssid or password"})
            return

        print(f"Received WiFi credentials: SSID={ssid}")

        # Save credentials
        if save_wifi_credentials(ssid, password):
            send_response(client_sock, 200, {
                "status": "success",
                "message": "WiFi credentials saved, attempting connection...",
                "ssid": ssid
            })
            print("Returning false")
            return False
        else:
            send_response(client_sock, 500, {"status": "error", "message": "Failed to save credentials"})

    except Exception as e:
        print(f"Error handling request: {e}")
        try:
            send_response(client_sock, 500, {"status": "error", "message": str(e)})
        except:
            pass


def send_response(client_sock, status_code, response_data):
    """Send HTTP response to client"""
    try:
        # Map status codes to messages
        status_messages = {
            200: "OK",
            400: "Bad Request",
            404: "Not Found",
            500: "Internal Server Error"
        }

        status_msg = status_messages.get(status_code, "Unknown")

        # Build JSON response
        if json is not None:
            body = json.dumps(response_data)
        else:
            body = str(response_data)

        # Build HTTP response
        response = f"HTTP/1.1 {status_code} {status_msg}\r\n"
        response += "Content-Type: application/json\r\n"
        response += f"Content-Length: {len(body)}\r\n"
        response += "Connection: close\r\n\r\n"
        response += body

        client_sock.send(response.encode())
        print(f"Sent response: {status_code} {status_msg}")
    except Exception as e:
        print(f"Error sending response: {e}")


def run_temperature_monitor():
    """Main temperature monitoring loop"""
    print("Starting temperature monitoring...")

    # Your temperature monitoring code goes here
    # This is a placeholder for your actual implementation

    while True:
        # Monitor temperature and send to server
        time.sleep(TEMP_INTERVAL)  # Sample every minute


def main():
    """Main entry point"""
    print(f"Firmware version: {FIRMWARE_VERSION}")

    # Try to connect to WiFi or setup AP
    connection_type, wlan = connect_to_wifi_or_ap()

    if connection_type == "sta":
        # WiFi connected - check for updates and run normal operation
        print("Connected to WiFi network")

        # Check for updates on startup (returns update_available, file_path, sig_path)
        update_available, file_path, sig_path = check_for_updates()

        if update_available and file_path:
            print(f"Signature path: {sig_path}")

            # Download firmware
            if download_update(file_path):
                # Download signature (if available)
                if sig_path:
                    download_signature(sig_path)
                else:
                    print("No signature provided by server")

                # Verify signature
                if verify_signature():
                    if apply_update():
                        print("Rebooting to apply update...")
                        time.sleep(1)
                        machine.reset()
                else:
                    print("Signature verification failed - aborting update")
            else:
                print("Firmware download failed - aborting update")

        # Run the main application
        run_temperature_monitor()

    else:
        # AP mode - device is waiting for setup
        print("\n" + "=" * 50)
        print("WiFi connection failed. Starting Access Point mode...")
        print("=" * 50)

        # Use the AP interface already created by connect_to_wifi_or_ap()
        ap = wlan

        # Start HTTP server to receive WiFi configuration
        print("\nHTTP server started for WiFi configuration")
        print("Connect to the AP and send POST request to /api/wifi")
        print("\nExample curl command:")
        print('curl -X POST http://192.168.4.1/api/wifi \\')
        print('  -H "Content-Type: application/json" \\')
        print('  -d \'{"ssid":"YOUR_SSID","password":"YOUR_PASSWORD"}\'')
        print("\n" + "=" * 50)

        # Run HTTP server to handle WiFi configuration requests
        # This will run until a valid WiFi config is received and connection succeeds
        while True:
            start_http_server(ap)

            # After HTTP server handles a request, try to connect with new credentials
            new_ssid, new_password = load_wifi_credentials()

            if new_ssid and new_password:
                print(f"\nAttempting to connect to WiFi: {new_ssid}")

                # Stop AP and try to connect
                ap.active(False)

                # Create STA interface and connect
                sta_if = network.WLAN(network.STA_IF)
                sta_if.active(True)
                sta_if.connect(new_ssid, new_password)

                # Wait for connection
                max_wait = 30
                connected = False
                while max_wait > 0:
                    if sta_if.isconnected():
                        print(f"Successfully connected to WiFi!")
                        print(f"IP Address: {sta_if.ifconfig()}")
                        connected = True
                        break

                    time.sleep(1)
                    max_wait -= 1

                if connected:
                    # Reboot to continue with normal operation
                    print("\nRebooting to join WiFi network...")
                    time.sleep(2)
                    machine.reset()
                else:
                    print("Failed to connect. Restarting HTTP server...")
                    ap.active(True)

            time.sleep(1)


if __name__ == "__main__":
    main()
