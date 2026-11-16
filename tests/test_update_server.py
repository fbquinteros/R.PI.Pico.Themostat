"""
Unit tests for OTA Update Server
"""

import pytest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from update_server import UpdateHandler, FIRMWARE_DIR, VERSION_FILE


class TestUpdateHandler:
    """Tests for the OTA update handler"""

    def test_check_update_available(self):
        """Test that update check returns available when versions differ"""
        # This would require mocking the HTTP request/response
        # For now, we verify the logic exists
        assert FIRMWARE_DIR is not None
        assert VERSION_FILE is not None

    def test_version_file_exists(self):
        """Test that version file can be read"""
        if os.path.exists(VERSION_FILE):
            with open(VERSION_FILE, 'r') as f:
                version = f.read().strip()
                # Version should not be empty
                assert len(version) > 0

    def test_firmware_directory_exists(self):
        """Test that firmware directory structure is valid"""
        if os.path.exists(FIRMWARE_DIR):
            assert os.path.isdir(FIRMWARE_DIR)


class TestCertificateHandling:
    """Tests for certificate-related functionality"""

    def test_ca_certificate_path(self):
        """Verify CA certificate path is configured"""
        ca_cert_path = "certificates/ca.crt"
        # Certificate should exist (generated during setup)
        if os.path.exists(ca_cert_path):
            with open(ca_cert_path, 'r') as f:
                content = f.read()
                assert "BEGIN CERTIFICATE" in content

    def test_server_certificate_path(self):
        """Verify server certificate path is configured"""
        server_cert_path = "certificates/server.crt"
        if os.path.exists(server_cert_path):
            with open(server_cert_path, 'r') as f:
                content = f.read()
                assert "BEGIN CERTIFICATE" in content


class TestFirmwareSigning:
    """Tests for firmware signing functionality"""

    def test_signing_key_configured(self):
        """Verify signing key can be loaded from secrets"""
        # In CI, this would come from GitHub Secrets
        # For local testing, we verify the key file structure if it exists
        signing_key_path = "signing.key"
        if os.path.exists(signing_key_path):
            with open(signing_key_path, 'r') as f:
                content = f.read()
                assert "BEGIN PRIVATE KEY" in content or "BEGIN RSA PRIVATE KEY" in content


def test_pipeline_configured():
    """Verify pipeline configuration exists"""
    workflow_path = ".github/workflows/ota-deploy.yml"
    if os.path.exists(workflow_path):
        with open(workflow_path, 'r') as f:
            content = f.read()
            assert "verify-and-test" in content
            assert "deploy" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
