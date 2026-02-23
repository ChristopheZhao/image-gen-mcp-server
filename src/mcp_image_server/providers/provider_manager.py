from typing import Dict, Optional, List
from .base import BaseImageProvider, debug_print
from .hunyuan_provider import HunyuanProvider
from .openai_provider import OpenAIProvider
from .doubao_provider import DoubaoProvider
from ..config import ServerConfig

class ProviderManager:
    """Manages multiple image generation API providers"""

    SUPPORTED_PROVIDERS = frozenset({"hunyuan", "openai", "doubao"})

    def __init__(self, config: Optional[ServerConfig] = None):
        self.config = config or ServerConfig()
        self.providers: Dict[str, BaseImageProvider] = {}
        self.default_provider: Optional[str] = None
        self._initialize_providers()

    def _initialize_providers(self):
        """Initialize available providers based on parsed server config."""

        # Initialize Hunyuan provider
        if self.config.tencent_secret_id and self.config.tencent_secret_key:
            try:
                self.providers["hunyuan"] = HunyuanProvider(
                    secret_id=self.config.tencent_secret_id,
                    secret_key=self.config.tencent_secret_key
                )
                debug_print("[INFO] Hunyuan provider initialized successfully")
                # Set as default if no default is set
                if not self.default_provider:
                    self.default_provider = "hunyuan"
            except Exception as e:
                debug_print(f"[ERROR] Failed to initialize Hunyuan provider: {e}")
        
        # Initialize OpenAI provider
        if self.config.openai_api_key:
            openai_model = self.config.openai_model.strip()
            if not openai_model:
                debug_print("[WARNING] OPENAI_MODEL is empty. Skipping OpenAI provider initialization.")
            else:
                try:
                    self.providers["openai"] = OpenAIProvider(
                        api_key=self.config.openai_api_key,
                        base_url=self.config.openai_base_url,
                        model=openai_model
                    )
                    debug_print("[INFO] OpenAI provider initialized successfully")
                    # Set as default if no default is set
                    if not self.default_provider:
                        self.default_provider = "openai"
                except Exception as e:
                    debug_print(f"[ERROR] Failed to initialize OpenAI provider: {e}")

        # Initialize Doubao provider (New Ark API)
        if self.config.doubao_api_key:
            doubao_model = self.config.doubao_model.strip()
            doubao_fallback_model = self.config.doubao_fallback_model.strip()
            if not doubao_model:
                debug_print("[WARNING] DOUBAO_MODEL is empty. Skipping Doubao provider initialization.")
            else:
                try:
                    self.providers["doubao"] = DoubaoProvider(
                        api_key=self.config.doubao_api_key,
                        endpoint=self.config.doubao_endpoint,
                        model=doubao_model,
                        fallback_model=doubao_fallback_model or None
                    )
                    debug_print("[INFO] Doubao provider initialized successfully")
                    #Set as default if no default is set
                    if not self.default_provider:
                        self.default_provider = "doubao"
                except Exception as e:
                    debug_print(f"[ERROR] Failed to initialize Doubao provider: {e}")

        # Check if any provider was initialized
        if not self.providers:
            debug_print("[WARNING] No image generation providers were initialized. Please check your environment variables.")

        configured_default_raw = getattr(self.config, "default_provider", None)
        configured_default = (
            configured_default_raw.strip().lower()
            if isinstance(configured_default_raw, str)
            else configured_default_raw
        )
        if configured_default == "":
            configured_default = None
        if configured_default:
            if configured_default not in self.SUPPORTED_PROVIDERS:
                raise ValueError(
                    "Invalid MCP_DEFAULT_PROVIDER. "
                    f"Supported values: {sorted(self.SUPPORTED_PROVIDERS)}; got: {configured_default!r}"
                )
            if configured_default not in self.providers:
                raise ValueError(
                    f"MCP_DEFAULT_PROVIDER={configured_default!r} is configured but unavailable. "
                    f"Initialized providers: {sorted(self.providers.keys()) or 'none'}. "
                    "Check API credentials and model settings."
                )
            self.default_provider = configured_default
        elif len(self.providers) > 1:
            debug_print(
                "[WARNING] Multiple providers are initialized but MCP_DEFAULT_PROVIDER is not set. "
                f"Using implicit default provider: {self.default_provider}"
            )

        if self.providers:
            debug_print(f"[INFO] Initialized providers: {list(self.providers.keys())}")
            debug_print(f"[INFO] Default provider: {self.default_provider}")

    def get_provider(self, provider_name: Optional[str] = None) -> Optional[BaseImageProvider]:
        """Get a specific provider or the default provider"""
        if provider_name:
            return self.providers.get(provider_name)
        elif self.default_provider:
            return self.providers.get(self.default_provider)
        else:
            return None

    def get_available_providers(self) -> List[str]:
        """Get list of available provider names"""
        return list(self.providers.keys())

    def get_all_styles(self) -> Dict[str, Dict[str, str]]:
        """Get styles from all providers"""
        all_styles = {}
        for provider_name, provider in self.providers.items():
            all_styles[provider_name] = provider.get_available_styles()
        return all_styles

    def get_all_resolutions(self) -> Dict[str, Dict[str, str]]:
        """Get resolutions from all providers"""
        all_resolutions = {}
        for provider_name, provider in self.providers.items():
            all_resolutions[provider_name] = provider.get_available_resolutions()
        return all_resolutions

    def validate_provider_style(self, provider_name: str, style: str) -> bool:
        """Validate if a style is supported by a specific provider"""
        provider = self.get_provider(provider_name)
        if provider:
            return provider.validate_style(style)
        return False

    def validate_provider_resolution(self, provider_name: str, resolution: str) -> bool:
        """Validate if a resolution is supported by a specific provider"""
        provider = self.get_provider(provider_name)
        if provider:
            return provider.validate_resolution(resolution)
        return False

    async def generate_images(
        self,
        query: str,
        provider_name: Optional[str] = None,
        style: str = "default",
        resolution: str = "1024:1024",
        negative_prompt: str = "",
        **kwargs
    ) -> List[Dict]:
        """Generate images using the specified provider or default provider"""
        provider = self.get_provider(provider_name)

        if not provider:
            available = ", ".join(self.get_available_providers())
            error_msg = f"Provider '{provider_name}' not available. Available providers: {available}"
            debug_print(f"[ERROR] {error_msg}")
            return [{
                "error": error_msg,
                "content_type": "text/plain"
            }]

        debug_print(f"[INFO] Using provider: {provider.get_provider_name()}")
        return await provider.generate_images(
            query=query,
            style=style,
            resolution=resolution,
            negative_prompt=negative_prompt,
            **kwargs
        )
