"""
Image info widget for displaying current image information.
"""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QGroupBox, QLabel

class ImageInfo(QWidget):
    """Widget for displaying current image information."""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface."""
        layout = QHBoxLayout()
        
        # Image info group
        self.image_info_group = QGroupBox("Image Info")
        image_info_layout = QHBoxLayout()
        
        self.image_info_label = QLabel()
        image_info_layout.addWidget(self.image_info_label)
        
        self.image_info_group.setLayout(image_info_layout)
        self.image_info_group.setMaximumHeight(60)
        self.image_info_group.setVisible(False)  # Initially hidden
        
        layout.addWidget(self.image_info_group)
        self.setLayout(layout)
    
    def update_image_info(self, filename):
        """Update the displayed image information."""
        if filename:
            self.image_info_label.setText(filename)
            self.image_info_group.setVisible(True)
        else:
            self.clear_image_info()
    
    def clear_image_info(self):
        """Clear the image information display."""
        self.image_info_label.setText("")
        self.image_info_group.setVisible(False)
    
    def set_visible(self, visible):
        """Set the visibility of the image info group."""
        self.image_info_group.setVisible(visible)
