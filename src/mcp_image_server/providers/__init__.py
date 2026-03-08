from .base import BaseImageProvider
from .provider_manager import ProviderManager

__all__ = ["BaseImageProvider", "HunyuanProvider", "OpenAIProvider", "DoubaoProvider", "ProviderManager"]


def __getattr__(name: str):
    if name == "HunyuanProvider":
        from .hunyuan_provider import HunyuanProvider
        return HunyuanProvider
    if name == "OpenAIProvider":
        from .openai_provider import OpenAIProvider
        return OpenAIProvider
    if name == "DoubaoProvider":
        from .doubao_provider import DoubaoProvider
        return DoubaoProvider
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
