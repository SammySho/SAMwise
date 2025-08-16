"""
Folder manager widget for handling unlabelled and labelled image folder selection.
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                               QGroupBox, QListWidget, QListWidgetItem)
from PySide6.QtCore import Qt, Signal
from core.events import event_bus, Event, EventType


class FolderManager(QWidget):
    """Widget for managing folder selection for unlabelled and labelled images."""
    
    # Signals
    folders_changed = Signal(list)  # Emitted when selected folders change
    image_source_toggled = Signal(str)  # Emitted when switching between unlabelled/labelled
    
    def __init__(self):
        super().__init__()
        self.current_mode = "unlabelled"  # Track current viewing mode
        self.init_ui()
        self.connect_events()
    
    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()
        
        # Toggle button for switching between image sources
        self.toggle_button = QPushButton("Toggle Labelled / Unlabelled Images")
        self.toggle_button.clicked.connect(self.toggle_image_source)
        layout.addWidget(self.toggle_button)
        
        # Data source layout - side by side groups
        data_source_layout = QHBoxLayout()
        
        # Unlabelled images group
        self.unlabelled_group = QGroupBox("Unlabelled Images")
        self.unlabelled_group.setEnabled(True)
        unlabelled_layout = QVBoxLayout()
        
        # Unlabelled control buttons
        unlabelled_buttons = QHBoxLayout()
        self.select_all_unlabelled_button = QPushButton("Select All")
        self.select_all_unlabelled_button.clicked.connect(self.select_all_unlabelled)
        self.deselect_all_unlabelled_button = QPushButton("Deselect All")
        self.deselect_all_unlabelled_button.clicked.connect(self.deselect_all_unlabelled)
        
        unlabelled_buttons.addWidget(self.select_all_unlabelled_button)
        unlabelled_buttons.addWidget(self.deselect_all_unlabelled_button)
        unlabelled_layout.addLayout(unlabelled_buttons)
        
        # Unlabelled folder list
        self.unlabelled_list = QListWidget()
        self.unlabelled_list.itemChanged.connect(self.on_folder_selection_changed)
        unlabelled_layout.addWidget(self.unlabelled_list)
        self.unlabelled_group.setLayout(unlabelled_layout)
        
        # Labelled images group
        self.labelled_group = QGroupBox("Labelled Images")
        self.labelled_group.setEnabled(False)
        labelled_layout = QVBoxLayout()
        
        # Labelled control buttons
        labelled_buttons = QHBoxLayout()
        self.select_all_labelled_button = QPushButton("Select All")
        self.select_all_labelled_button.clicked.connect(self.select_all_labelled)
        self.deselect_all_labelled_button = QPushButton("Deselect All")
        self.deselect_all_labelled_button.clicked.connect(self.deselect_all_labelled)
        
        labelled_buttons.addWidget(self.select_all_labelled_button)
        labelled_buttons.addWidget(self.deselect_all_labelled_button)
        labelled_layout.addLayout(labelled_buttons)
        
        # Labelled folder list
        self.labelled_list = QListWidget()
        self.labelled_list.itemChanged.connect(self.on_folder_selection_changed)
        labelled_layout.addWidget(self.labelled_list)
        self.labelled_group.setLayout(labelled_layout)
        
        # Add groups to data source layout
        data_source_layout.addWidget(self.unlabelled_group)
        data_source_layout.addWidget(self.labelled_group)
        layout.addLayout(data_source_layout)
        
        self.setLayout(layout)
    
    def connect_events(self):
        """Connect to application events."""
        event_bus.subscribe(EventType.EXPERIMENT_CHANGED, self.on_experiment_changed)
    
    def on_experiment_changed(self, event):
        """Handle experiment change event."""
        self.refresh_folders()
    
    def refresh_folders(self):
        """Refresh the folder lists when experiment changes."""
        # Emit signal to request folder refresh from experiment level
        event_bus.publish(Event(
            event_type=EventType.FOLDER_REFRESH_REQUESTED,
            source="folder_manager"
        ))
    
    def toggle_image_source(self):
        """Toggle between labeled and unlabeled image sources."""
        if self.unlabelled_group.isEnabled():
            self.unlabelled_group.setEnabled(False)
            self.labelled_group.setEnabled(True)
            self.current_mode = "labelled"
        else:
            self.labelled_group.setEnabled(False)
            self.unlabelled_group.setEnabled(True)
            self.current_mode = "unlabelled"
        
        # Emit signal about mode change
        self.image_source_toggled.emit(self.current_mode)
        
        # Update folder selection
        self.on_folder_selection_changed()
    
    def load_unlabelled_folders(self, experiment):
        """Load unlabeled folders from experiment."""
        self.unlabelled_list.clear()
        if experiment:
            for folder in experiment.folders:
                item = QListWidgetItem(folder.name)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Unchecked)
                self.unlabelled_list.addItem(item)
    
    def load_labelled_folders(self, experiment):
        """Load labeled folders from experiment."""
        self.labelled_list.clear()
        if experiment:
            for folder in experiment.folders:
                if folder.has_labels:
                    item = QListWidgetItem(folder.name)
                    item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                    item.setCheckState(Qt.Unchecked)
                    self.labelled_list.addItem(item)
    
    def select_all_unlabelled(self):
        """Select all unlabeled folders."""
        for index in range(self.unlabelled_list.count()):
            item = self.unlabelled_list.item(index)
            item.setCheckState(Qt.Checked)
    
    def deselect_all_unlabelled(self):
        """Deselect all unlabeled folders."""
        for index in range(self.unlabelled_list.count()):
            item = self.unlabelled_list.item(index)
            item.setCheckState(Qt.Unchecked)
    
    def select_all_labelled(self):
        """Select all labeled folders."""
        for index in range(self.labelled_list.count()):
            item = self.labelled_list.item(index)
            item.setCheckState(Qt.Checked)
    
    def deselect_all_labelled(self):
        """Deselect all labeled folders."""
        for index in range(self.labelled_list.count()):
            item = self.labelled_list.item(index)
            item.setCheckState(Qt.Unchecked)
    
    def on_folder_selection_changed(self):
        """Handle folder selection changes."""
        selected_folders = self.get_selected_folders()
        self.folders_changed.emit(selected_folders)
    
    def get_selected_folders(self):
        """Get list of currently selected folder names."""
        selected_folders = []
        
        if self.unlabelled_group.isEnabled():
            # Get selected unlabelled folders
            for index in range(self.unlabelled_list.count()):
                item = self.unlabelled_list.item(index)
                if item.checkState() == Qt.Checked:
                    selected_folders.append(item.text())
        else:
            # Get selected labelled folders
            for index in range(self.labelled_list.count()):
                item = self.labelled_list.item(index)
                if item.checkState() == Qt.Checked:
                    selected_folders.append(item.text())
        
        return selected_folders
    
    def get_current_mode(self):
        """Get current viewing mode (unlabelled or labelled)."""
        return self.current_mode
    
    def set_viewing_mode(self, mode):
        """Set the viewing mode programmatically."""
        if mode == "unlabelled" and not self.unlabelled_group.isEnabled():
            self.toggle_image_source()
        elif mode == "labelled" and not self.labelled_group.isEnabled():
            self.toggle_image_source()
