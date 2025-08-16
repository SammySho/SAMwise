"""
Image controls widget for navigation, threshold, and mask operations.
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                               QLabel, QProgressBar, QDialog, 
                               QCheckBox)
from PySide6.QtCore import Signal
from core.events import event_bus, EventType

class ImageControls(QWidget):
    """Widget for image navigation and mask operations."""
    
    # Signals
    random_image_requested = Signal()
    next_image_requested = Signal()
    previous_image_requested = Signal()
    mask_saved = Signal()
    save_and_next_requested = Signal()  # Save current mask and get random image
    image_cropped = Signal()
    all_images_cropped = Signal(bool)  # overwrite parameter
    
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()
        
        # Progress bar for SAM loading
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setFormat("Loading SAM model...")
        layout.addWidget(self.progress_bar)
        
        # Image navigation
        nav_layout = QHBoxLayout()
        self.prev_image_button = QPushButton("Previous")
        self.prev_image_button.clicked.connect(self.previous_image_requested.emit)
        
        self.index_label = QLabel("Image index: , Pool Size: ")
        
        self.next_image_button = QPushButton("Next")
        self.next_image_button.clicked.connect(self.next_image_requested.emit)
        
        self.load_image_button = QPushButton("Get Random Image")
        self.load_image_button.clicked.connect(self.random_image_requested.emit)
        
        nav_layout.addWidget(self.prev_image_button)
        nav_layout.addWidget(self.index_label)
        nav_layout.addWidget(self.next_image_button)
        nav_layout.addWidget(self.load_image_button)
        layout.addLayout(nav_layout)
        
        # Mask controls
        mask_layout = QHBoxLayout()
        
        # Save/crop buttons with save indicator
        save_layout = QVBoxLayout()
        
        # Save button with indicator
        save_button_layout = QHBoxLayout()
        self.save_mask_button = QPushButton("Save Mask")
        self.save_mask_button.clicked.connect(self.mask_saved.emit)
        self.save_mask_button.setMinimumWidth(120)  # Make wider
        
        self.save_indicator = QLabel("●")
        self.save_indicator.setStyleSheet("color: green; font-size: 16px; font-weight: bold;")
        self.save_indicator.setToolTip("Mask is saved")
        
        self.save_and_next_button = QPushButton("Save & Next")
        self.save_and_next_button.clicked.connect(self.save_and_next_requested.emit)
        self.save_and_next_button.setToolTip("Save current mask and get a random image")
        self.save_and_next_button.setMinimumWidth(120)  # Make wider
        
        save_button_layout.addStretch()  # Left stretch for centering
        save_button_layout.addWidget(self.save_mask_button)
        save_button_layout.addWidget(self.save_indicator)
        save_button_layout.addWidget(self.save_and_next_button)
        save_button_layout.addStretch()  # Right stretch for centering
        save_layout.addLayout(save_button_layout)
        
        self.crop_mask_button = QPushButton("Crop Image By Mask")
        self.crop_mask_button.clicked.connect(self.image_cropped.emit)
        save_layout.addWidget(self.crop_mask_button)
        
        self.crop_all_button = QPushButton("Crop All Images By Mask")
        self.crop_all_button.clicked.connect(self.show_crop_all_dialog)
        save_layout.addWidget(self.crop_all_button)
        
        mask_layout.addLayout(save_layout)
        layout.addLayout(mask_layout)
        
        self.setLayout(layout)
        
        # Initially disable image-dependent controls
        self.set_image_controls_enabled(False)
    
    def connect_events(self):
        """Connect to application events."""
        event_bus.subscribe(EventType.MASK_CREATED, self.on_mask_created)
        event_bus.subscribe(EventType.MASK_CLEARED, self.on_mask_cleared)
    
    def show_crop_all_dialog(self):
        """Show confirmation dialog for cropping all images."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Crop All Images Confirmation")
        layout = QVBoxLayout(dialog)
        
        label = QLabel("This will crop all images in the selected folders by their corresponding masks.\n"
                      "This operation may take some time.")
        layout.addWidget(label)
        
        # Overwrite checkbox
        overwrite_checkbox = QCheckBox("Overwrite existing cropped images")
        layout.addWidget(overwrite_checkbox)
        
        # Buttons
        button_layout = QHBoxLayout()
        ok_button = QPushButton("Start Cropping")
        cancel_button = QPushButton("Cancel")
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
        # Connect buttons
        ok_button.clicked.connect(lambda: self.start_crop_all(dialog, overwrite_checkbox.isChecked()))
        cancel_button.clicked.connect(dialog.reject)
        
        dialog.exec()
    
    def start_crop_all(self, dialog, overwrite):
        """Start the crop all operation."""
        dialog.accept()
        self.all_images_cropped.emit(overwrite)
    
    def update_image_info(self, image_index, pool_size):
        """Update image navigation info."""
        self.index_label.setText(f"Image index: {image_index + 1}, Pool size: {pool_size}")
    
    def set_image_controls_enabled(self, enabled):
        """Enable/disable image-dependent controls."""
        self.save_mask_button.setEnabled(enabled)
        self.save_and_next_button.setEnabled(enabled)
        self.crop_mask_button.setEnabled(enabled)
    
    def reset_image_info(self):
        """Reset image info when no image is loaded."""
        self.index_label.setText("Image index:")
    
    def update_save_indicator(self, is_saved):
        """Update the save indicator based on mask state."""
        if is_saved:
            self.save_indicator.setText("●")
            self.save_indicator.setStyleSheet("color: green; font-size: 16px; font-weight: bold;")
            self.save_indicator.setToolTip("Mask is saved")
        else:
            self.save_indicator.setText("●")
            self.save_indicator.setStyleSheet("color: red; font-size: 16px; font-weight: bold;")
            self.save_indicator.setToolTip("Mask has unsaved changes")
    
    def show_progress_bar(self, visible=True):
        """Show/hide the progress bar for SAM loading."""
        self.progress_bar.setVisible(visible)
        if visible:
            self.progress_bar.setRange(0, 0)  # Indeterminate progress