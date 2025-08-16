"""
Main Window for Organoid Segmentation Application

This module provides the central user interface for the organoid segmentation
application. It coordinates between various UI components and services to 
provide a unified workflow for image annotation and mask creation.

The main window integrates:
- Image display and navigation
- Drawing tools for manual annotation
- SAM (Segment Anything Model) integration for semi-automated segmentation
- Experiment and folder management
- Mask saving and export functionality
"""
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QMessageBox, QSizePolicy)
from PySide6.QtGui import QImage
import numpy as np
from ui.drawing_canvas import DrawingCanvas
from ui.components import (DrawingTools, FolderManager, ExperimentManager, 
                          ImageControls, ImageInfo)

from services.image_manager import ImageManager
from services.experiment_service import ExperimentService
from services.model_service import ModelService
from services.auto_sam_service import AutoSamService
from utils.logging_config import get_logger
from core.events import event_bus, EventType


class MainWindow(QMainWindow):
    """Main application window with modular architecture and clean separation of responsibilities."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Segment Wise")
        
        # Set up logging
        self.logger = get_logger(__name__)
        
        # Initialize services
        self.experiment_service = ExperimentService()
        self.image_manager = ImageManager(self.experiment_service)
        self.model_service = ModelService()
        self.auto_sam_service = AutoSamService(self.model_service)
        
        # SAM state
        self.sam_loaded = False
        self.current_sam_image = None
        
        # Track mask save state
        self.mask_is_saved = True
        self.current_mask_modified = False
        
        # Initialize UI components
        self.init_components()
        self.init_ui()
        self.connect_components()
        self.connect_events()
        
        # Initialize state
        self.initialize_application_state()
        
        # Preload SAM model to avoid freeze on first use
        self.preload_sam_model()

    def init_components(self):
        """Initialize all UI components."""
        # Core components
        self.canvas = DrawingCanvas()
        self.canvas.setMinimumSize(500, 500)
        # Set size policy to expand in both directions
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # UI component widgets
        self.experiment_manager = ExperimentManager(self.experiment_service)
        self.drawing_tools = DrawingTools()
        self.folder_manager = FolderManager()
        self.image_controls = ImageControls()
        self.image_info = ImageInfo()

    def init_ui(self):
        """Initialize the user interface layout."""
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Main layout
        main_layout = QHBoxLayout(self.central_widget)
        
        # Left panel for controls
        left_panel = QVBoxLayout()
        left_panel.addWidget(self.experiment_manager)
        left_panel.addWidget(self.folder_manager)
        left_panel.addWidget(self.drawing_tools)
        
        # Right panel for canvas and controls
        right_panel = QVBoxLayout()
        right_panel.addWidget(self.canvas, 1)  # Give canvas most of the space
        right_panel.addWidget(self.image_info, 0)  # Fixed size for info
        right_panel.addWidget(self.image_controls, 0)  # Fixed size for controls
        
        # Add panels to main layout
        main_layout.addLayout(left_panel, 1)
        main_layout.addLayout(right_panel, 2)

    def connect_components(self):
        """Connect UI components to each other and to the main window."""
        # Experiment manager connections
        self.experiment_manager.experiment_changed.connect(self.on_experiment_changed)
        
        # Folder manager connections
        self.folder_manager.folders_changed.connect(self.on_folders_changed)
        self.folder_manager.image_source_toggled.connect(self.on_image_source_toggled)
        
        # Image controls connections
        self.image_controls.random_image_requested.connect(self.get_random_image)
        self.image_controls.next_image_requested.connect(self.get_next_image)
        self.image_controls.previous_image_requested.connect(self.get_previous_image)
        self.image_controls.mask_saved.connect(self.save_mask)
        self.image_controls.save_and_next_requested.connect(self.save_and_get_next)
        self.image_controls.image_cropped.connect(self.crop_by_mask)
        self.image_controls.all_images_cropped.connect(self.crop_all_images)
        
        # Drawing tools connections
        self.drawing_tools.brush_size_changed.connect(self.canvas.set_penWidth)
        self.drawing_tools.opacity_changed.connect(self.canvas.set_opacity)
        self.drawing_tools.auto_sam_toggled.connect(self.on_auto_sam_toggled)
        self.drawing_tools.threshold_applied.connect(self.apply_threshold)
        
        # Canvas connections
        self.canvas.mask_changed.connect(self.on_mask_modified)
        self.canvas.point_clicked.connect(self.on_sam_marker_placed)

    def connect_events(self):
        """Connect to application events."""
        event_bus.subscribe(EventType.MASK_CREATED, self.on_mask_created)
        event_bus.subscribe(EventType.MASK_CLEARED, self.on_mask_cleared)
        event_bus.subscribe(EventType.FOLDER_REFRESH_REQUESTED, self.on_folder_refresh_requested)
        event_bus.subscribe(EventType.SAM_MARKER_REMOVED, self.on_sam_marker_removed)

    def initialize_application_state(self):
        """Initialize the application state."""
        # Load initial experiment data
        current_experiment = self.experiment_manager.get_current_experiment()
        if current_experiment:
            self.folder_manager.load_unlabelled_folders(current_experiment)
            self.folder_manager.load_labelled_folders(current_experiment)
        
        # Set initial viewing mode
        self.image_manager.set_viewing_mode("unlabelled")
        
        # Initialize button states
        self.image_controls.set_crop_all_enabled(False)  # No folders selected initially
        
        self.update_gui_no_image()
    
    def preload_sam_model(self):
        """Preload SAM model at startup to avoid freeze on first use."""
        try:
            success = self.model_service.load_sam()
            if not success:
                self.logger.error("SAM model could not be loaded. SAM functionality will be disabled.")
                QMessageBox.warning(
                    self, 
                    "SAM Model Warning", 
                    "SAM model could not be loaded. SAM functionality will be disabled."
                )
        except Exception as e:
            self.logger.error(f"Error loading SAM model: {e}", exc_info=True)
            QMessageBox.warning(
                self, 
                "SAM Model Error", 
                f"Error loading SAM model: {str(e)}"
            )

    def on_experiment_changed(self, experiment):
        """Handle experiment change."""
        self.folder_manager.load_unlabelled_folders(experiment)
        self.folder_manager.load_labelled_folders(experiment)
        self.update_canvas_state()

    def on_folders_changed(self, selected_folders):
        """Handle folder selection changes."""
        self.image_manager.set_selected_folders(selected_folders)
        
        # Enable/disable crop all button based on folder selection
        has_folders = len(selected_folders) > 0
        self.image_controls.set_crop_all_enabled(has_folders)
        
        self.update_canvas_state()

    def on_image_source_toggled(self, mode):
        """Handle image source toggle."""
        self.image_manager.set_viewing_mode(mode)
        self.update_canvas_state()

    def on_folder_refresh_requested(self, event):
        """Handle folder refresh request."""
        current_experiment = self.experiment_manager.get_current_experiment()
        if current_experiment:
            self.folder_manager.load_unlabelled_folders(current_experiment)
            self.folder_manager.load_labelled_folders(current_experiment)
            
            # Clear current selections and update canvas
            self.image_manager.set_selected_folders([])
            self.update_canvas_state()

    def update_canvas_state(self):
        """Update canvas state based on current selections."""
        if self.image_manager.get_num_images() > 0:
            self.get_random_image()
        else:
            self.load_image_path(None, None)

    def get_random_image(self):
        """Load a random image."""
        file_path = self.image_manager.get_random_image()
        if file_path:
            mask_path = self.image_manager.get_image_mask()
            self.load_image_path(file_path, mask_path)
        else:
            self.load_image_path(None, None)

    def get_next_image(self):
        """Load next image."""
        file_path = self.image_manager.get_next_image()
        if file_path:
            mask_path = self.image_manager.get_image_mask()
            self.load_image_path(file_path, mask_path)

    def get_previous_image(self):
        """Load previous image."""
        file_path = self.image_manager.get_previous_image()
        if file_path:
            mask_path = self.image_manager.get_image_mask()
            self.load_image_path(file_path, mask_path)

    def load_image_path(self, file_path, mask_path):
        """Load image and mask to canvas."""
        if file_path:
            self.update_gui_image()
            self.canvas.loadImage(file_path)
            if mask_path:
                self.canvas.loadMask(mask_path)
                self.mask_is_saved = True
            else:
                self.canvas.clearMask()
                self.mask_is_saved = True
            self.current_mask_modified = False
            self.image_controls.update_save_indicator(self.mask_is_saved)
            
            # Reset SAM state for new image (will be loaded on demand)
            self.sam_loaded = False
            self.current_sam_image = None
            
            # Check if Auto SAM is enabled and apply it
            if self.drawing_tools.is_auto_sam_enabled():
                self.apply_auto_sam(file_path)
        else:
            self.update_gui_no_image()

    def apply_threshold(self, threshold_value):
        """Apply thresholding to generate mask."""
        current_path = self.image_manager.get_current_image_path()
        if current_path:
            self.canvas.applyThreshold(threshold_value, current_path)
            self.on_mask_modified()

    def save_mask(self):
        """Save current mask."""
        mask = self.canvas.get_mask()
        if self.image_manager.save_mask(mask):
            self.mask_is_saved = True
            self.current_mask_modified = False
            self.image_controls.update_save_indicator(self.mask_is_saved)
    
    def save_and_get_next(self):
        """Save current mask and get a random image."""
        # First save the mask
        self.save_mask()
        # Then get a random image
        self.get_random_image()

    def crop_by_mask(self):
        """Crop current image by mask."""
        cropped_np = self.canvas.crop_by_mask()
        if cropped_np is not None:
            self.image_manager.save_cropped_image(cropped_np)

    def crop_all_images(self, overwrite):
        """Crop all images by their masks."""
        if not self.image_manager.current_experiment or not self.image_manager.selected_folders:
            QMessageBox.warning(self, "Warning", "Please select an experiment and folders first.")
            return
        
        try:
            self.image_manager.crop_all_images_by_masks(self.image_manager.selected_folders, overwrite)
            QMessageBox.information(self, "Success", "All images have been cropped successfully!")
        except Exception as e:
            self.logger.error(f"Error cropping images: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Error cropping images: {str(e)}")

    def on_sam_marker_placed(self, point):
        """Handle SAM marker placement."""
        current_path = self.image_manager.get_current_image_path()
        if not current_path:
            return
        
        # Load SAM on demand when marker is placed
        if not self.sam_loaded or self.current_sam_image != current_path:
            if not self.load_sam_for_current_image():
                return
        
        # Apply SAM with the marker point
        self.apply_sam_with_point(point)

    def load_sam_for_current_image(self):
        """Load SAM model for the current image on demand."""
        current_path = self.image_manager.get_current_image_path()
        if not current_path:
            return False
        
        self.image_controls.show_progress_bar(True)
        
        try:
            success = self.model_service.set_sam_predictor(current_path)
            if success:
                self.sam_loaded = True
                self.current_sam_image = current_path
                return True
            else:
                self.logger.error(f"Error loading SAM model: {current_path}")
                return False
        except Exception as e:
            self.logger.error(f"Error loading SAM model: {e}", exc_info=True)
            QMessageBox.warning(self, "SAM Error", f"Could not load SAM model: {str(e)}")
            return False
        finally:
            self.image_controls.show_progress_bar(False)
    
    def load_sam_for_image(self, image_path):
        """Load SAM model for a specific image (legacy method)."""
        self.image_controls.show_progress_bar(True)
        
        try:
            success = self.model_service.set_sam_predictor(image_path)
            if success:
                self.sam_loaded = True
                self.current_sam_image = image_path
    
            else:
                pass
        except Exception as e:
            self.logger.error(f"Error loading SAM model: {e}", exc_info=True)
            QMessageBox.warning(self, "SAM Error", f"Could not load SAM model: {str(e)}")
        finally:
            self.image_controls.show_progress_bar(False)

    def apply_sam_with_point(self, point):
        """Apply SAM segmentation with a point marker."""
        # Get all current markers from canvas
        markers = self.canvas.get_sam_markers()
        self.apply_sam_with_markers(markers)
    
    def apply_sam_with_markers(self, markers):
        """Apply SAM segmentation with a list of markers."""
        try:
            if not markers:
                self.logger.error("No markers provided for SAM segmentation")
                return
            
            sam_points = np.array([[p.x(), p.y()] for p in markers])
            
            mask = self.model_service.add_predictor_point(sam_points)
            
            if mask is not None:
                mask_qimage = self.convert_sam_mask_to_qimage(mask)
                self.canvas.set_mask(mask_qimage)
                self.on_mask_modified()  # Mark as modified
            
        except Exception as e:
            self.logger.error(f"Error applying SAM segmentation: {e}", exc_info=True)
            QMessageBox.warning(self, "SAM Error", f"Could not apply SAM segmentation: {str(e)}")

    def convert_sam_mask_to_qimage(self, mask):
        """Convert SAM mask (numpy array) to QImage."""
        height, width = mask.shape
        mask_image = np.zeros((height, width, 4), dtype=np.uint8)
        mask_image[mask == 1] = [0, 0, 255, 255]  # Blue mask where SAM detected
        
        qimage = QImage(mask_image.data, width, height, mask_image.strides[0], QImage.Format_RGBA8888)
        return qimage

    def on_mask_created(self, event):
        """Handle mask creation event."""
        self.update_gui_image()

    def on_mask_cleared(self, event):
        """Handle mask clear event."""
        self.on_mask_modified()
        self.update_gui_image()

    def on_mask_modified(self):
        """Handle mask modification."""
        self.current_mask_modified = True
        self.mask_is_saved = False
        self.image_controls.update_save_indicator(self.mask_is_saved)
    
    def on_sam_marker_removed(self, event):
        """Handle SAM marker removal - regenerate mask with remaining markers."""
        if not self.sam_loaded:
            self.logger.error("SAM model not loaded")
            return
        
        remaining_markers = event.data.get("markers", [])
        
        if remaining_markers:
            # Regenerate mask with remaining markers

            self.apply_sam_with_markers(remaining_markers)
        else:
            # No markers left, clear the mask
            self.canvas.clearMask()
            self.on_mask_modified()
    
    def on_auto_sam_toggled(self, enabled):
        """Handle Auto SAM toggle."""
        if enabled:
            current_path = self.image_manager.get_current_image_path()
            if current_path:
                # Apply auto SAM to current image
                self.apply_auto_sam(current_path)
    
    def apply_auto_sam(self, image_path):
        """Apply auto SAM to the given image."""
        if not image_path:
            self.logger.error("No image path provided for auto SAM")
            return
        
        # Load SAM on demand when Auto SAM is used
        if not self.sam_loaded or self.current_sam_image != image_path:
            if not self.load_sam_for_current_image():
                self.logger.error("Failed to load SAM model for auto SAM")
                return
        
        # Use the auto SAM service to get the centroid point
        centroid_point = self.auto_sam_service.generate_auto_mask(image_path)
        if centroid_point:
            self.apply_auto_sam_point(centroid_point)
    
    def apply_auto_sam_point(self, point):
        """Apply SAM with the auto-generated point."""
        try:
            # Convert QPoint to numpy array format expected by SAM
            sam_points = np.array([[point.x(), point.y()]])
            
            # Apply SAM model
            mask = self.model_service.add_predictor_point(sam_points)
            
            if mask is not None:
                # Convert mask to QImage format
                mask_qimage = self.convert_sam_mask_to_qimage(mask)
                self.canvas.set_mask(mask_qimage)
                self.on_mask_modified()  # Mark as modified

            else:
                self.logger.error("Auto SAM failed to generate mask")
            
        except Exception as e:
            self.logger.error(f"Error applying auto SAM: {e}", exc_info=True)
            QMessageBox.warning(self, "Auto SAM Error", f"Could not apply auto SAM: {str(e)}")

    def update_gui_image(self):
        """Update GUI when image is loaded."""
        self.image_info.update_image_info(self.image_manager.get_image_filename())
        self.image_controls.update_image_info(
            self.image_manager.get_image_index(), 
            self.image_manager.get_num_images()
        )
        self.image_controls.set_image_controls_enabled(True)
        self.image_controls.set_navigation_enabled(True)
        self.drawing_tools.set_tools_enabled(True)

    def update_gui_no_image(self):
        """Update GUI when no image is loaded."""
        self.image_info.clear_image_info()
        self.image_controls.reset_image_info()
        
        # Determine placeholder type based on state
        placeholder_type = "default"
        if self.image_manager.selected_folders and self.image_manager.viewing_mode == "unlabelled":
            # Check if we have folders selected but no unlabelled images
            total_images = 0
            for folder_name in self.image_manager.selected_folders:
                folder_images = self.experiment_service.get_folder_image_paths(
                    self.image_manager.current_experiment, folder_name
                )
                total_images += len(folder_images)
            
            if total_images > 0:
                placeholder_type = "no_unlabelled"
            else:
                placeholder_type = "no_images"
        
        self.canvas.displayPlaceholder(placeholder_type)
        self.canvas.clearMask()
        self.image_controls.set_image_controls_enabled(False)
        self.drawing_tools.set_tools_enabled(False)
        
        # Disable navigation if no images available, but check if we have pools
        has_images = self.image_manager.get_num_images() > 0
        self.image_controls.set_navigation_enabled(has_images)
        
        # Reset save state
        self.mask_is_saved = True
        self.current_mask_modified = False
        self.image_controls.update_save_indicator(self.mask_is_saved)
