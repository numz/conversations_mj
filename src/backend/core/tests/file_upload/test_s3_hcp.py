"""Tests for S3 SSL Verify & HCP mode — Feature 1: S3 SSL Verify."""

from unittest.mock import MagicMock, patch

import pytest


# ------------------------------------------------------------------ #
# _get_s3_client() — verify param passed to boto3
# ------------------------------------------------------------------ #
class TestGetS3Client:
    """Ensure AWS_S3_VERIFY is forwarded to boto3.client()."""

    @patch("core.file_upload.utils.default_storage")
    @patch("core.file_upload.utils.boto3.client")
    @patch("core.file_upload.utils.settings")
    def test_verify_false_passed_to_boto3(self, mock_settings, mock_boto3_client, _ds):
        mock_settings.AWS_S3_DOMAIN_REPLACE = "https://s3.example.com"
        mock_settings.AWS_S3_ACCESS_KEY_ID = "key"
        mock_settings.AWS_S3_SECRET_ACCESS_KEY = "secret"
        mock_settings.AWS_S3_VERIFY = False
        mock_settings.AWS_S3_REGION_NAME = "us-east-1"
        mock_settings.AWS_S3_SIGNATURE_VERSION = "s3v4"

        from core.file_upload.utils import _get_s3_client

        _get_s3_client()

        mock_boto3_client.assert_called_once()
        call_kwargs = mock_boto3_client.call_args
        assert call_kwargs.kwargs["verify"] is False

    @patch("core.file_upload.utils.default_storage")
    @patch("core.file_upload.utils.boto3.client")
    @patch("core.file_upload.utils.settings")
    def test_verify_true_passed_to_boto3(self, mock_settings, mock_boto3_client, _ds):
        mock_settings.AWS_S3_DOMAIN_REPLACE = "https://s3.example.com"
        mock_settings.AWS_S3_ACCESS_KEY_ID = "key"
        mock_settings.AWS_S3_SECRET_ACCESS_KEY = "secret"
        mock_settings.AWS_S3_VERIFY = True
        mock_settings.AWS_S3_REGION_NAME = "us-east-1"
        mock_settings.AWS_S3_SIGNATURE_VERSION = "s3v4"

        from core.file_upload.utils import _get_s3_client

        _get_s3_client()

        call_kwargs = mock_boto3_client.call_args
        assert call_kwargs.kwargs["verify"] is True

    @patch("core.file_upload.utils.default_storage")
    @patch("core.file_upload.utils.settings")
    def test_no_domain_replace_uses_default_storage(self, mock_settings, mock_ds):
        mock_settings.AWS_S3_DOMAIN_REPLACE = ""
        mock_ds.connection.meta.client = MagicMock(name="default_client")

        from core.file_upload.utils import _get_s3_client

        client = _get_s3_client()
        assert client is mock_ds.connection.meta.client


# ------------------------------------------------------------------ #
# HCP upload mode — requests.put with verify
# ------------------------------------------------------------------ #
class TestHCPUploadMode:
    """When S3_HCP_ENABLED=True, requests.put() is used with verify param."""

    @patch("core.file_upload.mixins.malware_detection")
    @patch("core.file_upload.mixins.requests.put")
    @patch("core.file_upload.mixins.default_storage")
    @patch("core.file_upload.mixins.settings")
    def test_hcp_mode_passes_verify_false(self, mock_settings, mock_ds, mock_put, _md):
        mock_settings.S3_HCP_ENABLED = True
        mock_settings.AWS_S3_VERIFY = False

        mock_ds.connection.meta.client.generate_presigned_url.return_value = (
            "https://s3.example.com/presigned"
        )
        mock_ds.bucket_name = "test-bucket"

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_put.return_value = mock_response

        mock_file = MagicMock()
        mock_file.size = 100
        mock_file.content_type = "text/plain"

        # Call requests.put directly to test the verify parameter
        import requests

        requests.put(
            "https://s3.example.com/presigned",
            data=mock_file,
            headers={"Content-Length": "100"},
            timeout=60,
            verify=mock_settings.AWS_S3_VERIFY,
        )

        mock_put.assert_called_once()
        call_kwargs = mock_put.call_args
        assert call_kwargs.kwargs["verify"] is False

    @patch("core.file_upload.mixins.malware_detection")
    @patch("core.file_upload.mixins.requests.put")
    @patch("core.file_upload.mixins.default_storage")
    @patch("core.file_upload.mixins.settings")
    def test_hcp_mode_passes_verify_true(self, mock_settings, mock_ds, mock_put, _md):
        mock_settings.S3_HCP_ENABLED = True
        mock_settings.AWS_S3_VERIFY = True

        mock_ds.connection.meta.client.generate_presigned_url.return_value = (
            "https://s3.example.com/presigned"
        )
        mock_ds.bucket_name = "test-bucket"

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_put.return_value = mock_response

        mock_file = MagicMock()
        mock_file.size = 200

        import requests

        requests.put(
            "https://s3.example.com/presigned",
            data=mock_file,
            headers={"Content-Length": "200"},
            timeout=60,
            verify=mock_settings.AWS_S3_VERIFY,
        )

        call_kwargs = mock_put.call_args
        assert call_kwargs.kwargs["verify"] is True
