# Certificates

**IMPORTANT: Do not commit these files to git!**

This directory contains SSL/TLS certificates for the OTA update server. All files in this directory are excluded from git tracking via `.gitignore`.

## Files

- `ca.crt` - CA public certificate (for client verification of server)
- `ca.key` - CA private key (**KEEP SECRET** - used for signing firmware)
- `server.crt` - Server certificate (signed by CA)
- `server.key` - Server private key (**KEEP SECRET**)
- `pico1.crt` - Device 1 certificate (signed by CA)
- `pico1.key` - Device 1 private key (**KEEP SECRET**)
- `pico2.crt` - Device 2 certificate (signed by CA)
- `pico2.key` - Device 2 private key (**KEEP SECRET**)

## For Pico Deployment

When deploying firmware to the Pico W:
1. Copy `ca.crt` to the Pico as `ca.crt` (for HTTPS verification)
2. This file is needed for the Pico to verify the OTA server's identity

```bash
# Example: Copy ca.crt to Pico using Thonny or mpremote
mpremote cp ca.crt pico:ca.crt
```

## Regenerating Certificates

If you need to regenerate the certificates:

```bash
# Generate CA key and certificate
openssl req -x509 -newkey rsa:4096 -keyout ca.key -out ca.crt -days 3650 -nodes -subj "/C=US/ST=State/L=City/O=YourOrg/CN=PicoWOTA-CA"

# Generate server certificate
openssl req -newkey rsa:4096 -nodes -keyout server.key -out server.csr -subj "/C=US/ST=State/L=City/O=YourOrg/CN=ota-server"
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -set_serial 1 -out server.crt -days 365

# Generate device certificates
for device in pico1 pico2; do
    openssl req -newkey rsa:4096 -nodes -keyout ${device}.key -out ${device}.csr -subj "/C=US/ST=State/L=City/O=YourOrg/CN=${device}"
    openssl x509 -req -in ${device}.csr -CA ca.crt -CAkey ca.key -set_serial $((RANDOM % 1000 + 1)) -out ${device}.crt -days 365
done
```
