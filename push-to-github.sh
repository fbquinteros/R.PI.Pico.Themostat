#!/bin/bash
# Push firmware updates to GitHub
# Run this script after making changes to push to your repository

echo "=== Pushing to GitHub ==="
echo ""

# Stage all changed files
git add config.py .gitignore main.py wifi_config_api.md

# Commit with a descriptive message
git commit -m "Add WiFi configuration REST API with persistent storage

- Add API settings to config.py (port, timeout, credentials file)
- Implement HTTP server in AP mode for WiFi configuration
- Add /api/wifi endpoint that accepts POST JSON with ssid/password
- Save credentials to wifi_config.json on device flash
- Auto-load saved credentials on boot, overriding config.py defaults
- Attempt WiFi connection after receiving credentials via API
- Reboot device on successful connection
- Update .gitignore to include wifi_config.json
- Add documentation for the REST API"

# Push to GitHub
git push origin main

echo ""
echo "=== Done! ==="
