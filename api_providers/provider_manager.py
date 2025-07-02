import os
from typing import Dict, Optional, List
from .base import BaseImageProvider, debug_print
from .hunyuan_provider import HunyuanProvider
from .openai_provider import OpenAIProvider
from .doubao_provider import DoubaoProvider

class ProviderManager:
    """Manages multiple image generation API providers"""
    
    def __init__(self):
        self.providers: Dict[str, BaseImageProvider] = {}
        self.default_provider: Optional[str] = None
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize available providers based on environment variables"""
        
        # Initialize Hunyuan provider
        tencent_secret_id = os.getenv("TENCENT_SECRET_ID")
        tencent_secret_key = os.getenv("TENCENT_SECRET_KEY")
        if tencent_secret_id and tencent_secret_key:
            try:
                self.providers["hunyuan"] = HunyuanProvider(
                    secret_id=tencent_secret_id,
                    secret_key=tencent_secret_key
                )
                debug_print("[INFO] Hunyuan provider initialized successfully")
                # Set as default if no default is set
                if not self.default_provider:
                    self.default_provider = "hunyuan"
            except Exception as e:
                debug_print(f"[ERROR] Failed to initialize Hunyuan provider: {e}")
        
        # Initialize OpenAI provider
        openai_api_key = os.getenv("OPENAI_API_KEY")
        openai_base_url = os.getenv("OPENAI_BASE_URL")  # Optional custom base URL
        if openai_api_key:
            try:
                self.providers["openai"] = OpenAIProvider(
                    api_key=openai_api_key,
                    base_url=openai_base_url
                )
                debug_print("[INFO] OpenAI provider initialized successfully")
                # Set as default if no default is set
                if not self.default_provider:
                    self.default_provider = "openai"
            except Exception as e:
                debug_print(f"[ERROR] Failed to initialize OpenAI provider: {e}")
        
        # Initialize Doubao provider
        doubao_access_key = os.getenv("DOUBAO_ACCESS_KEY")
        doubao_secret_key = os.getenv("DOUBAO_SECRET_KEY")
        doubao_endpoint = os.getenv("DOUBAO_ENDPOINT")  # Optional custom endpoint
        if doubao_access_key and doubao_secret_key:
            try:
                self.providers["doubao"] = DoubaoProvider(
                    access_key=doubao_access_key,
                    secret_key=doubao_secret_key,
                    endpoint=doubao_endpoint
                )
                debug_print("[INFO] Doubao provider initialized successfully")
                # Set as default if no default is set
                if not self.default_provider:
                    self.default_provider = "doubao"
            except Exception as e:
                debug_print(f"[ERROR] Failed to initialize Doubao provider: {e}")
        
        # Check if any provider was initialized
        if not self.providers:
            debug_print("[WARNING] No image generation providers were initialized. Please check your environment variables.")
        else:
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