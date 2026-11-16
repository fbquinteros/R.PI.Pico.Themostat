# Step-by-Step Implementation Guide: OTA Pipeline for Pico W

This document provides a detailed, sequential guide to implementing and deploying the OTA update system.

---

## Prerequisites Checklist

Before starting, ensure you have:

- [ ] Raspberry Pi Pico W with MicroPython flashed
- [ ] Python 3.8+ installed on your development machine
- [ ] OpenSSL installed (`openssl version` in terminal)
- [ ] Git repository created (GitHub recommended)
- [ ] Thonny or Mu editor for flashing Pico W

---

## Phase 1: Certificate Setup (Day 1)

### Step 1.1: Generate CA and Server Certificates

```bash
cd /home/adam/Development/r-pi-pico-temperature/certificates
python generate_cert.py
```

**Expected output:**
```
==================================================
OTA Update Certificate Generator
==================================================
Generating CA private key...
Generating CA certificate...
CA certificate generated: ca.crt, ca.key
Generating server certificate...
Server certificate generated: server.crt, server.key
Generating certificate for device: pico1
Device certificate generated: pico1.crt, pico1.key

==================================================
All certificates generated successfully!
==================================================
```

### Step 1.2: Verify Certificates

```bash
# Verify CA certificate
openssl x509 -in ca.crt -text -noout | head -20

# Verify server certificate is signed by CA
openssl verify -CAfile ca.crt server.crt

# Verify device certificate is signed by CA
openssl verify -CAfile ca.crt pico1.crt
```

### Step 1.3: Secure Private Keys

Create a secure backup of private keys (NOT in git):

```bash
mkdir -p ~/secure/keys
cp ca.key server.key pico1.key ~/secure/keys/
chmod 600 ~/secure/keys/*.key
```

---

## Phase 2: Firmware Development (Day 1-2)

### Step 2.1: Configure Your Application

Edit `main.py` with your actual credentials:

```python
# Update these lines in main.py:
WIFI_SSID = "YOUR_WIFI_NAME"
WIFI_PASSWORD = "YOUR_WIFI_PASSWORD"
UPDATE_SERVER_URL = "https://YOUR_SERVER_IP:8443/update"
FIRMWARE_VERSION = "1.0.0"
```

### Step 2.2: Add CA Certificate to Firmware

Add this to your `main.py` after the imports:

```python
# CA certificate for SSL verification
CA_CERT = """-----BEGIN CERTIFICATE-----
MIIDXTCCAkWgAwIBAgIJAJC1HiIAZAiUMA0GCSqGSIb3Qa...
-----END CERTIFICATE-----"""
```

(Replace with actual content from `certificates/ca.crt`)

### Step 2.3: Flash to Pico W

Using Thonny:
1. Connect Pico W via USB
2. Open `main.py` in Thonny
3. Select Python (MicroPython) interpreter
4. Click "Save" to transfer to device
5. Click "Run" to execute

---

## Phase 3: Server Setup (Day 2)

### Step 3.1: Test Server Locally

```bash
cd /home/adam/Development/r-pi-pico-temperature

# Start HTTPS server (requires certificates in correct location)
python update_server_https.py
```

**Expected output:**
```
Secure OTA Update Server starting on port 8443
Firmware directory: firmware
CA Certificate: ../certificates/ca.crt
Server Certificate: ../certificates/server.crt
Available device certificates: ['pico1.crt']
Secure server running at https://localhost:8443
Client certificate authentication enabled
```

### Step 3.2: Test API Endpoints

Open another terminal:

```bash
# Check update availability (requires client cert)
curl --cert pico1.crt --key pico1.key \
  https://localhost:8443/update/check?version=1.0.0

# Expected response:
# {"update_available": false, "current_version": "1.0.0", ...}
```

---

## Phase 4: Git Repository Setup (Day 2)

### Step 4.1: Initialize Git Repository

```bash
cd /home/adam/Development/r-pi-pico-temperature

# Initialize git
git init

# Create .gitignore (already created, but verify)
cat .gitignore | grep -A 5 "Private keys"

# Stage all files
git add .

# Initial commit
git commit -m "Initial OTA update setup with HTTPS and signing"
```

### Step 4.2: Push to GitHub

```bash
# Create repository on GitHub first, then:
git branch -M main
git remote add origin git@github.com:YOUR_USERNAME/r-pi-pico-temperature.git
git push -u origin main
```

---

## Phase 5: CI/CD Pipeline Configuration (Day 3)

### Step 5.1: Configure GitHub Secrets

Go to your repository → Settings → Secrets and variables → Actions

Add these secrets:

| Secret Name | Value | How to Get |
|-------------|-------|------------|
| `FIRMWARE_SIGNING_KEY` | Your signing private key | From step 1.3 backup or generate new |
| `AWS_ACCESS_KEY_ID` | AWS access key | If using S3 deployment |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | If using S3 deployment |
| `AWS_S3_PATH` | s3://your-bucket/firmware | Your S3 path |
| `HTTP_SERVER_URL` | https://your-server:8443 | Your OTA server URL |
| `DEPLOYMENT_TOKEN` | Your auth token | Server API token |
| `NOTIFICATION_WEBHOOK_URL` | Slack webhook URL | For notifications |

### Step 5.2: Test Pipeline Locally

```bash
# Install test dependencies
pip install pytest pycodestyle cryptography boto3

# Run all tests
pytest tests/ -v

# Check linting
pycodestyle update_server_https.py main.py
```

---

## Phase 6: First Deployment (Day 3-4)

### Step 6.1: Create Initial Firmware Package

```bash
# Create firmware directory
mkdir -p firmware

# Set initial version
echo "1.0.0" > firmware/VERSION

# Copy your main.py as update package
cp main.py firmware/update.py

# Verify structure
ls -la firmware/
```

### Step 6.2: Commit and Tag for Deployment

```bash
git add .
git commit -m "Release initial firmware v1.0.0"

# Create deployment tag
git tag v1.0.0

# Push to trigger pipeline
git push origin main
git push origin v1.0.0
```

### Step 6.3: Monitor Pipeline Execution

1. Go to GitHub → Actions tab
2. Watch the "OTA Update Pipeline" workflow run
3. Verify all steps complete successfully

**Expected workflow stages:**
- ✅ verify-and-test (Lint, Tests, Build)
- ⏳ deploy (Sign, Deploy, Notify) - triggers after tag push
- ✅ security-scan (Bandit, Safety)

---

## Phase 7: Device Update Testing (Day 4-5)

### Step 7.1: Test OTA Flow Manually

On your Pico W:
1. Power cycle the device
2. Check serial output for update check messages
3. Verify it connects to server securely

Expected console output:
```
==================================================
MicroPython OTA Update Client
==================================================
Device: pico1
Current Version: 1.0.0
Connecting to WiFi: YOUR_WIFI_NAME
WiFi connected successfully
IP Address: ['192.168.x.x', ...]
Checking for updates...
No updates available
Update check complete
```

### Step 7.2: Trigger an Update

On your development machine:

```bash
# Increment version
echo "1.0.1" > firmware/VERSION

# Add some code change to main.py (e.g., update a comment)

git add .
git commit -m "Update firmware to v1.0.1"

# Create new tag
git tag v1.0.1
git push origin v1.0.1
```

### Step 7.3: Verify Update on Device

Power cycle the Pico W again. Expected output:
```
Checking for updates...
Update available: 1.0.0 -> 1.0.1
Downloading firmware from: https://.../firmware/update.py
Firmware downloaded successfully
Applying update...
Update applied successfully!
Rebooting to apply update...
```

---

## Phase 8: Production Hardening (Day 5+)

### Step 8.1: Add Device Manifest

Create `firmware/allowed_devices.txt`:

```txt
pico1
pico2
all
```

### Step 8.2: Configure Rollback

Add to your firmware logic:
```python
# Check if new firmware is working
if not verify_firmware():
    print("New firmware failed, rolling back...")
    uos.rename("main.py", "update.py.bak")
    uos.rename("main.py.bak", "main.py")
    machine.reset()
```

### Step 8.3: Set Up Monitoring

Configure alerts for:
- Failed deployments in GitHub Actions
- Certificate expiry (use `openssl x509 -checkend 86400`)
- Device connection failures

---

## Quick Reference Commands

```bash
# Generate certificates
cd certificates && python generate_cert.py

# Start HTTPS server
python update_server_https.py

# Test API
curl --cert pico1.crt --key pico1.key \
  https://localhost:8443/update/check?version=1.0.0

# Deploy new version
echo "1.0.X" > firmware/VERSION
git add . && git commit -m "Release v1.0.X"
git tag v1.0.X && git push origin v1.0.X

# Check certificate expiry
openssl x509 -in ca.crt -checkend 2592000 -noout

# Run tests locally
pytest tests/ -v
```

---

## Common Issues & Solutions

### Issue: "Client certificate required" error
**Solution:** Ensure client is presenting valid certificate signed by your CA

### Issue: "Certificate verify failed"
**Solution:** Verify CA cert on device matches server's CA

### Issue: Pipeline not triggering
**Solution:** Ensure tag format is `v*` (e.g., v1.0.0, v2.0.0)

### Issue: Private key rejected
**Solution:** Check key format - should be PEM encoded with BEGIN/END markers

---

## Next Steps After Implementation

1. **Add multiple devices** - Generate certificates for each Pico W
2. **Implement version rollback** - Automatic fallback on failed updates
3. **Add delta updates** - Only send changed portions of firmware
4. **Set up staging environment** - Test updates before production
5. **Document device provisioning** - How to enroll new devices

---

**Timeline Summary:**
- Day 1: Certificates + Initial firmware
- Day 2: Server setup + Git repository
- Day 3: CI/CD configuration + First deployment
- Day 4-5: Testing + Production hardening
