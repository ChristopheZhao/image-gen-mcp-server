import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mcp_image_server.providers.provider_manager import ProviderManager


class ProviderManagerConfigTests(unittest.TestCase):
    @staticmethod
    def _build_config(**overrides):
        base = {
            "default_provider": None,
            "tencent_secret_id": None,
            "tencent_secret_key": None,
            "openai_api_key": None,
            "openai_base_url": None,
            "openai_model": "gpt-image-1.5",
            "doubao_api_key": None,
            "doubao_endpoint": None,
            "doubao_model": "doubao-seedream-4.5",
            "doubao_fallback_model": "doubao-seedream-4.0",
        }
        base.update(overrides)
        return SimpleNamespace(**base)

    def test_model_fields_are_injected_from_config(self):
        config = self._build_config(
            openai_api_key="openai-key",
            openai_base_url="https://api.openai.com/v1",
            openai_model="gpt-image-1.5",
            doubao_api_key="doubao-key",
            doubao_endpoint="https://ark.cn-beijing.volces.com",
            doubao_model="doubao-seedream-4.5",
            doubao_fallback_model="doubao-seedream-4.0",
        )

        with patch("mcp_image_server.providers.provider_manager.OpenAIProvider") as mock_openai, patch(
            "mcp_image_server.providers.provider_manager.DoubaoProvider"
        ) as mock_doubao:
            mock_openai.return_value = MagicMock()
            mock_doubao.return_value = MagicMock()

            manager = ProviderManager(config=config)

        mock_openai.assert_called_once_with(
            api_key="openai-key",
            base_url="https://api.openai.com/v1",
            model="gpt-image-1.5",
        )
        mock_doubao.assert_called_once_with(
            api_key="doubao-key",
            endpoint="https://ark.cn-beijing.volces.com",
            model="doubao-seedream-4.5",
            fallback_model="doubao-seedream-4.0",
        )
        self.assertEqual(manager.default_provider, "openai")
        self.assertEqual(sorted(manager.get_available_providers()), ["doubao", "openai"])

    def test_empty_model_string_skips_provider_initialization(self):
        config = self._build_config(
            openai_api_key="openai-key",
            openai_model="   ",
            doubao_api_key="doubao-key",
            doubao_model="",
            doubao_fallback_model="doubao-seedream-4.0",
        )

        with patch("mcp_image_server.providers.provider_manager.OpenAIProvider") as mock_openai, patch(
            "mcp_image_server.providers.provider_manager.DoubaoProvider"
        ) as mock_doubao:
            manager = ProviderManager(config=config)

        mock_openai.assert_not_called()
        mock_doubao.assert_not_called()
        self.assertEqual(manager.get_available_providers(), [])
        self.assertIsNone(manager.default_provider)

    def test_configured_default_provider_overrides_implicit_order(self):
        config = self._build_config(
            default_provider="doubao",
            openai_api_key="openai-key",
            openai_model="gpt-image-1.5",
            doubao_api_key="doubao-key",
            doubao_model="doubao-seedream-4.5",
            doubao_fallback_model="doubao-seedream-4.0",
        )

        with patch("mcp_image_server.providers.provider_manager.OpenAIProvider") as mock_openai, patch(
            "mcp_image_server.providers.provider_manager.DoubaoProvider"
        ) as mock_doubao:
            mock_openai.return_value = MagicMock()
            mock_doubao.return_value = MagicMock()
            manager = ProviderManager(config=config)

        self.assertEqual(sorted(manager.get_available_providers()), ["doubao", "openai"])
        self.assertEqual(manager.default_provider, "doubao")

    def test_invalid_or_unavailable_default_provider_fails_fast(self):
        invalid_name_config = self._build_config(
            default_provider="invalid-provider",
            openai_api_key="openai-key",
            openai_model="gpt-image-1.5",
        )
        with patch("mcp_image_server.providers.provider_manager.OpenAIProvider") as mock_openai:
            mock_openai.return_value = MagicMock()
            with self.assertRaises(ValueError):
                ProviderManager(config=invalid_name_config)

        unavailable_config = self._build_config(
            default_provider="doubao",
            openai_api_key="openai-key",
            openai_model="gpt-image-1.5",
        )
        with patch("mcp_image_server.providers.provider_manager.OpenAIProvider") as mock_openai:
            mock_openai.return_value = MagicMock()
            with self.assertRaises(ValueError):
                ProviderManager(config=unavailable_config)


if __name__ == "__main__":
    unittest.main()
