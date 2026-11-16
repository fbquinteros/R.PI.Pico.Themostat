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
import uuid

# Import configuration from config.py (contains sensitive information)
from config import (
    WIFI_SSID,
    WIFI_PASSWORD,
    UPDATE_SERVER_URL,
    FIRMWARE_VERSION,
    AP_SSID,
    AP_PASSWORD,
    AP_CHANNEL,
    AP_AUTH_MODE,
    TEMP_INTERVAL
)


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


def connect_to_wifi():
    """Connect to WiFi network with fallback to AP mode"""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

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

    ap.config(essid=unique_ssid, password=AP_PASSWORD, channel=AP_CHANNEL)
    ap.config(authmode=AP_AUTH_MODE)

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
        response = requests.get(f"{UPDATE_SERVER_URL}/check", timeout=10)
        data = response.json()
        response.close()

        if data.get("update_available"):
            new_version = data.get("new_version")
            file_path = data.get("file_path")

            print(f"Update available: {FIRMWARE_VERSION} -> {new_version}")
            return True, file_path

        print("No updates available")
        return False, None

    except Exception as e:
        print(f"Error checking for updates: {e}")
        return False, None


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
        # Check for updates on startup
        update_available, file_path = check_for_updates()

        if update_available and file_path:
            if download_update(file_path) and apply_update():
                print("Rebooting to apply update...")
                time.sleep(1)
                machine.reset()

        # Run the main application
        run_temperature_monitor()

    else:
        # AP mode - device is waiting for setup
        print("\nDevice is in setup mode. Connect to the AP and update config.py.")
        print("After updating config, reset the device to connect to your WiFi.\n")

        # Keep AP running indefinitely in setup mode
        while True:
            time.sleep(60)


if __name__ == "__main__":
    main()
