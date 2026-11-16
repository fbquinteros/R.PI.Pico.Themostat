# Firmware Compilation and Deployment Guide

This guide explains how to compile your MicroPython firmware for the Raspberry Pi Pico W and perform OTA updates using the pull-based update system.

## Prerequisites

### 1. Install Required Tools

**On your development machine (for building firmware):**
```bash
# Install Python 3.8+ with cryptography library
pip install cryptography

# Optional: Install MicroPython tooling for direct flashing
pip install mpremote

# For Ubuntu/Debian
sudo apt-get install python3-pip python3-venv
```

**For the Pico W:**
- [Thonny IDE](https://thonny.org/) (recommended for beginners)
- OR [Mu Editor](https://codewith.mu/)
- OR command-line `mpremote` tool

---

## Part 1: Initial Firmware Flash (First-Time Setup)

### Step 1: Prepare Your main.py

1. Edit `/home/adam/Development/r-pi-pico-temperature/main.py` with your WiFi credentials:

```python
# Update these lines (around line 25):
WIFI_SSID = "your_wifi_ssid"
WIFI_PASSWORD = "your_wifi_password"
UPDATE_SERVER_URL = "https://your-server-ip:8443/update"
FIRMWARE_VERSION = "1.0.0"
```

2. Create a `config.py` file for sensitive data (optional, git-ignored):

```python
# config.py - DO NOT COMMIT TO GIT
WIFI_SSID = "your_wifi_ssid"
WIFI_PASSWORD = "your_wifi_password"
UPDATE_SERVER_URL = "https://your-server-ip:8443/update"
FIRMWARE_VERSION = "1.0.0"
```

### Step 2: Copy CA Certificate to Pico

The Pico needs the CA certificate to verify HTTPS connections to your update server:

**Using mpremote:**
```bash
cd /home/adam/Development/r-pi-pico-temperature
mpremote cp certificates/ca.crt pico:ca.crt
```

**Using Thonny:**
1. Connect Pico W via USB
2. Open Thonny → Tools → Select "Raspberry Pi Pico (MicroPython)"
3. In the Files pane, drag `certificates/ca.crt` onto the Pico's file system
4. Rename to `ca.crt` if needed

### Step 3: Flash main.py to Pico

**Using Thonny:**
1. Connect Pico W via USB (press the BOOTSEL button while connecting if needed)
2. Open Thonny
3. Go to **Tools → Select Interpreter → Raspberry Pi Pico (MicroPython)**
4. Open `main.py` in Thonny
5. Click **Save** (floppy disk icon) - this transfers the file to the Pico
6. Click **Run** (green play button) to execute

**Using mpremote:**
```bash
cd /home/adam/Development/r-pi-pico-temperature
mpremote cp main.py pico:main.py
mpremote run main.py
```

### Step 4: Verify Initial Setup

After flashing, the Pico will:
1. Attempt to connect to WiFi using credentials in `main.py` or `config.py`
2. If WiFi fails, create an Access Point (`rpi_temp_XXXX`) for configuration
3. Log output to the serial console

**Check serial output (in Thonny):**
```
Firmware version: 1.0.0
Loading credentials.
Loaded WiFi credentials for SSID: your_wifi_ssid
Connecting to WiFi: your_wifi_ssid
WiFi connected successfully
IP Address: [...]
Checking for updates...
```

---

## Part 2: Creating Firmware Updates (OTA)

### Step 1: Make Changes to main.py

Edit your firmware code in `main.py`. For example, update the version:

```python
FIRMWARE_VERSION = "1.0.1"  # Increment version number
```

### Step 2: Create Update Package

Create the firmware files that the OTA server will serve:

```bash
cd /home/adam/Development/r-pi-pico-temperature

# Create/update VERSION file with new version
echo "1.0.1" > firmware/VERSION

# Copy main.py as the update firmware
cp main.py firmware/update.py

# Sign the firmware using CA private key
openssl dgst -sha256 -sign certificates/ca.key \
  -out firmware/firmware.bin.sig firmware/update.py
```

**Note:** The signature file must be named `firmware.bin.sig` for the server to serve it. If you're using `update.py` as the firmware name, also create a matching signature:

```bash
# Alternative: Create both naming conventions
cp firmware/update.py firmware/firmware.bin
openssl dgst -sha256 -sign certificates/ca.key \
  -out firmware/firmware.bin.sig firmware/firmware.bin
```

### Step 3: Start the Update Server

Start the HTTPS server on your machine (or a dedicated server):

```bash
cd /home/adam/Development/r-pi-pico-temperature

# Sign firmware and start server
python update_server_https.py --sign --port 8443
```

Expected output:
```
Signing firmware...
Firmware signed successfully: firmware/firmware.bin.sig
Secure OTA Update Server starting on port 8443
Firmware directory: firmware
CA Certificate: ../certificates/ca.crt
Server Certificate: ../certificates/server.crt
Available device certificates: ['pico1.crt', 'pico2.crt']
Secure server running at https://localhost:8443
Client certificate authentication enabled
```

**Important:** The server requires client certificate authentication. For testing without a Pico certificate, you can temporarily modify the `is_allowed_device()` method in `update_server_https.py` to accept any certificate, or generate a device certificate:

```bash
cd /home/adam/Development/r-pi-pico-temperature/certificates

# Generate a device certificate for testing
openssl req -newkey rsa:4096 -nodes \
  -keyout test_device.key -out test_device.csr \
  -subj "/C=US/ST=State/L=City/O=Test/CN=test_device"

openssl x509 -req -in test_device.csr \
  -CA ca.crt -CAkey ca.key -set_serial 12345 \
  -out test_device.crt -days 365
```

### Step 4: Trigger Update on Pico

The Pico checks for updates on startup. To trigger an update:

**Option A: Power cycle the Pico**
1. Unplug USB from Pico W
2. Reconnect - it will boot and check for updates

**Option B: Reset via code**
Add a manual reset trigger in your code or use the serial console to call `machine.reset()`.

**Option C: Manual update check (for testing)**
Connect via Thonny REPL and run:
```python
import main
main.check_for_updates()
```

### Step 5: Monitor Update Process

Watch the serial console for update progress:

```
Checking for updates...
Update available: 1.0.0 -> 1.0.1
Signature path: firmware.bin.sig
Downloading firmware from: https://your-server-ip:8443/update/firmware.bin
Saving update file...
Update downloaded successfully
Downloading signature from: https://your-server-ip:8443/update/firmware.bin.sig
Signature downloaded successfully
Signature file verified (RSA verification requires cryptography library)
Applying update...
Update applied successfully!
Rebooting to apply update...
```

---

## Part 3: Advanced - Full MicroPython Build Process

If you want to create a complete `.uf2` firmware file for flashing:

### Step 1: Install MicroPython SDK

```bash
# Clone the Raspberry Pi Pico SDK
git clone https://github.com/raspberrypi/pico-sdk.git ~/pico-sdk
export PICO_SDK_PATH=~/pico-sdk

# For C-based MicroPython projects (not needed for pure Python)
git clone https://github.com/micropython/micropython.git ~/micropython
cd ~/micropython/microboard/rp2
make BOARD=PICO_W
```

### Step 2: Pure Python Approach (Recommended)

For pure MicroPython code like `main.py`, you don't need to compile - just flash the `.py` files directly:

```bash
# Using mpremote
mpremote deploy .

# Or using Thonny's "Save As" feature to write to Pico
```

### Step 3: Create Combined Firmware (Optional)

If you want to bundle all Python files into a single firmware image:

```bash
# Create a zip of all MicroPython files
cd /home/adam/Development/r-pi-pico-temperature
zip -r pico_firmware.zip main.py config.py wifi_config.json ca.crt

# Flash using mpremote
mpremote deploy pico_firmware.zip:/
```

---

## Part 4: Troubleshooting

### Issue: Pico Can't Connect to WiFi

**Solution:** Check credentials and ensure `wifi_config.json` is created:
```python
# The Pico should auto-load from wifi_config.json after first successful connection
import uos
print(uos.listdir())  # Should show 'wifi_config.json'
```

### Issue: HTTPS Connection Fails

**Solution:** Verify CA certificate is on the Pico:
```python
import uos
uos.stat("ca.crt")  # Should succeed if file exists
```

### Issue: Update Not Detected

**Solutions:**
1. Ensure `firmware/VERSION` has a higher version than current
2. Check server is running and accessible
3. Verify client certificate authentication (generate device cert)

### Issue: Signature Verification Fails

**Note:** The current implementation uses graceful degradation - if full RSA verification isn't available, it checks that the signature file exists and is non-empty. For production, consider:
- Using `upycryptolib` if available on your MicroPython build
- Or using hash-based verification as a fallback

---

## Quick Reference Commands

```bash
# Start update server with signing
python update_server_https.py --sign

# Sign firmware manually
openssl dgst -sha256 -sign certificates/ca.key \
  -out firmware/firmware.bin.sig firmware/update.py

# Copy files to Pico
mpremote cp main.py pico:main.py
mpremote cp ca.crt pico:ca.crt

# Run on Pico
mpremote run main.py

# Deploy all files
mpremote deploy .

# Check Pico filesystem
mpremote ls pico:

# Flash UF2 file (if you have one)
# Copy the .uf2 file to the Pico's mass storage device
```

---

## Security Checklist

- [ ] CA private key (`ca.key`) is NOT committed to git
- [ ] Device certificates are signed by your CA
- [ ] WiFi credentials stored in `wifi_config.json` (git-ignored)
- [ ] Update server uses HTTPS with valid certificates
- [ ] Firmware is signed before deployment
- [ ] Signature verification runs on the Pico

---

## Next Steps

1. **Test locally:** Run the update server on your machine and verify the Pico can connect
2. **Deploy to production:** Host the update server on a publicly accessible machine
3. **Add monitoring:** Log update attempts and successes
4. **Implement rollback:** If updates fail, restore from `main.py.bak`
