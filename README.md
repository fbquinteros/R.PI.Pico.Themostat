# Raspberry Pi Pico W - OTA Update System

A secure Over-The-Air (OTA) update system for Raspberry Pi Pico W running MicroPython, featuring HTTPS with mutual TLS authentication and cryptographic firmware signing.

## Features

- **HTTPS Secure Communication** - All updates transmitted over encrypted HTTPS
- **Mutual TLS Authentication** - Both server and client authenticate using certificates
- **Cryptographic Signing** - Firmware updates are signed and verified before installation
- **CI/CD Pipeline** - Automated testing, signing, and deployment via GitHub Actions
- **Rollback Support** - Original firmware backed up before updates

## Project Structure

```
r-pi-pico-temperature/
├── .github/workflows/
│   └── ota-deploy.yml          # CI/CD pipeline configuration
├── certificates/
│   ├── generate_cert.py        # Certificate generation script
│   ├── ca.crt / ca.key         # CA certificate (keep key secret!)
│   ├── server.crt / server.key # Server certificate
│   └── pico1.crt / pico1.key   # Device certificates
├── firmware/
│   ├── VERSION                 # Current firmware version
│   └── update.py               # Firmware binary
├── micropython/
│   └── update_client.py        # MicroPython OTA client code
├── tests/
│   └── test_update_server.py   # Unit tests
├── main.py                     # Main Pico application
├── update_server.py            # HTTP update server (legacy)
├── update_server_https.py      # HTTPS update server with auth
├── PipelineSetup.md            # Step-by-step setup guide
└── README.md                   # This file
```

## Quick Start

Follow these steps to get your OTA update system up and running in under 30 minutes.

### Step 1: Generate SSL Certificates

Generate the self-signed CA and device certificates:

```bash
cd /home/adam/Development/r-pi-pico-temperature/certificates
python generate_cert.py
```

This creates:
- `ca.crt` / `ca.key` - Certificate Authority (keep key secure!)
- `server.crt` / `server.key` - Server certificate for HTTPS
- `pico1.crt` / `pico1.key` - Sample device certificate

**IMPORTANT:** Never commit `.key` files to version control—they're already in `.gitignore`.

---

### Step 2: Configure Your Firmware

Edit `/home/adam/Development/r-pi-pico-temperature/main.py` with your actual credentials:

```python
# Update these lines (around line 13):
WIFI_SSID = "your_wifi_ssid"
WIFI_PASSWORD = "your_wifi_password"
UPDATE_SERVER_URL = "https://your-server-ip:8443/update"
FIRMWARE_VERSION = "1.0.0"
```

Also copy the CA certificate content into `main.py` for SSL verification:

```python
# Add after imports (around line 9):
CA_CERT = """-----BEGIN CERTIFICATE-----
(paste contents of certificates/ca.crt here)
-----END CERTIFICATE-----"""
```

---

### Step 3: Test the Update Server Locally

Start the HTTPS server to verify it works:

```bash
cd /home/adam/Development/r-pi-pico-temperature
python update_server_https.py
```

Expected output:
```
Secure OTA Update Server starting on port 8443
Firmware directory: firmware
CA Certificate: ../certificates/ca.crt
Server Certificate: ../certificates/server.crt
Available device certificates: ['pico1.crt']
Secure server running at https://localhost:8443
Client certificate authentication enabled
```

Test the API with your device certificate:

```bash
curl --cert pico1.crt --key pico1.key \
  https://localhost:8443/update/check?version=1.0.0
```

---

### Step 4: Set Up Git Repository and CI/CD

Initialize git and push to GitHub:

```bash
cd /home/adam/Development/r-pi-pico-temperature
git init
git add .
git commit -m "Initial OTA update setup"
git branch -M main
git remote add origin git@github.com:yourusername/r-pi-pico-temperature.git
git push -u origin main
```

**Configure GitHub Secrets:** Go to your repository → Settings → Secrets → Actions and add:

| Secret | Value |
|--------|-------|
| `FIRMWARE_SIGNING_KEY` | Copy contents of a signing private key |
| `AWS_ACCESS_KEY_ID` | Your AWS access key (if using S3) |
| `AWS_SECRET_ACCESS_KEY` | Your AWS secret key |
| `HTTP_SERVER_URL` | Your OTA server URL (e.g., https://your-server:8443) |

---

### Step 5: Deploy Your First Firmware Update

Create and push a deployment tag to trigger the CI/CD pipeline:

```bash
# Create firmware directory and version file
mkdir -p firmware
echo "1.0.0" > firmware/VERSION
cp main.py firmware/update.py

# Commit and tag for deployment
git add .
git commit -m "Release firmware v1.0.0"
git tag v1.0.0
git push origin v1.0.0
```

This triggers GitHub Actions to:
1. Run tests and linting
2. Sign the firmware with your private key
3. Deploy to your server or S3
4. Create a GitHub release

---

### Step 6: Flash Your Pico W

Using Thonny or Mu editor:

1. Connect Pico W via USB
2. Open `main.py` in your editor
3. Select "MicroPython (Raspberry Pi Pico)" as interpreter
4. Click **Save** to transfer to device
5. Click **Run** to execute

Your Pico W will now:
- Connect to WiFi
- Check for updates from your server via HTTPS
- Receive and verify signed firmware updates automatically

---

### Verify Everything Works

1. **Check pipeline status:** Go to GitHub → Actions tab to see the workflow run
2. **Watch device logs:** Open serial console on Pico W to see update check output
3. **Trigger an update:** Change `FIRMWARE_VERSION` to `1.0.1`, create new tag, and watch the device update

---

## Next Steps

- Read [`IMPLEMENTATION_STEPS.md`](IMPLEMENTATION_STEPS.md) for detailed 8-phase guide
- Review [`PipelineSetup.md`](PipelineSetup.md) for CI/CD configuration details
- Customize `main.py` with your actual temperature monitoring code

## Security Architecture

### Certificate Chain

```
                    ┌─────────────┐
                    │   CA Key    │ (Keep offline & secure)
                    └──────┬──────┘
                           │ Signs
                   ┌───────▼────────┐
                   │  Server Cert   │ (For HTTPS server)
                   └───────┬────────┘
                           │ Trusts
        ┌──────────────────┼──────────────────┐
        │                  │                  │
┌───────▼───────┐  ┌───────▼───────┐  ┌───────▼───────┐
│  Device Cert  │  │  Device Cert  │  │  Device Cert  │
│    (pico1)    │  │    (pico2)    │  │    (all)      │
└───────────────┘  └───────────────┘  └───────────────┘
```

### Update Flow

1. **Device boots** → Connects to WiFi
2. **HTTPS handshake** → Server presents certificate, verified against CA
3. **Client auth** → Device presents its certificate for authentication
4. **Update check** → Secure request to `/check?version=X&device=Y`
5. **Firmware download** → HTTPS transfer of signed firmware
6. **Signature verification** → Cryptographic signature validated
7. **Apply update** → New firmware installed, old backed up
8. **Reboot** → Device restarts with new firmware

### Signing Process (CI/CD)

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Firmware    │ --> │   Sign       │ --> │   Deploy     │
│  Code        │     │ (Private Key)│     │ (Server)     │
└──────────────┘     └──────────────┘     └──────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │   Signature  │
                    │   (.sig file)│
                    └──────────────┘
```

## GitHub Actions Pipeline

The pipeline in `.github/workflows/ota-deploy.yml` performs:

### On Push (Main Branch)
- ✅ Lint Python code
- ✅ Run unit tests
- ✅ Build firmware package
- ✅ Security scan (Bandit, Safety)

### On Tag (`v*`)
- ✅ Verify and test (depends on above)
- ✅ Sign firmware with private key
- ✅ Deploy to S3/HTTP server
- ✅ Create GitHub release
- ✅ Send deployment notifications

## Configuration Variables

Set these as GitHub Secrets for secure deployment:

| Secret | Description |
|--------|-------------|
| `FIRMWARE_SIGNING_KEY` | Private key for signing firmware |
| `AWS_ACCESS_KEY_ID` | AWS credentials for S3 deployment |
| `AWS_SECRET_ACCESS_KEY` | AWS secret access key |
| `AWS_S3_PATH` | S3 bucket path for firmware |
| `HTTP_SERVER_URL` | OTA server URL for HTTP deployment |
| `DEPLOYMENT_TOKEN` | Auth token for server API |
| `NOTIFICATION_WEBHOOK_URL` | Slack/Discord webhook for notifications |

## Testing Locally

```bash
# Install dependencies
pip install pytest pycodestyle cryptography boto3

# Run tests
pytest tests/ -v

# Start HTTPS server (requires certificates)
python update_server_https.py

# Test update check
curl -v --cert pico1.crt --key pico1.key \
  https://localhost:8443/update/check?version=1.0.0
```

## Troubleshooting

### Certificate Issues
```bash
# Verify certificate chain
openssl verify -CAfile ca.crt pico1.crt
openssl verify -CAfile ca.crt server.crt

# Check certificate expiry
openssl x509 -in server.crt -text -noout | grep -A 1 "Validity"
```

### Server Not Starting
```bash
# Check port availability
netstat -tlnp | grep 8443

# Verify certificates exist
ls -la certificates/
```

### Device Can't Connect
- Verify WiFi credentials in `main.py`
- Ensure device certificate is signed by your CA
- Check server is reachable from device's network

## Security Best Practices

1. **Protect Private Keys** - Never commit `.key` files, store in secure vaults
2. **Rotate Certificates** - Re-generate certificates periodically
3. **Use Strong Passwords** - For WiFi and server access
4. **Monitor Logs** - Watch for unauthorized access attempts
5. **Verify Signatures** - Always verify firmware before installation

## Resources

- [MicroPython Documentation](https://docs.micropython.org/)
- [Raspberry Pi Pico W Specs](https://www.raspberrypi.com/documentation/microcontrollers/raspberry-pi-pico.html)
- [OpenSSL Certificate Guide](https://www.openssl.org/docs/)
- [GitHub Actions Workflow Syntax](https://docs.github.com/en/actions)

## License

MIT License - See LICENSE file for details.

---

**Generated with Claude Code**
