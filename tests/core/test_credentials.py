# Assisted by WCA@IBM
# Latest GenAI contribution: ibm/granite-8b-code-instruct
import unittest
from ibm_watsonx_orchestrate.client.credentials import Credentials

class TestCredentials(unittest.TestCase):
    def test_init(self):
        credentials = Credentials(url="https://example.com", api_key="1234567890")
        self.assertEqual(credentials.url, "https://example.com")
        self.assertEqual(credentials.api_key, "1234567890")
        self.assertIsNone(credentials.token)
        self.assertIsNone(credentials.verify)

    def test_from_dict(self):
        credentials = Credentials.from_dict(
            {"url": "https://example.com", "api_key": "1234567890"}
        )
        self.assertEqual(credentials.url, "https://example.com")
        self.assertEqual(credentials.api_key, "1234567890")
        self.assertIsNone(credentials.token)
        self.assertIsNone(credentials.verify)

    def test_to_dict(self):
        credentials = Credentials(url="https://example.com", api_key="1234567890")
        self.assertEqual(
            credentials.to_dict(),
            {"url": "https://example.com", "api_key": "1234567890"},
        )

    def test_getitem(self):
        credentials = Credentials(url="https://example.com", api_key="1234567890")
        self.assertEqual(credentials["api_key"], "1234567890")

    def test_get(self):
        credentials = Credentials(url="https://example.com", api_key="1234567890")
        self.assertEqual(credentials.get("api_key"), "1234567890")
        self.assertEqual(credentials.get("api_key", "default"), "1234567890")
        self.assertEqual(credentials.get("token"), None)
        self.assertEqual(credentials.get("token", "default"), "default")


if __name__ == "__main__":
    unittest.main()