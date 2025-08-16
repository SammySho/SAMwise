"""
SAM Model Service for organoid segmentation.
Streamlined service focused solely on SAM functionality.
"""

import os
import numpy as np
import cv2
import torch
from segment_anything import sam_model_registry, SamAutomaticMaskGenerator, SamPredictor
from utils.logging_config import get_logger


class ModelService:
    """Streamlined service for SAM model operations only."""
    
    def __init__(self, sam_checkpoint_path=None, model_type="vit_h"):
        """
        Initialize the SAM model service.
        
        Args:
            sam_checkpoint_path (str): Path to SAM checkpoint file
            model_type (str): SAM model type ('vit_h', 'vit_l', 'vit_b')
        """
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.logger = get_logger(__name__)

        # SAM model configuration
        self.sam_checkpoint_path = sam_checkpoint_path or "Models/sam_vit_h_4b8939.pth"
        self.model_type = model_type
        
        # SAM model state
        self.sam_model = None
        self.predictor = None
        self.mask_generator = None
        self.current_image = None
        
        self.logger.info(f"ModelService initialized with device: {self.device}, model: {self.model_type}")
        
    def load_sam(self):
        """Load the SAM model from checkpoint."""
        if self.sam_model is not None:
            return True
            
        try:
            if not os.path.exists(self.sam_checkpoint_path):
                self.logger.error(f"SAM checkpoint not found at: {self.sam_checkpoint_path}")
                return False
            
            self.logger.info(f"Loading SAM model ({self.model_type}) from {self.sam_checkpoint_path}")
            
            # Load SAM model
            self.sam_model = sam_model_registry[self.model_type](checkpoint=self.sam_checkpoint_path)
            self.sam_model.to(device=self.device)
            
            self.logger.info("SAM model loaded successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error loading SAM model: {e}", exc_info=True)
            return False
    
    def set_sam_predictor(self, image_path):
        """
        Set up SAM predictor for a specific image.
        
        Args:
            image_path (str): Path to the image file
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Load SAM model if not already loaded
            if self.sam_model is None:
                if not self.load_sam():
                    return False
            
            # Load and prepare image
            image = cv2.imread(image_path)
            if image is None:
                self.logger.error(f"Could not load image: {image_path}")
                raise ValueError(f"Could not load image: {image_path}")
            
            # Handle grayscale images
            if len(image.shape) == 2:
                image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
            elif image.shape[2] == 3:
                # Convert BGR to RGB (SAM expects RGB)
                image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Initialize predictor and set image
            self.predictor = SamPredictor(self.sam_model)
            self.predictor.set_image(image)
            self.current_image = image_path
            
            self.logger.debug(f"SAM predictor set for image: {os.path.basename(image_path)}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error setting SAM predictor for {image_path}: {e}", exc_info=True)
            return False
    
    def add_predictor_point(self, input_points, input_labels=None):
        """
        Generate segmentation mask using point prompts.
        
        Args:
            input_points (np.ndarray): Array of (x, y) coordinates  
            input_labels (np.ndarray): Array of labels (1 for foreground, 0 for background)
            
        Returns:
            np.ndarray: Best segmentation mask or None if failed
        """
        try:
            if self.predictor is None:
                return None
            
            # Default to foreground points if no labels provided
            if input_labels is None:
                input_labels = np.ones(len(input_points), dtype=int)
            
            # Ensure correct format
            input_points = np.array(input_points, dtype=np.float32)
            input_labels = np.array(input_labels, dtype=int)
            
            # Generate predictions
            masks, scores, logits = self.predictor.predict(
                point_coords=input_points,
                point_labels=input_labels,
                multimask_output=True,
            )
            
            # Return the mask with the highest score
            best_mask_idx = np.argmax(scores)
            best_mask = masks[best_mask_idx]
            

            return best_mask
            
        except Exception as e:
            self.logger.error(f"Error adding predictor point: {e}", exc_info=True)
            return None
    
    def auto_segment_image(self, image_path, points_per_side=32):
        """
        Perform automatic segmentation on an entire image.
        
        Args:
            image_path (str): Path to the image file
            points_per_side (int): Number of points per side for grid
            
        Returns:
            list: List of segmentation masks with metadata
        """
        try:
            # Load SAM model if not already loaded
            if self.sam_model is None:
                if not self.load_sam():
                    return []
            
            # Load image
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"Could not load image: {image_path}")
            
            # Convert BGR to RGB
            if len(image.shape) == 3:
                image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Initialize mask generator
            if self.mask_generator is None:
                self.mask_generator = SamAutomaticMaskGenerator(
                    self.sam_model,
                    points_per_side=points_per_side,
                )
            
            # Generate masks
            masks = self.mask_generator.generate(image)

            return masks
            
        except Exception as e:
            self.logger.error(f"Error auto segmenting image {image_path}: {e}", exc_info=True)
            return []
    
    def is_sam_available(self):
        """Check if SAM model is available and loaded."""
        return self.sam_model is not None
    
    def get_device_info(self):
        """Get information about the current device and SAM state."""
        return {
            'device': str(self.device),
            'cuda_available': torch.cuda.is_available(),
            'sam_loaded': self.sam_model is not None,
            'predictor_ready': self.predictor is not None,
            'current_image': self.current_image,
            'checkpoint_path': self.sam_checkpoint_path,
            'model_type': self.model_type
        }
    
    def clear_predictor(self):
        """Clear the current predictor state."""
        self.predictor = None
        self.current_image = None
    
    def unload_sam(self):
        """Unload the SAM model to free memory."""
        self.sam_model = None
        self.predictor = None
        self.mask_generator = None
        self.current_image = None
        
        # Force garbage collection
        if torch.cuda.is_available():
            torch.cuda.empty_cache()