"""Comprehensive tests for the redact_sensitive_keys function.

This test suite validates the redact_sensitive_keys function which is used to
sanitize sensitive information from data structures before logging or tracing.
"""

import json
import pytest

from ibm_watsonx_orchestrate_sdk.observability.constants import REDACTED
from ibm_watsonx_orchestrate_sdk.observability.decorators import redact_sensitive_keys


class TestRedactSensitiveKeysBasicFunctionality:
    """Tests for basic redaction functionality."""

    def test_redacts_password_in_dict(self):
        """Password keys should be redacted."""
        data = {"username": "john", "password": "secret123"}
        result = redact_sensitive_keys(data)
        assert result["username"] == "john"
        assert result["password"] == REDACTED

    def test_redacts_api_key_in_dict(self):
        """API key fields should be redacted."""
        data = {"endpoint": "https://api.example.com", "api_key": "abc123"}
        result = redact_sensitive_keys(data)
        assert result["endpoint"] == "https://api.example.com"
        assert result["api_key"] == REDACTED

    def test_redacts_token_in_dict(self):
        """Token fields should be redacted."""
        data = {"user": "alice", "auth_token": "xyz789"}
        result = redact_sensitive_keys(data)
        assert result["user"] == "alice"
        assert result["auth_token"] == REDACTED

    def test_redacts_multiple_sensitive_keys(self):
        """Multiple sensitive keys should all be redacted."""
        data = {
            "username": "bob",
            "password": "pass123",
            "api_key": "key456",
            "bearer_token": "token789"
        }
        result = redact_sensitive_keys(data)
        assert result["username"] == "bob"
        assert result["password"] == REDACTED
        assert result["api_key"] == REDACTED
        assert result["bearer_token"] == REDACTED

    def test_preserves_non_sensitive_keys(self):
        """Non-sensitive keys should remain unchanged."""
        data = {
            "username": "alice",
            "email": "alice@example.com",
            "age": 30,
            "active": True
        }
        result = redact_sensitive_keys(data)
        assert result == data


class TestRedactSensitiveKeysNestedStructures:
    """Tests for handling nested data structures."""

    def test_handles_nested_dict(self):
        """Sensitive keys in nested dicts should be redacted.
        
        NOTE: There's a known limitation where if a parent key matches a sensitive
        pattern (like 'credentials'), the entire value is redacted rather than
        recursively processing nested keys.
        """
        data = {
            "user": "charlie",
            "credentials": {
                "password": "secret",
                "api_key": "key123"
            }
        }
        result = redact_sensitive_keys(data)
        assert result["user"] == "charlie"
        # Known limitation: 'credentials' key causes entire dict to be redacted
        assert result["credentials"] == REDACTED

    def test_handles_list_of_dicts(self):
        """Sensitive keys in list items should be redacted."""
        data = [
            {"name": "user1", "password": "pass1"},
            {"name": "user2", "api_key": "key2"}
        ]
        result = redact_sensitive_keys(data)
        assert result[0]["name"] == "user1"
        assert result[0]["password"] == REDACTED
        assert result[1]["name"] == "user2"
        assert result[1]["api_key"] == REDACTED

    def test_handles_dict_with_list_values(self):
        """Sensitive keys in nested structures with lists should be redacted."""
        data = {
            "users": [
                {"username": "alice", "password": "secret1"},
                {"username": "bob", "token": "token123"}
            ]
        }
        result = redact_sensitive_keys(data)
        assert result["users"][0]["username"] == "alice"
        assert result["users"][0]["password"] == REDACTED
        assert result["users"][1]["username"] == "bob"
        assert result["users"][1]["token"] == REDACTED

    def test_handles_tuple(self):
        """Tuples containing dicts with sensitive keys should be handled."""
        data = ({"password": "secret"}, {"api_key": "key123"})
        result = redact_sensitive_keys(data)
        assert isinstance(result, tuple)
        assert result[0]["password"] == REDACTED
        assert result[1]["api_key"] == REDACTED

    def test_deeply_nested_structure(self):
        """Sensitive keys in deeply nested structures should be redacted."""
        data = {
            "level1": {
                "level2": {
                    "level3": {
                        "password": "deep_secret",
                        "data": "safe_value"
                    }
                }
            }
        }
        result = redact_sensitive_keys(data)
        assert result["level1"]["level2"]["level3"]["password"] == REDACTED
        assert result["level1"]["level2"]["level3"]["data"] == "safe_value"

    def test_preserves_nested_non_sensitive_data(self):
        """Nested structures with non-sensitive data should be preserved."""
        data = {
            "user": {
                "name": "John",
                "email": "john@example.com",
                "profile": {
                    "age": 30,
                    "city": "NYC"
                }
            }
        }
        result = redact_sensitive_keys(data)
        assert result == data


class TestRedactSensitiveKeysKeyMatching:
    """Tests for key matching behavior."""

    def test_case_insensitive_matching(self):
        """Sensitive key matching should be case-insensitive."""
        data = {
            "PASSWORD": "secret1",
            "Password": "secret2",
            "ApiKey": "key123",
            "API_KEY": "key456"
        }
        result = redact_sensitive_keys(data)
        assert result["PASSWORD"] == REDACTED
        assert result["Password"] == REDACTED
        assert result["ApiKey"] == REDACTED
        assert result["API_KEY"] == REDACTED

    def test_handles_hyphenated_keys(self):
        """Hyphenated sensitive keys should be redacted."""
        data = {
            "api-key": "key123",
            "auth-token": "token456",
            "bearer-token": "bearer789"
        }
        result = redact_sensitive_keys(data)
        assert result["api-key"] == REDACTED
        assert result["auth-token"] == REDACTED
        assert result["bearer-token"] == REDACTED

    def test_redacts_secret_variations(self):
        """Various forms of 'secret' keys should be redacted."""
        data = {
            "client_secret": "secret1",
            "secret_key": "secret2",
            "my_secret": "secret3"
        }
        result = redact_sensitive_keys(data)
        assert result["client_secret"] == REDACTED
        assert result["secret_key"] == REDACTED
        assert result["my_secret"] == REDACTED

    def test_redacts_credential_variations(self):
        """Various forms of 'credential' keys should be redacted."""
        data = {
            "credentials": "cred1",
            "user_credential": "cred2",
            "credential_id": "cred3"
        }
        result = redact_sensitive_keys(data)
        assert result["credentials"] == REDACTED
        assert result["user_credential"] == REDACTED
        assert result["credential_id"] == REDACTED


class TestRedactSensitiveKeysDataTypes:
    """Tests for handling different data types."""

    def test_handles_json_string_input(self):
        """JSON strings should be parsed and sensitive keys redacted."""
        json_str = '{"username": "john", "password": "secret123"}'
        result = redact_sensitive_keys(json_str)
        assert result["username"] == "john"
        assert result["password"] == REDACTED

    def test_handles_invalid_json_string(self):
        """Invalid JSON strings should be returned as-is."""
        invalid_json = "not a json string"
        result = redact_sensitive_keys(invalid_json)
        assert result == "not a json string"

    def test_handles_none_values(self):
        """None values in sensitive keys should still be redacted."""
        data = {"username": "john", "password": None}
        result = redact_sensitive_keys(data)
        assert result["username"] == "john"
        assert result["password"] == REDACTED

    def test_handles_numeric_values(self):
        """Numeric values in sensitive keys should be redacted."""
        data = {
            "user_id": 12345,
            "password": 98765,
            "age": 30
        }
        result = redact_sensitive_keys(data)
        assert result["user_id"] == 12345
        assert result["password"] == REDACTED
        assert result["age"] == 30

    def test_handles_boolean_values(self):
        """Boolean values in sensitive keys should be redacted.
        
        NOTE: Keys containing sensitive substrings are also redacted, so
        'has_password' is redacted because it contains 'password'.
        """
        data = {
            "is_active": True,
            "has_password": False,
            "password": "secret"
        }
        result = redact_sensitive_keys(data)
        assert result["is_active"] is True
        # 'has_password' is redacted because it contains 'password'
        assert result["has_password"] == REDACTED
        assert result["password"] == REDACTED

    def test_handles_empty_dict(self):
        """Empty dict should remain empty."""
        data = {}
        result = redact_sensitive_keys(data)
        assert result == {}

    def test_handles_empty_list(self):
        """Empty list should remain empty."""
        data = []
        result = redact_sensitive_keys(data)
        assert result == []


class TestRedactSensitiveKeysSpecificPatterns:
    """Tests for specific sensitive patterns from SENSITIVE_KEY_PATTERNS."""

    def test_redacts_jwt_token(self):
        """JWT tokens should be redacted."""
        data = {
            "jwt": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
            "jwt_token": "token123"
        }
        result = redact_sensitive_keys(data)
        assert result["jwt"] == REDACTED
        assert result["jwt_token"] == REDACTED

    def test_redacts_session_cookie(self):
        """Session and cookie fields should be redacted."""
        data = {
            "session_id": "sess123",
            "cookie": "cookie_value",
            "csrf_token": "csrf123"
        }
        result = redact_sensitive_keys(data)
        assert result["session_id"] == REDACTED
        assert result["cookie"] == REDACTED
        assert result["csrf_token"] == REDACTED

    def test_redacts_private_key(self):
        """Private and access keys should be redacted."""
        data = {
            "private_key": "-----BEGIN PRIVATE KEY-----",
            "access_key": "AKIAIOSFODNN7EXAMPLE"
        }
        result = redact_sensitive_keys(data)
        assert result["private_key"] == REDACTED
        assert result["access_key"] == REDACTED

    def test_redacts_connection_string(self):
        """Connection strings should be redacted."""
        data = {
            "connection_string": "mongodb://user:pass@localhost:27017",
            "database_url": "postgres://user:pass@localhost:5432/db"
        }
        result = redact_sensitive_keys(data)
        assert result["connection_string"] == REDACTED
        # database_url should not be redacted as it doesn't match patterns
        assert result["database_url"] == "postgres://user:pass@localhost:5432/db"

    @pytest.mark.parametrize("key_name,value", [
        ("token", "value"),
        ("auth_token", "value"),
        ("bearer_token", "value"),
        ("access_token", "value"),
    ])
    def test_token_patterns(self, key_name, value):
        """All token-related keys should be redacted."""
        data = {key_name: value}
        result = redact_sensitive_keys(data)
        assert result[key_name] == REDACTED

    @pytest.mark.parametrize("key_name,value", [
        ("secret", "value"),
        ("client_secret", "value"),
        ("api_secret", "value"),
    ])
    def test_secret_patterns(self, key_name, value):
        """All secret-related keys should be redacted."""
        data = {key_name: value}
        result = redact_sensitive_keys(data)
        assert result[key_name] == REDACTED

    @pytest.mark.parametrize("key_name,value", [
        ("password", "value"),
        ("passwd", "value"),
        ("pwd", "value"),
        ("user_password", "value"),
    ])
    def test_password_patterns(self, key_name, value):
        """All password-related keys should be redacted."""
        data = {key_name: value}
        result = redact_sensitive_keys(data)
        assert result[key_name] == REDACTED

    @pytest.mark.parametrize("key_name,value", [
        ("api_key", "value"),
        ("apikey", "value"),
        ("access_key", "value"),
        ("private_key", "value"),
        ("license_key", "value"),
    ])
    def test_key_patterns(self, key_name, value):
        """All key-related fields should be redacted."""
        data = {key_name: value}
        result = redact_sensitive_keys(data)
        assert result[key_name] == REDACTED

    @pytest.mark.parametrize("key_name,value", [
        ("auth", "value"),
        ("authorization", "value"),
        ("authenticate", "value"),
    ])
    def test_auth_patterns(self, key_name, value):
        """All auth-related keys should be redacted."""
        data = {key_name: value}
        result = redact_sensitive_keys(data)
        assert result[key_name] == REDACTED

    @pytest.mark.parametrize("key_name,value", [
        ("credential", "value"),
        ("credentials", "value"),
        ("user_credential", "value"),
    ])
    def test_credential_patterns(self, key_name, value):
        """All credential-related keys should be redacted."""
        data = {key_name: value}
        result = redact_sensitive_keys(data)
        assert result[key_name] == REDACTED


class TestRedactSensitiveKeysEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_preserves_original_data_structure(self):
        """Ensure the function doesn't mutate the original data."""
        original = {"username": "john", "password": "secret"}
        original_copy = original.copy()
        redact_sensitive_keys(original)
        assert original == original_copy

    def test_handles_list_of_non_sensitive_dicts(self):
        """Lists of dicts with non-sensitive data should be preserved."""
        data = [
            {"name": "user1", "email": "user1@example.com"},
            {"name": "user2", "email": "user2@example.com"}
        ]
        result = redact_sensitive_keys(data)
        assert result == data

    def test_mixed_nested_structures(self):
        """Complex nested structures with sensitive keys should be handled.
        
        NOTE: There's a known limitation where if a parent key matches a sensitive
        pattern (like 'auth'), the entire value is redacted rather than recursively
        processing nested keys.
        """
        data = {
            "users": [
                {
                    "name": "alice",
                    "auth": {
                        "password": "secret1",
                        "tokens": ["token1", "token2"]
                    }
                }
            ]
        }
        result = redact_sensitive_keys(data)
        assert result["users"][0]["name"] == "alice"
        # Known limitation: 'auth' key causes entire dict to be redacted
        assert result["users"][0]["auth"] == REDACTED

    def test_handles_special_characters_in_values(self):
        """Values with special characters should be properly redacted."""
        data = {
            "username": "user@example.com",
            "password": "p@$$w0rd!#$%",
            "api_key": "key-with-dashes-123"
        }
        result = redact_sensitive_keys(data)
        assert result["username"] == "user@example.com"
        assert result["password"] == REDACTED
        assert result["api_key"] == REDACTED
