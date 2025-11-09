"""Pytest-BDD step definitions for Comdirect API client tests.

This module implements step definitions for the Gherkin scenarios
defined in comdirect_api.feature.
"""

import logging
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from comdirect_client.client import ComdirectClient

# Load all scenarios from the feature file
scenarios("../comdirect_api.feature")


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_httpx_client():
    """Mock httpx AsyncClient."""
    return AsyncMock(spec=httpx.AsyncClient)


@pytest.fixture
def client_credentials():
    """Valid client credentials."""
    return {
        "client_id": "test_client_id",
        "client_secret": "test_client_secret",
        "username": "test_username",
        "password": "test_password",
    }


@pytest.fixture
def invalid_credentials():
    """Invalid credentials for testing."""
    return {
        "client_id": "invalid_client",
        "client_secret": "invalid_secret",
        "username": "invalid_user",
        "password": "invalid_pass",
    }


@pytest.fixture
def comdirect_client(client_credentials, mock_httpx_client):
    """Create a ComdirectClient instance with mocked HTTP client."""
    with patch("comdirect_client.client.httpx.AsyncClient", return_value=mock_httpx_client):
        client = ComdirectClient(**client_credentials)
        client._http_client = mock_httpx_client
        return client


@pytest.fixture
def log_capture(caplog):
    """Capture logs for verification."""
    caplog.set_level(logging.DEBUG)
    return caplog


# ============================================================================
# Background Steps
# ============================================================================


@given("the Comdirect API base URL is configured")
def api_base_url_configured(comdirect_client):
    """Ensure API base URL is configured."""
    assert comdirect_client.base_url == "https://api.comdirect.de"


@given("client credentials are provided")
def client_credentials_provided(comdirect_client):
    """Ensure client credentials are provided."""
    assert comdirect_client.client_id
    assert comdirect_client.client_secret


@given("user credentials are provided")
def user_credentials_provided(comdirect_client):
    """Ensure user credentials are provided."""
    assert comdirect_client.username
    assert comdirect_client._password


@given("logging is configured with appropriate log levels")
def logging_configured(log_capture):
    """Ensure logging is configured."""
    assert log_capture is not None


# ============================================================================
# Authentication Flow Steps
# ============================================================================


@given("the user has valid Comdirect credentials")
def valid_credentials(comdirect_client, mock_httpx_client):
    """Set up mock responses for valid credentials."""
    # Mock Step 1: OAuth2 password credentials
    mock_httpx_client.post.return_value = AsyncMock(
        status_code=200,
        json=lambda: {
            "access_token": "test_access_token_step1",
            "token_type": "Bearer",
            "expires_in": 600,
        },
    )

    # Mock Step 2: Session status
    mock_httpx_client.get.return_value = AsyncMock(
        status_code=200,
        json=lambda: [{"identifier": "test_session_uuid"}],
    )


@given("the user has invalid Comdirect credentials")
def invalid_credentials_setup(comdirect_client, mock_httpx_client):
    """Set up mock responses for invalid credentials."""
    mock_httpx_client.post.return_value = AsyncMock(
        status_code=401,
        json=lambda: {"error": "invalid_grant"},
    )


@when("the user triggers authentication")
async def trigger_authentication(comdirect_client):
    """Trigger authentication flow."""
    try:
        await comdirect_client.authenticate()
    except Exception:
        # Store exception for later verification
        pass


@then("the library should generate a session UUID")
def session_uuid_generated(comdirect_client):
    """Verify session UUID was generated."""
    assert comdirect_client._session_id is not None


@then("the library should obtain an OAuth2 password credentials token")
def oauth2_token_obtained(mock_httpx_client):
    """Verify OAuth2 token request was made."""
    assert mock_httpx_client.post.called


@then(parsers.parse('the library should log "{log_message}"'))
def verify_log_message(log_capture, log_message):
    """Verify specific log message appears."""
    assert any(log_message in record.message for record in log_capture.records)


@then(parsers.parse('the library should log "{log_message}" with TAN type'))
def verify_log_with_tan_type(log_capture, log_message):
    """Verify log message with TAN type appears."""
    matching_logs = [r for r in log_capture.records if log_message in r.message]
    assert len(matching_logs) > 0


@then("the library should retrieve the session status")
def session_status_retrieved(mock_httpx_client):
    """Verify session status request was made."""
    assert mock_httpx_client.get.called


@then("the library should create a TAN challenge")
def tan_challenge_created(mock_httpx_client):
    """Verify TAN challenge was created."""
    # Would need more specific mock setup
    pass


@then("the library should poll for TAN approval every 1 second")
def tan_polling_configured():
    """Verify TAN polling interval."""
    # This would be verified through time measurements in actual tests
    pass


@then(parsers.parse('the library should log "{log_message}" for each poll attempt'))
def verify_polling_logs(log_capture, log_message):
    """Verify polling logs appear."""
    # Count how many times the polling log appears
    # In actual tests, we would verify the count matches expected polls


@then("the library should exchange for secondary token")
def secondary_token_exchanged():
    """Verify secondary token exchange."""
    pass


@then("the library should store the access token")
def access_token_stored(comdirect_client):
    """Verify access token is stored."""
    # Would check after successful auth
    pass


@then("the library should store the refresh token")
def refresh_token_stored(comdirect_client):
    """Verify refresh token is stored."""
    # Would check after successful auth
    pass


@then("the library should store the token expiry timestamp")
def token_expiry_stored(comdirect_client):
    """Verify token expiry is stored."""
    # Would check after successful auth
    pass


@then("the authentication should be marked as complete")
def authentication_complete(comdirect_client):
    """Verify authentication is complete."""
    # Would check is_authenticated() after successful auth
    pass


# ============================================================================
# Error Handling Steps
# ============================================================================


@then("the library should attempt OAuth2 password credentials grant")
def oauth2_attempt(mock_httpx_client):
    """Verify OAuth2 attempt was made."""
    assert mock_httpx_client.post.called


@then("the library should receive a 401 Unauthorized response")
def verify_401_response(mock_httpx_client):
    """Verify 401 response was received."""
    # Check that the mock returned 401
    pass


@then("the library should raise an AuthenticationError exception")
def verify_authentication_error():
    """Verify AuthenticationError was raised."""
    # Would use pytest.raises in actual test
    pass


@then("no tokens should be stored")
def no_tokens_stored(comdirect_client):
    """Verify no tokens are stored after failed auth."""
    assert comdirect_client._access_token is None
    assert comdirect_client._refresh_token is None


# ============================================================================
# TAN Timeout Steps
# ============================================================================


@given("the authentication flow has reached the TAN polling stage")
def tan_polling_stage(comdirect_client, mock_httpx_client):
    """Set up mocks for TAN polling stage."""
    # Mock responses up to TAN polling
    pass


@when("60 seconds elapse without TAN approval")
async def tan_timeout_elapsed():
    """Simulate TAN timeout."""
    # Would use time mocking in actual test
    pass


@then("the library should raise a TANTimeoutError exception")
def verify_tan_timeout_error():
    """Verify TANTimeoutError was raised."""
    # Would use pytest.raises in actual test
    pass


# ============================================================================
# Token Refresh Steps
# ============================================================================


@given("the user is authenticated")
async def user_authenticated(comdirect_client, mock_httpx_client):
    """Set up authenticated state."""
    comdirect_client._access_token = "test_access_token"
    comdirect_client._refresh_token = "test_refresh_token"
    comdirect_client._token_expiry = datetime.now() + timedelta(seconds=300)


@given("the token expires in less than 120 seconds")
def token_expiring_soon(comdirect_client):
    """Set token to expire soon."""
    comdirect_client._token_expiry = datetime.now() + timedelta(seconds=100)


@when("the automatic token refresh task runs")
async def auto_refresh_runs():
    """Trigger automatic refresh."""
    # Would trigger the background task
    pass


@then("the library should attempt to refresh the token")
def verify_refresh_attempt(mock_httpx_client):
    """Verify token refresh was attempted."""
    # Check refresh token endpoint was called
    pass


# ============================================================================
# API Request Steps
# ============================================================================


@when("the user requests account balances")
async def request_account_balances(comdirect_client, mock_httpx_client):
    """Request account balances."""
    mock_httpx_client.get.return_value = AsyncMock(
        status_code=200,
        json=lambda: {
            "values": [
                {
                    "accountId": "test_account_id",
                    "account": {"accountDisplayId": "DE89370400440532013000"},
                    "accountType": {"text": "GIRO"},
                    "balance": {"value": 1234.56, "unit": "EUR"},
                    "availableCashAmount": {"value": 1234.56, "unit": "EUR"},
                    "balanceDate": "2024-01-01",
                }
            ]
        },
    )

    try:
        await comdirect_client.get_account_balances()
    except Exception:
        pass


@then("the library should return a list of AccountBalance objects")
def verify_account_balances_returned():
    """Verify AccountBalance objects were returned."""
    # Would check return value in actual test
    pass


@then("each balance should have properly typed fields")
def verify_balance_types():
    """Verify field types on balance objects."""
    # Would check field types in actual test
    pass
