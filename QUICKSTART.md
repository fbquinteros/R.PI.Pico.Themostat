# Quick Start Guide - Flash and Update Your Pico W

This is the fastest way to get your Raspberry Pi Pico W running with OTA updates.

## Prerequisites Checklist

- [ ] Raspberry Pi Pico W connected via USB
- [ ] Thonny IDE installed ([thonny.org](https://thonny.org))
- [ ] Python 3.8+ installed on your computer (for the update server)
- [ ] Project folder at `/home/adam/Development/r-pi-pico-temperature`

---

## Step 1: Flash Initial Firmware (5 minutes)

### A. Open Thonny and Connect Pico

```
1. Plug in Pico W via USB
2. Open Thonny
3. Tools → Select Interpreter → Raspberry Pi Pico (MicroPython)
4. Bottom-right should show "Running on Raspberry Pi Pico"
```

### B. Edit main.py with Your WiFi Credentials

Open `main.py` in Thonny and update these lines:

```python
# Lines 25-27 - UPDATE THESE!
WIFI_SSID = "your_wifi_ssid"           # ← Change this
WIFI_PASSWORD = "your_wifi_password"    # ← Change this
UPDATE_SERVER_URL = "https://192.168.1.100:8443/update"  # ← Your server IP
```

### C. Save to Pico

```
1. Click the "Save" button (floppy disk icon)
2. Save as: main.py (on the Raspberry Pi Pico device)
3. Click the "Run" button (green play icon)
```

**Expected output in Thonny shell:**
```
Firmware version: 1.0.0
Loading credentials.
Loaded WiFi credentials for SSID: your_wifi_ssid
Connecting to WiFi: your_wifi_ssid
WiFi connected successfully
IP Address: [...]
Checking for updates...
No updates available
Starting temperature monitoring...
```

---

## Step 2: Set Up the Update Server (5 minutes)

### A. Install Python Dependencies

```bash
pip install cryptography
```

### B. Copy CA Certificate to Pico

In Thonny, drag `certificates/ca.crt` from your computer onto the Pico's file list (rename to `ca.crt`).

### C. Start the Update Server

```bash
cd /home/adam/Development/r-pi-pico-temperature
python update_server_https.py --sign
```

**Expected output:**
```
Signing firmware...
Firmware signed successfully: firmware/firmware.bin.sig
Secure OTA Update Server starting on port 8443
...
Secure server running at https://localhost:8443
```

Keep this terminal open!

---

## Step 3: Create Your First Firmware Update (3 minutes)

### A. Increment Version Number

Edit `main.py` and change:
```python
FIRMWARE_VERSION = "1.0.1"  # Was "1.0.0"
```

### B. Create Update Package

```bash
cd /home/adam/Development/r-pi-pico-temperature

# Update VERSION file
echo "1.0.1" > firmware/VERSION

# Copy main.py as the update
cp main.py firmware/update.py

# Sign it
openssl dgst -sha256 -sign certificates/ca.key \
  -out firmware/firmware.bin.sig firmware/update.py
```

### C. Trigger Update on Pico

**Option 1: Power cycle**
- Unplug USB from Pico W, wait 5 seconds, plug back in

**Option 2: Reset button**
- Press the RESET button on the Pico W

Watch Thonny's shell for:
```
Checking for updates...
Update available: 1.0.0 -> 1.0.1
Downloading firmware from: https://localhost:8443/update/firmware.bin
Saving update file...
Update downloaded successfully
Applying update...
Update applied successfully!
Rebooting to apply update...
```

---

## Step 4: Verify Update Success

After reboot, check the shell output:
```
Firmware version: 1.0.1
Loading credentials.
Loaded WiFi credentials for SSID: your_wifi_ssid
Connecting to WiFi: your_wifi_ssid
WiFi connected successfully
Checking for updates...
No updates available
Starting temperature monitoring...
```

If it shows `1.0.1`, the update was successful!

---

## Common Issues

### "No module named 'urequests'"
- Make sure you're using MicroPython firmware (not CircuitPython)
- Re-flash Pico with latest MicroPython from [raspberrypi.com](https://www.raspberrypi.com/documentation/microcontrollers/raspberry-pi-pico.html)

### "Connection refused" on update check
- Verify the server is running: `python update_server_https.py --sign`
- Check your IP address is correct in `UPDATE_SERVER_URL`

### Certificate errors
- Ensure `ca.crt` is on the Pico (check in Thonny's Files pane)

---

## What Happens Next?

Your Pico W will now:
1. Boot and connect to WiFi
2. Check for updates every time it starts
3. Download and verify any new firmware automatically
4. Apply updates and reboot

To deploy future updates:
1. Edit `main.py` with your changes
2. Increment `FIRMWARE_VERSION`
3. Create update package (Step 3B)
4. Power cycle the Pico (Step 3C)

---

## Full Documentation

For advanced topics (CI/CD, custom certificates, production deployment), see:
- `FIRMWARE_GUIDE.md` - Complete compilation and deployment guide
- `README.md` - Project overview and architecture
- `certificates/README.md` - Certificate management
