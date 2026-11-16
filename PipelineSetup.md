# OTA Update Pipeline - Step-by-Step Setup Guide

This guide walks you through implementing the complete CI/CD pipeline for OTA updates to your Raspberry Pi Pico W.

## Prerequisites

1. **Python 3.8+** installed on your machine
2. **OpenSSL** for certificate generation
3. **Git** repository (GitHub, GitLab, etc.)
4. **Raspberry Pi Pico W** with MicroPython flashed

---

## Step 1: Generate SSL Certificates

First, generate the self-signed CA and server certificates:

```bash
cd certificates
python generate_cert.py
```

This will create:
- `ca.crt` / `ca.key` - Certificate Authority (keep private key secure!)
- `server.crt` / `server.key` - Server certificate for HTTPS
- `pico1.crt` / `pico1.key` - Sample device certificate

**Important:** Store private keys (`*.key`) in a secure location. Never commit them to version control!

---

## Step 2: Configure Your Firmware

Edit `main.py` with your actual credentials:

```python
# Configuration section (around line 13)
WIFI_SSID = "your_wifi_ssid"
WIFI_PASSWORD = "your_wifi_password"
UPDATE_SERVER_URL = "https://your-server-ip:8443/update"  # Use HTTPS!
FIRMWARE_VERSION = "1.0.0"
```

Also, copy the CA certificate to your Pico for SSL verification:

```python
# Add this to main.py after imports
import uos

# CA certificate content (base64 encoded in your actual implementation)
CA_CERT = """-----BEGIN CERTIFICATE-----
(your ca.crt content here)
-----END CERTIFICATE-----"""

# Save CA cert to flash
with open("ca.crt", "w") as f:
    f.write(CA_CERT)
```

---

## Step 3: Create Your First Firmware Update

Create a new firmware version in the `firmware/` directory:

```bash
mkdir -p firmware
echo "1.0.1" > firmware/VERSION
# Copy your updated main.py as firmware.bin or update.py
cp main.py firmware/update.py
```

---

## Step 4: Set Up GitHub Repository

Initialize git and push to GitHub:

```bash
git init
git add .
git commit -m "Initial OTA update setup"
git branch -M main
git remote add origin git@github.com:yourusername/r-pi-pico-temperature.git
git push -u origin main
```

---

## Step 5: Configure GitHub Actions Pipeline

The pipeline is already set up in `.github/workflows/ota-deploy.yml`. It includes:

### Phase 1: Verify & Test (runs on every push)
- **Lint**: Check Python syntax and code style
- **Unit Tests**: Validate server logic and certificate handling
- **Build**: Package firmware for deployment

### Phase 2: Deploy (runs on tag creation)
- **Sign Firmware**: Cryptographically sign the update
- **Deploy**: Upload to S3/HTTP server
- **Notify**: Send deployment status

---

## Step 6: Install Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install pytest pycodestyle boto3 cryptography
```

---

## Step 7: Run Tests Locally

Before deploying, verify everything works:

```bash
pytest tests/ -v
python update_server.py  # Start server locally to test
```

Test the OTA flow manually:
1. Start server: `python update_server.py`
2. Access `https://localhost:8443/check?version=1.0.0`
3. Verify signed firmware download works

---

## Step 8: Deploy an Update

### Trigger a Deployment

Create a new version tag:

```bash
# Increment version in firmware/VERSION
echo "1.0.2" > firmware/VERSION

# Commit changes
git add .
git commit -m "Release firmware version 1.0.2"

# Create and push tag (triggers deployment)
git tag v1.0.2
git push origin v1.0.2
```

### What Happens Automatically

1. GitHub Actions detects the new tag
2. Pipeline runs verification tests
3. Firmware is cryptographically signed
4. Signed firmware is deployed to your server
5. Devices on WiFi will receive the update on next startup check

---

## Step 9: Device Update Flow

Your Pico W will automatically:

1. **Connect to WiFi** on boot
2. **Verify Server Certificate** against your CA
3. **Request Update Check** via HTTPS with client certificate
4. **Download Signed Firmware** if available
5. **Verify Signature** before applying update
6. **Reboot** with new firmware

---

## Step 10: Monitor Deployment

Check GitHub Actions tab in your repository:
- Watch the workflow runs for each push/tag
- Review test results and deployment status
- Check logs for any errors

---

## Security Best Practices

1. **Never commit private keys** - add `*.key` to `.gitignore`
2. **Rotate certificates** periodically (ca.key is critical!)
3. **Use strong passwords** for WiFi and server access
4. **Enable firmware signature verification** on devices
5. **Monitor deployment logs** for unauthorized access attempts

---

## Troubleshooting

### Certificate Errors
```bash
# Verify certificate chain
openssl verify -CAfile ca.crt pico1.crt
openssl verify -CAfile ca.crt server.crt
```

### Server Not Starting
```bash
# Check port availability
netstat -tlnp | grep 8443

# Verify certificates are valid
openssl x509 -in server.crt -text -noout
```

### Device Can't Connect
- Verify WiFi credentials in `main.py`
- Check CA certificate matches what device trusts
- Ensure server is reachable from device's network

---

## Quick Reference Commands

```bash
# Generate new certificates
cd certificates && python generate_cert.py

# Start OTA server
python update_server.py

# Run tests
pytest tests/ -v

# Create deployment tag
git tag v1.0.x && git push origin v1.0.x

# Check workflow status
gh run list  # Requires GitHub CLI
```

---

## Next Steps

1. Customize `main.py` with your actual temperature monitoring code
2. Configure your cloud hosting (AWS S3, DigitalOcean, etc.)
3. Set up device provisioning for multiple Pico W units
4. Add rollback mechanism if updates fail
