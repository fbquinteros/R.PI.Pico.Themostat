# Makefile for OTA Update Pipeline
# Quick commands for common tasks

.PHONY: all setup certs test lint deploy clean help

.DEFAULT_GOAL := help

help:
	@echo "OTA Update Pipeline - Available Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make setup          - Install dependencies"
	@echo "  make certs          - Generate SSL certificates"
	@echo ""
	@echo "Testing:"
	@echo "  make test           - Run all tests"
	@echo "  make lint           - Check code style"
	@echo "  make security       - Run security scans"
	@echo ""
	@echo "Development:"
	@echo "  make server         - Start HTTPS update server"
	@echo "  make dev-server     - Start HTTP server (no SSL)"
	@echo "  make build          - Build firmware package"
	@echo ""
	@echo "Deployment:"
	@echo "  make deploy TAG=v1.0.0 - Deploy with specific tag"
	@echo "  make sign             - Sign firmware manually"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean            - Clean build artifacts"
	@echo "  make verify-certs     - Verify certificate chain"

setup:
	@echo "Installing dependencies..."
	python -m pip install --upgrade pip
	pip install -r requirements.txt

certs:
	@echo "Generating certificates..."
	cd certificates && python generate_cert.py

test:
	@echo "Running tests..."
	pytest tests/ -v --tb=short

lint:
	@echo "Checking code style..."
	pycodestyle update_server.py update_server_https.py main.py

security:
	@echo "Running security scans..."
	bandit -r update_server.py main.py
	safety check

server:
	@echo "Starting HTTPS server on port 8443..."
	python update_server_https.py

dev-server:
	@echo "Starting HTTP server on port 8080..."
	python update_server.py

build:
	@echo "Building firmware package..."
	mkdir -p dist/firmware
	cp main.py dist/firmware/update.py
	echo "$(shell cat firmware/VERSION 2>/dev/null || echo '1.0.0')" > dist/firmware/VERSION
	tar -czf dist/firmware-package.tar.gz -C dist firmware/
	@echo "Build complete: dist/firmware-package.tar.gz"

deploy:
ifndef TAG
	$(error TAG is required. Usage: make deploy TAG=v1.0.0)
endif
	@echo "Deploying version $(TAG)..."
	git tag -d $(TAG) 2>/dev/null || true
	git tag $(TAG)
	git push origin $(TAG)
	@echo "Tag pushed - GitHub Actions will trigger deployment"

sign:
	@echo "Signing firmware..."
	python << 'PYTHON_SCRIPT'
import base64
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

# Load private key (ensure signing.key exists)
try:
    with open("signing.key", "rb") as f:
        private_key = serialization.load_pem_private_key(f.read(), password=None)

    # Sign firmware file
    with open("firmware/update.py", "rb") as f:
        firmware_data = f.read()

    signature = private_key.sign(
        firmware_data,
        padding.PKCS1v15(),
        hashes.SHA256()
    )

    # Save signature
    with open("firmware/update.py.sig", "wb") as f:
        f.write(base64.b64encode(signature))

    print("Firmware signed successfully: firmware/update.py.sig")
except FileNotFoundError:
    print("Error: signing.key not found. Generate one first.")
PYTHON_SCRIPT

clean:
	@echo "Cleaning build artifacts..."
	rm -rf dist/
	rm -rf __pycache__/
	rm -rf .pytest_cache/
	rm -rf *.egg-info/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@echo "Clean complete"

verify-certs:
	@echo "Verifying certificate chain..."
	openssl verify -CAfile certificates/ca.crt certificates/server.crt
	openssl verify -CAfile certificates/ca.crt certificates/pico1.crt
	@echo "Certificate verification complete"

install-hooks:
	@echo "Setting up git hooks..."
	mkdir -p .git/hooks
	cp scripts/pre-commit .git/hooks/ 2>/dev/null || echo "No pre-commit script found"
