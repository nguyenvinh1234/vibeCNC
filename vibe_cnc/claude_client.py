import json
import os
from typing import Tuple

import requests


class AIClient:
    def __init__(self, settings):
        self.cfg = settings.data

    def ask(self, prompt: str) -> Tuple[bool, str]:
        """Main ask method with explicit provider selection and no silent fallback.

        The current CNC PC is weak, so local AI is disabled by default through
        ``ai.allow_local: false``.  This is a deployment default, not a permanent
        ban: a future machine with sufficient CPU/GPU/RAM may explicitly enable
        local Ollama without changing the Mach3Turn machine profile.
        """
        ai_cfg = self.cfg.get("ai", {})

        if ai_cfg.get("offline", False):
            return (
                False,
                "AI is disabled by ai.offline=true. Enable AI and select a provider to use it.",
            )

        mode = str(ai_cfg.get("mode", "anthropic")).strip().lower()

        if mode in ("claude", "anthropic"):
            return self.ask_claude(prompt)

        if mode == "ollama":
            if not bool(ai_cfg.get("allow_local", False)):
                return (
                    False,
                    "Local AI/Ollama is disabled by ai.allow_local=false. "
                    "Enable it only on a machine with sufficient resources.",
                )
            return self.ask_ollama(prompt)

        return (
            False,
            f"Unsupported AI provider mode: {mode}. No fallback provider was used.",
        )

    # ---- Claude (Anthropic) ----
    def ask_claude(self, prompt: str) -> Tuple[bool, str]:
        """Ask Claude API with comprehensive error handling"""
        try:
            anthropic = self.cfg["ai"]["anthropic"]
            api_key = os.environ.get(
                anthropic.get("api_key_env", "ANTHROPIC_API_KEY"), ""
            )

            if not api_key or api_key.strip() == "":
                return (
                    False,
                    "ANTHROPIC_API_KEY is not set. Configure the environment variable before using Anthropic API.",
                )

            base_url = anthropic.get("base_url", "")
            if not base_url:
                return (False, "config.yaml invalid: ai.anthropic.base_url missing")

            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            }

            data = {
                "model": anthropic.get("model", "claude-sonnet-4-20250514"),
                "max_tokens": int(anthropic.get("max_output_tokens", 800)),
                "messages": [{"role": "user", "content": prompt}],
            }

            try:
                response = requests.post(
                    base_url,
                    headers=headers,
                    data=json.dumps(data),
                    timeout=60,
                )
            except requests.exceptions.Timeout:
                return (False, "Claude API: Timeout after 60s. Please try again.")
            except requests.exceptions.ConnectionError:
                return (
                    False,
                    "Claude API: No connection. Please check your internet connection.",
                )
            except requests.exceptions.RequestException as exc:
                return (False, f"Claude API: Network error - {str(exc)}")

            if response.status_code == 401:
                return (
                    False,
                    "Claude API: Invalid API key. Please check ANTHROPIC_API_KEY.",
                )
            if response.status_code == 429:
                return (
                    False,
                    "Claude API: Rate limit reached. Please wait a moment and try again.",
                )
            if response.status_code == 500:
                return (False, "Claude API: Server error. Please try again later.")
            if response.status_code != 200:
                error_msg = response.text[:300] if response.text else "Unknown error"
                return (
                    False,
                    f"Claude API HTTP {response.status_code}: {error_msg}",
                )

            try:
                payload = response.json()
            except json.JSONDecodeError:
                return (False, "Claude API: Invalid JSON response")

            parts = payload.get("content", [])
            text_parts = []
            for part in parts:
                if isinstance(part, dict) and part.get("type") == "text":
                    text_parts.append(part.get("text", ""))
                elif isinstance(part, str):
                    text_parts.append(part)

            result = "\n".join(text_parts).strip()
            if not result:
                result = str(payload)[:1000] if payload else "Empty response"

            return (True, result)

        except KeyError as exc:
            return (False, f"Config error: '{exc}' missing in config.yaml")
        except Exception as exc:
            return (False, f"Unexpected error: {type(exc).__name__}: {str(exc)}")

    # ---- Ollama (optional local provider) ----
    def ask_ollama(self, prompt: str) -> Tuple[bool, str]:
        """Ask Ollama API when local AI has been explicitly enabled."""
        try:
            ollama = self.cfg["ai"]["ollama"]
            base_url = ollama.get("base_url", "")

            if not base_url:
                return (False, "config.yaml invalid: ai.ollama.base_url missing")

            data = {
                "model": ollama.get("model", "qwen2.5:7b-instruct"),
                "messages": [
                    {"role": "system", "content": ollama.get("system_prompt", "")},
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
            }

            try:
                response = requests.post(base_url, json=data, timeout=120)
            except requests.exceptions.ConnectionError:
                return (
                    False,
                    "Ollama: Connection failed. Is Ollama running?",
                )
            except requests.exceptions.Timeout:
                return (False, "Ollama: Timeout after 120s. Model too slow?")
            except requests.exceptions.RequestException as exc:
                return (False, f"Ollama: Network error - {str(exc)}")

            if response.status_code == 404:
                model = ollama.get("model", "unknown")
                return (False, f"Ollama: Model '{model}' not found.")
            if response.status_code != 200:
                error_msg = response.text[:300] if response.text else "Unknown error"
                return (False, f"Ollama HTTP {response.status_code}: {error_msg}")

            try:
                payload = response.json()
            except json.JSONDecodeError:
                return (False, "Ollama: Invalid JSON response")

            result = payload.get("message", {}).get("content", "").strip()
            if not result:
                result = "Empty response"

            return (True, result)

        except KeyError as exc:
            return (False, f"Config error: '{exc}' missing in config.yaml")
        except Exception as exc:
            return (False, f"Unexpected error: {type(exc).__name__}: {str(exc)}")
