"""
Experiment management service with automatic folder detection.
"""
from pathlib import Path
from typing import List, Dict, Optional
from models.experiment import ProjectConfig, Experiment, ExperimentFolder
from core.events import event_bus, Event, EventType
from core.base import IExperimentConfig
from utils.logging_config import get_logger


class ExperimentService(IExperimentConfig):
    """
    Service for managing experiments with automatic folder structure detection.
    """
    
    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
        self.config: Optional[ProjectConfig] = None
        self.current_experiment: Optional[Experiment] = None
        self.logger = get_logger(__name__)
        self.refresh_experiments()
    
    def refresh_experiments(self):
        """Refresh experiment list by scanning directories."""
        try:
            self.config = ProjectConfig.auto_detect(str(self.base_path))
            self.logger.info(f"Detected {len(self.config.experiments)} experiments in {self.base_path}")
        except Exception as e:
            self.logger.error(f"Error detecting experiments in {self.base_path}: {e}", exc_info=True)
            # Create empty config as fallback
            self.config = ProjectConfig(
                data_path=self.base_path / "Data",
                labels_path=self.base_path / "Labels", 
                cropped_path=self.base_path / "Cropped",
                experiments=[]
            )
    
    def get_experiments(self) -> List[Experiment]:
        """Get list of all available experiments."""
        return self.config.experiments if self.config else []
    
    def get_experiment_folders(self, experiment_id: str) -> List[ExperimentFolder]:
        """Get folders for a specific experiment."""
        experiment = self.get_experiment_by_id(experiment_id)
        return experiment.folders if experiment else []
    
    def get_experiment_by_id(self, experiment_id: str) -> Optional[Experiment]:
        """Get experiment by ID."""
        for exp in self.get_experiments():
            if exp.id == experiment_id:
                return exp
        return None
    
    def get_experiment_by_index(self, index: int) -> Optional[Experiment]:
        """Get experiment by index."""
        experiments = self.get_experiments()
        if 0 <= index < len(experiments):
            return experiments[index]
        return None
    
    def set_current_experiment(self, experiment: Experiment):
        """Set the current active experiment."""
        self.current_experiment = experiment
        
        # Publish experiment change event
        event_bus.publish(Event(
            event_type=EventType.EXPERIMENT_CHANGED,
            data={
                "experiment": experiment,
                "folders": experiment.folders
            },
            source="experiment_service"
        ))
    
    def get_current_experiment(self) -> Optional[Experiment]:
        """Get the currently active experiment."""
        return self.current_experiment
    
    def get_folder_image_paths(self, experiment: Experiment, folder_name: str) -> List[str]:
        """Get all image paths in a specific folder."""
        folder = next((f for f in experiment.folders if f.name == folder_name), None)
        if not folder:
            return []
        
        image_extensions = {'.png', '.jpg', '.jpeg', '.bmp'}
        image_paths = []
        
        for file_path in folder.path.iterdir():
            if file_path.suffix.lower() in image_extensions:
                image_paths.append(str(file_path))
        
        return sorted(image_paths)
    
    def get_unlabeled_images(self, experiment: Experiment, folder_names: List[str]) -> List[str]:
        """Get unlabeled images from specified folders."""
        unlabeled_images = []
        
        for folder_name in folder_names:
            folder_images = self.get_folder_image_paths(experiment, folder_name)
            
            for image_path in folder_images:
                # Check if corresponding mask exists
                if not self.has_mask(image_path):
                    unlabeled_images.append(image_path)
        
        return unlabeled_images
    
    def get_labeled_images(self, experiment: Experiment, folder_names: List[str]) -> List[str]:
        """Get labeled images from specified folders."""
        labeled_images = []
        
        for folder_name in folder_names:
            folder_images = self.get_folder_image_paths(experiment, folder_name)
            
            for image_path in folder_images:
                # Check if corresponding mask exists
                if self.has_mask(image_path):
                    labeled_images.append(image_path)
        
        return labeled_images
    
    def has_mask(self, image_path: str) -> bool:
        """Check if an image has a corresponding mask."""
        image_path = Path(image_path)
        
        # Calculate relative path from data directory
        try:
            relative_path = image_path.relative_to(self.config.data_path)
            mask_path = self.config.labels_path / relative_path
            return mask_path.exists()
        except ValueError:
            # Image path is not relative to data path
            return False
    
    def get_mask_path(self, image_path: str) -> Optional[str]:
        """Get the mask path for an image."""
        if not self.has_mask(image_path):
            return None
        
        image_path = Path(image_path)
        relative_path = image_path.relative_to(self.config.data_path)
        mask_path = self.config.labels_path / relative_path
        return str(mask_path)
    
    def create_directories(self):
        """Create necessary directories if they don't exist."""
        if self.config:
            self.config.data_path.mkdir(exist_ok=True)
            self.config.labels_path.mkdir(exist_ok=True)
            self.config.cropped_path.mkdir(exist_ok=True)
    
    def get_number_experiments(self) -> int:
        """Get total number of experiments."""
        return len(self.get_experiments())
    
    def get_experiment_dates(self, experiment_number: int) -> List[str]:
        """Get folder names for an experiment (compatibility method)."""
        experiment = self.get_experiment_by_index(experiment_number - 1)  # Convert 1-based to 0-based
        return [folder.name for folder in experiment.folders] if experiment else []
    
    @property
    def data_path(self) -> str:
        """Get data path for compatibility."""
        return str(self.config.data_path) if self.config else "./Data"
    
    @property
    def labels_path(self) -> str:
        """Get labels path for compatibility."""
        return str(self.config.labels_path) if self.config else "./Labels"
    
    @property
    def cropped_path(self) -> str:
        """Get cropped path for compatibility."""
        return str(self.config.cropped_path) if self.config else "./Cropped"
    
    def get_project_stats(self) -> Dict[str, int]:
        """Get project-wide statistics."""
        experiments = self.get_experiments()
        total_images = sum(exp.total_images for exp in experiments)
        total_labeled = sum(exp.labeled_count for exp in experiments)
        
        return {
            "total_experiments": len(experiments),
            "total_images": total_images,
            "total_labeled_folders": total_labeled,
            "completion_percentage": int((total_labeled / max(1, total_images)) * 100)
        }
