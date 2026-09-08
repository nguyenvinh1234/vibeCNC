import unittest
from types import SimpleNamespace
from unittest.mock import patch

from vibe_cnc.claude_client import AIClient


def make_settings(mode="anthropic", offline=False, profile="MACH3TURN_XHC_MKX_ET"):
    return SimpleNamespace(
        data={
            "machine": {"profile": profile} if profile else {},
            "ai": {
                "mode": mode,
                "offline": offline,
                "anthropic": {
                    "base_url": "https://example.invalid/v1/messages",
                    "api_key_env": "ANTHROPIC_API_KEY",
                    "max_output_tokens": 100,
                },
                "ollama": {
                    "base_url": "http://127.0.0.1:11434/api/chat",
                    "model": "test-model",
                    "system_prompt": "test",
                },
            },
        }
    )


class AIProviderPolicyTests(unittest.TestCase):
    def test_offline_mode_makes_no_network_or_local_call(self):
        client = AIClient(make_settings(offline=True))

        with patch("vibe_cnc.claude_client.requests.post") as post:
            ok, message = client.ask("review this")

        self.assertFalse(ok)
        self.assertIn("disabled", message.lower())
        post.assert_not_called()

    def test_production_profile_blocks_ollama_even_if_config_selects_it(self):
        client = AIClient(make_settings(mode="ollama"))

        with patch("vibe_cnc.claude_client.requests.post") as post:
            ok, message = client.ask("review this")

        self.assertFalse(ok)
        self.assertIn("disabled", message.lower())
        self.assertIn("ollama", message.lower())
        post.assert_not_called()

    def test_unknown_provider_never_falls_back_to_ollama(self):
        client = AIClient(make_settings(mode="unknown-cloud"))

        with patch("vibe_cnc.claude_client.requests.post") as post:
            ok, message = client.ask("review this")

        self.assertFalse(ok)
        self.assertIn("unsupported", message.lower())
        self.assertIn("no fallback", message.lower())
        post.assert_not_called()

    def test_anthropic_alias_routes_to_cloud_client(self):
        client = AIClient(make_settings(mode="anthropic"))

        with patch.object(client, "ask_claude", return_value=(True, "cloud-ok")) as cloud:
            with patch.object(client, "ask_ollama", return_value=(True, "local-bad")) as local:
                result = client.ask("review this")

        self.assertEqual(result, (True, "cloud-ok"))
        cloud.assert_called_once_with("review this")
        local.assert_not_called()

    def test_legacy_claude_mode_still_routes_to_anthropic_cloud(self):
        client = AIClient(make_settings(mode="claude"))

        with patch.object(client, "ask_claude", return_value=(True, "cloud-ok")) as cloud:
            result = client.ask("review this")

        self.assertEqual(result, (True, "cloud-ok"))
        cloud.assert_called_once_with("review this")

    def test_ollama_remains_available_only_outside_production_profile(self):
        client = AIClient(make_settings(mode="ollama", profile=None))

        with patch.object(client, "ask_ollama", return_value=(True, "local-ok")) as local:
            result = client.ask("review this")

        self.assertEqual(result, (True, "local-ok"))
        local.assert_called_once_with("review this")


if __name__ == "__main__":
    unittest.main()
