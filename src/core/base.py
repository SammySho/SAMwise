"""
Base classes and interfaces for the application.
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from enum import Enum
from PySide6.QtGui import QImage

class ToolType(Enum):
    """Available drawing tools."""
    BRUSH = "brush"
    MARKER = "marker"  # For SAM point selection
    ERASER = "eraser"

class MaskMode(Enum):
    """Different mask creation modes."""
    MANUAL = "manual"        # Hand-drawn
    SAM_POINT = "sam_point"  # SAM with point prompts
    SAM_AUTO = "sam_auto"    # SAM automatic
    THRESHOLD = "threshold"   # Threshold-based

class IMaskGenerator(ABC):
    """Interface for mask generation strategies."""
    
    @abstractmethod
    def generate_mask(self, image_path: str, **kwargs) -> Optional['QImage']:
        """Generate a mask for the given image."""
        pass

class IImageLoader(ABC):
    """Interface for image loading strategies."""
    
    @abstractmethod
    def load_images(self, path: str) -> List[str]:
        """Load image paths from a directory."""
        pass

class IExperimentConfig(ABC):
    """Interface for experiment configuration."""
    
    @abstractmethod
    def get_experiments(self) -> List[dict]:
        """Get list of available experiments."""
        pass
    
    @abstractmethod
    def get_experiment_folders(self, experiment_id: str) -> List[str]:
        """Get folders for a specific experiment."""
        pass
