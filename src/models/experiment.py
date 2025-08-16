"""
Data models for experiments and project configuration.
"""

from dataclasses import dataclass
from typing import List
from pathlib import Path

@dataclass
class ExperimentFolder:
    """Represents a single experiment folder (e.g., a date folder)."""
    name: str
    path: Path
    image_count: int
    has_labels: bool = False


@dataclass
class Experiment:
    """Represents an experiment with multiple folders."""
    id: str
    name: str
    path: Path
    folders: List[ExperimentFolder]
    
    @property
    def total_images(self) -> int:
        """Total number of images across all folders."""
        return sum(folder.image_count for folder in self.folders)
    
    @property
    def labeled_count(self) -> int:
        """Number of folders with labels."""
        return sum(1 for folder in self.folders if folder.has_labels)


@dataclass
class ProjectConfig:
    """Project configuration settings."""
    data_path: Path
    labels_path: Path
    cropped_path: Path
    experiments: List[Experiment]
    
    @classmethod
    def auto_detect(cls, base_path: str = ".") -> 'ProjectConfig':
        """Auto-detect experiments from folder structure."""
        base = Path(base_path)
        data_path = base / "Data"
        labels_path = base / "Labels" 
        cropped_path = base / "Cropped"
        
        experiments = []
        
        if data_path.exists():
            for exp_dir in data_path.iterdir():
                if exp_dir.is_dir() and exp_dir.name.startswith("Experiment"):
                    experiment = cls._create_experiment_from_folder(exp_dir, labels_path)
                    experiments.append(experiment)
        
        return cls(
            data_path=data_path,
            labels_path=labels_path,
            cropped_path=cropped_path,
            experiments=sorted(experiments, key=lambda x: x.name)
        )
    
    @classmethod
    def _create_experiment_from_folder(cls, exp_dir: Path, labels_path: Path) -> Experiment:
        """Create an Experiment object from a directory."""
        exp_id = exp_dir.name.lower().replace(" ", "_")
        folders = []
        
        for folder in exp_dir.iterdir():
            if folder.is_dir():
                # Count images in this folder
                image_files = [f for f in folder.iterdir() 
                             if f.suffix.lower() in ['.png', '.jpg', '.jpeg', '.bmp']]
                
                # Check if labels exist for this folder
                label_folder = labels_path / exp_dir.name / folder.name
                has_labels = label_folder.exists() and any(label_folder.iterdir())
                
                exp_folder = ExperimentFolder(
                    name=folder.name,
                    path=folder,
                    image_count=len(image_files),
                    has_labels=has_labels
                )
                folders.append(exp_folder)
        
        return Experiment(
            id=exp_id,
            name=exp_dir.name,
            path=exp_dir,
            folders=sorted(folders, key=lambda x: x.name)
        )
