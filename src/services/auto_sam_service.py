"""
Auto SAM service for automatic mask generation using the largest region detection.
"""

import cv2
from skimage.measure import regionprops, label
from PySide6.QtCore import QObject, Signal
from PySide6.QtCore import QPoint
from utils.logging_config import get_logger


class AutoSamService(QObject):
    """Service for automatic SAM mask generation."""
    
    # Signals
    auto_mask_generated = Signal(object)  # QPoint for the centroid
    
    def __init__(self, model_service):
        super().__init__()
        self.model_service = model_service
        self.logger = get_logger(__name__)
    
    def generate_auto_mask(self, image_path):
        """
        Generate auto mask using the largest region detection approach.
        
        Args:
            image_path: Path to the image to process.
            
        Returns:
            QPoint: Centroid of the largest region, or None if failed.
        """
        if not image_path:
            self.logger.warning("No image path provided for auto SAM generation")
            return None
        
        try:
            self.logger.debug(f"Generating auto mask for image: {image_path}")
            # Load and process the image
            image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            if image is None:
                self.logger.error(f"Could not load image: {image_path}")
                return None
            
            # Binarise the image using Otsu's thresholding method
            _, binarised_image = cv2.threshold(image, 0, 255, cv2.THRESH_OTSU)
            
            # Invert the image
            binarised_image = cv2.bitwise_not(binarised_image)
            
            # Calculate region properties of the image
            labeled_mask = label(binarised_image)
            props = regionprops(labeled_mask)
            
            if not props:
                self.logger.warning(f"No regions found in image: {image_path}")
                return None
            
            # Sort regions by area and select the largest one
            largest_regions = sorted(props, key=lambda x: x.area, reverse=True)[:5]
            
            if largest_regions:
                largest_region = largest_regions[0]
                centroid = largest_region.centroid

                # Convert to QPoint format (x, y) - note the order swap
                centroid_point = QPoint(int(centroid[1]), int(centroid[0]))
                
                self.logger.debug(f"Auto SAM found largest region with area {largest_region.area} at centroid ({centroid_point.x()}, {centroid_point.y()})")
                
                # Emit signal with the centroid point
                self.auto_mask_generated.emit(centroid_point)
                
                return centroid_point
                
        except Exception as e:
            self.logger.error(f"Error generating auto mask for {image_path}: {e}", exc_info=True)
            return None
    
    def apply_auto_sam(self, image_path):
        """
        Apply auto SAM to the given image.
        
        Args:
            image_path: Path to the image to process.
            
        Returns:
            QPoint: The centroid point used for SAM, or None if failed.
        """
        centroid_point = self.generate_auto_mask(image_path)
        
        if centroid_point:
            # The main window should handle the SAM application using this point
            # We just return the point for the caller to use
            return centroid_point
        
        self.logger.error(f"Error applying auto mask for {image_path}", exc_info=True)
        return None