from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import sys

def debug_print(*args, **kwargs):
    """Print debug messages to stderr instead of stdout"""
    print(*args, file=sys.stderr, **kwargs)

class BaseImageProvider(ABC):
    """Base class for image generation API providers"""
    
    def __init__(self, **kwargs):
        """Initialize the provider with configuration"""
        self.config = kwargs
        
    @abstractmethod
    async def generate_images(
        self, 
        query: str, 
        style: str = "default",
        resolution: str = "1024:1024",
        negative_prompt: str = "",
        **kwargs
    ) -> List[Dict]:
        """
        Generate images using the provider's API
        
        Args:
            query: Image description text
            style: Drawing style
            resolution: Image resolution
            negative_prompt: Negative prompt
            **kwargs: Additional provider-specific parameters
            
        Returns:
            List[Dict]: List of generated image information
        """
        pass
    
    @abstractmethod
    def get_available_styles(self) -> Dict[str, str]:
        """Get available image styles for this provider"""
        pass
    
    @abstractmethod
    def get_available_resolutions(self) -> Dict[str, str]:
        """Get available image resolutions for this provider"""
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Get the name of this provider"""
        pass
    
    def validate_style(self, style: str) -> bool:
        """Validate if the style is supported by this provider"""
        return style in self.get_available_styles()
    
    def validate_resolution(self, resolution: str) -> bool:
        """Validate if the resolution is supported by this provider"""
        return resolution in self.get_available_resolutions()