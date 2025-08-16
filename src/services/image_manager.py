"""
Image Management Service

This module provides comprehensive image management functionality for the 
organoid segmentation application. It handles image pools, navigation,
mask operations, and integration with the experiment service.

Key responsibilities:
- Managing image pools based on labeled/unlabeled status
- Providing navigation through image collections
- Handling mask saving and cropping operations
- Coordinating with experiment service for folder management

Classes:
    ImageManager: Central service for all image-related operations
"""

import os
import random
import cv2
from pathlib import Path
from typing import List, Optional, Set
from models.experiment import Experiment
from utils.logging_config import get_logger
from core.events import event_bus, Event, EventType

class ImageManager:
    """
    Modern image manager that works with the new experiment service.
    Replaces the old ImageService with better architecture.
    """
    
    def __init__(self, experiment_service):
        self.experiment_service = experiment_service
        self.current_experiment: Optional[Experiment] = None
        self.selected_folders: Set[str] = set()
        self.viewing_mode = "unlabelled"  # "unlabelled" or "labelled"
        
        # Image pool and current state
        self.image_pool: List[str] = []
        self.current_image_path = ""
        self.current_image_index = 0
        
        # Set up logging
        self.logger = get_logger(__name__)
        
        # Connect to experiment changes
        event_bus.subscribe(EventType.EXPERIMENT_CHANGED, self.on_experiment_changed)
    
    def on_experiment_changed(self, event):
        """Handle experiment change event."""
        self.current_experiment = event.data["experiment"]
        self.selected_folders.clear()
        self.refresh_image_pool()
    
    def set_viewing_mode(self, mode: str):
        """Set viewing mode to 'unlabelled' or 'labelled'."""
        self.viewing_mode = mode
        self.refresh_image_pool()
    
    def set_selected_folders(self, folder_names: List[str]):
        """Set which folders are selected for viewing."""
        self.selected_folders = set(folder_names)
        self.refresh_image_pool()
    
    def refresh_image_pool(self):
        """Refresh the image pool based on current settings."""
        if not self.current_experiment or not self.selected_folders:
            self.image_pool = []
            self.current_image_path = ""
            self.current_image_index = 0
            return
        
        # Build image pool
        self.image_pool = []
        
        for folder_name in self.selected_folders:
            folder_images = self.get_folder_images(folder_name)
            self.image_pool.extend(folder_images)
        
        # Reset current image
        self.current_image_index = 0
        if self.image_pool:
            self.current_image_path = self.image_pool[0]
        else:
            self.current_image_path = ""
    
    def get_folder_images(self, folder_name: str) -> List[str]:
        """Get images from a specific folder based on viewing mode."""
        if not self.current_experiment:
            return []
        
        # Find the folder
        folder = next((f for f in self.current_experiment.folders if f.name == folder_name), None)
        if not folder:
            return []
        
        # Get all image files
        image_extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif'}
        all_images = []
        
        try:
            for file_path in folder.path.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in image_extensions:
                    all_images.append(str(file_path))
        except Exception as e:
            self.logger.error(f"Error getting folder images for {folder_name}: {e}", exc_info=True)
            return []
        
        # Filter based on viewing mode
        if self.viewing_mode == "unlabelled":
            return [img for img in all_images if not self.has_mask(img)]
        elif self.viewing_mode == "labelled":
            return [img for img in all_images if self.has_mask(img)]
        else:
            return all_images
    
    def has_mask(self, image_path: str) -> bool:
        """Check if an image has a corresponding mask."""
        try:
            image_path = Path(image_path)
            data_path = Path(self.experiment_service.data_path)
            labels_path = Path(self.experiment_service.labels_path)
            
            # Calculate relative path from data directory
            relative_path = image_path.relative_to(data_path)
            mask_path = labels_path / relative_path
            
            return mask_path.exists()
        except (ValueError, Exception):
            self.logger.error(f"Error checking mask for {image_path}", exc_info=True)
            return False
    
    def get_mask_path(self, image_path: str) -> Optional[str]:
        """Get the mask path for an image."""
        if not self.has_mask(image_path):
            return None
        
        try:
            image_path = Path(image_path)
            data_path = Path(self.experiment_service.data_path)
            labels_path = Path(self.experiment_service.labels_path)
            
            relative_path = image_path.relative_to(data_path)
            mask_path = labels_path / relative_path
            
            return str(mask_path)
        except (ValueError, Exception):
            self.logger.error(f"Error getting mask path for {image_path}", exc_info=True)
            return None
    
    def get_random_image(self) -> Optional[str]:
        """Get a random image from the current pool."""
        # Refresh pool to ensure we have current labelled/unlabelled state
        self.refresh_image_pool()
        
        if not self.image_pool:
            return None
        
        self.current_image_index = random.randint(0, len(self.image_pool) - 1)
        self.current_image_path = self.image_pool[self.current_image_index]
        return self.current_image_path
    
    def get_image_by_index(self, index: int) -> Optional[str]:
        """Get image by index in the pool."""
        if not self.image_pool or index < 0 or index >= len(self.image_pool):
            return None
        
        self.current_image_index = index
        self.current_image_path = self.image_pool[index]
        return self.current_image_path
    
    def get_next_image(self) -> Optional[str]:
        """Get the next image in the pool."""
        if not self.image_pool:
            return None
        
        next_index = (self.current_image_index + 1) % len(self.image_pool)
        return self.get_image_by_index(next_index)
    
    def get_previous_image(self) -> Optional[str]:
        """Get the previous image in the pool."""
        if not self.image_pool:
            return None
        
        prev_index = (self.current_image_index - 1) % len(self.image_pool)
        return self.get_image_by_index(prev_index)
    
    def save_mask(self, mask_qimage) -> bool:
        """Save a mask for the current image."""
        if not self.current_image_path:
            return False
        
        try:
            image_path = Path(self.current_image_path)
            data_path = Path(self.experiment_service.data_path)
            labels_path = Path(self.experiment_service.labels_path)
            
            # Calculate relative path and create mask path
            relative_path = image_path.relative_to(data_path)
            mask_path = labels_path / relative_path
            
            # Create directories if needed
            mask_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save the mask
            success = mask_qimage.save(str(mask_path))
            
            if success:

                # Publish mask saved event
                event_bus.publish(Event(
                    event_type=EventType.MASK_CREATED,
                    data={"mask_path": str(mask_path), "image_path": self.current_image_path},
                    source="image_manager"
                ))
            
            return success
        except Exception as e:
            self.logger.error(f"Error saving mask for {self.current_image_path}: {e}", exc_info=True)
            return False
    
    def save_cropped_image(self, cropped_image_np) -> bool:
        """Save a cropped image."""
        if not self.current_image_path:
            return False
        
        try:
            image_path = Path(self.current_image_path)
            data_path = Path(self.experiment_service.data_path)
            cropped_path = Path(self.experiment_service.cropped_path)
            
            # Calculate relative path and create cropped path
            relative_path = image_path.relative_to(data_path)
            cropped_image_path = cropped_path / relative_path
            
            # Create directories if needed
            cropped_image_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save the cropped image
            success = cv2.imwrite(str(cropped_image_path), cropped_image_np)
            
            if success:
                return success
            
        except Exception as e:
            self.logger.error(f"Error saving cropped image for {self.current_image_path}: {e}", exc_info=True)
            return False
    
    def get_current_image_path(self) -> str:
        """Get current image path."""
        return self.current_image_path
    
    def get_image_index(self) -> int:
        """Get current image index."""
        return self.current_image_index
    
    def get_num_images(self) -> int:
        """Get total number of images in pool."""
        return len(self.image_pool)
    
    def get_image_filename(self) -> str:
        """Get relative filename of current image."""
        if not self.current_image_path:
            self.logger.error("No current image path")
            return ""
        
        try:
            image_path = Path(self.current_image_path)
            data_path = Path(self.experiment_service.data_path)
            return str(image_path.relative_to(data_path))
        except (ValueError, Exception):
            self.logger.error(f"Error getting image filename for {self.current_image_path}", exc_info=True)
            return os.path.basename(self.current_image_path)
    
    def get_image_mask(self) -> Optional[str]:
        """Get mask path for current image (compatibility method)."""
        return self.get_mask_path(self.current_image_path)
    
    def crop_all_images_by_masks(self, folder_names: List[str], overwrite: bool = False):
        """Crop all images in specified folders by their corresponding masks."""
        if not self.current_experiment:
            self.logger.error("Cannot crop all images: No current experiment selected")
            return
        
        total_cropped = 0
        
        for folder_name in folder_names:
            folder_images = self.get_folder_images_all(folder_name)  # Get all images, not filtered by viewing mode
            
            for image_path in folder_images:
                if self.has_mask(image_path):
                    try:
                        # Check if cropped image already exists
                        cropped_exists = self.cropped_image_exists(image_path)
                        if not overwrite and cropped_exists:

                            continue
                        
                        # Load mask and apply cropping
                        mask_path = self.get_mask_path(image_path)
                        if mask_path and self.crop_image_by_mask(image_path, mask_path):
                            total_cropped += 1

                    except Exception as e:
                        self.logger.error(f"Error cropping image {image_path}: {e}", exc_info=True)
                        continue
        
        self.logger.info(f"Cropped {total_cropped} images")
    
    def get_folder_images_all(self, folder_name: str) -> List[str]:
        """Get all images from a folder regardless of viewing mode."""
        if not self.current_experiment:
            return []
        
        folder = next((f for f in self.current_experiment.folders if f.name == folder_name), None)
        if not folder:
            return []
        
        image_extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif'}
        all_images = []
        
        try:
            for file_path in folder.path.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in image_extensions:
                    all_images.append(str(file_path))
        except Exception as e:
            self.logger.error(f"Error getting folder images all for {folder_name}: {e}", exc_info=True)
            return []
        
        return all_images
    
    def cropped_image_exists(self, image_path: str) -> bool:
        """Check if a cropped version of the image already exists."""
        try:
            image_path = Path(image_path)
            data_path = Path(self.experiment_service.data_path)
            cropped_path = Path(self.experiment_service.cropped_path)
            
            relative_path = image_path.relative_to(data_path)
            cropped_image_path = cropped_path / relative_path
            
            return cropped_image_path.exists()
        except (ValueError, Exception):
            self.logger.error(f"Error checking if cropped image exists for {image_path}", exc_info=True)
            return False
    
    def crop_image_by_mask(self, image_path: str, mask_path: str) -> bool:
        """Crop a specific image by its mask."""
        try:
            
            # Load original image
            original_image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            if original_image is None:
                self.logger.error(f"Error loading original image {image_path}")
                return False
            
            # Load mask
            mask_image = cv2.imread(mask_path, cv2.IMREAD_UNCHANGED)
            if mask_image is None:
                self.logger.error(f"Error loading mask image {mask_path}")
                return False
            
            # Apply mask (set transparent pixels to white)
            if mask_image.shape[2] == 4:  # RGBA mask
                transparency_channel = mask_image[:, :, 3]
                transparency_mask = transparency_channel == 0
                original_image[transparency_mask] = 255
            
            # Save cropped image
            image_path_obj = Path(image_path)
            data_path = Path(self.experiment_service.data_path)
            cropped_path = Path(self.experiment_service.cropped_path)
            
            relative_path = image_path_obj.relative_to(data_path)
            cropped_image_path = cropped_path / relative_path
            
            # Create directories if needed
            cropped_image_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save the cropped image
            success = cv2.imwrite(str(cropped_image_path), original_image)
            if not success:
                self.logger.error(f"Error saving cropped image {cropped_image_path}")
            return success
            
        except Exception as e:
            self.logger.error(f"Error cropping image {image_path} by mask {mask_path}: {e}", exc_info=True)
            return False
