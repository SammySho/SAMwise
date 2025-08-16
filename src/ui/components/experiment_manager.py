"""
Experiment manager widget for selecting and managing experiments.
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox, QLabel
from PySide6.QtCore import Signal
from core.events import event_bus, Event, EventType


class ExperimentManager(QWidget):
    """Widget for managing experiment selection."""
    
    # Signals
    experiment_changed = Signal(object)  # Emitted when experiment changes
    
    def __init__(self, experiment_service):
        super().__init__()
        self.experiment_service = experiment_service
        self.init_ui()
        self.load_experiments()
    
    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()
        
        # Experiment selection label
        experiment_label = QLabel("Experiment Selection:")
        experiment_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(experiment_label)
        
        # Experiment controls
        experiment_controls = QHBoxLayout()
        
        # Experiment dropdown
        self.experiment_dropdown = QComboBox()
        self.experiment_dropdown.currentIndexChanged.connect(self.on_experiment_changed)
        experiment_controls.addWidget(self.experiment_dropdown)
        
        # Refresh button
        self.refresh_button = QPushButton("↻")
        self.refresh_button.setToolTip("Refresh experiment list")
        self.refresh_button.setMaximumWidth(30)
        self.refresh_button.clicked.connect(self.refresh_experiments)
        experiment_controls.addWidget(self.refresh_button)
        
        layout.addLayout(experiment_controls)
        self.setLayout(layout)
    
    def load_experiments(self):
        """Load experiments into dropdown."""
        experiments = self.experiment_service.get_experiments()
        self.experiment_dropdown.clear()
        
        if experiments:
            self.experiment_dropdown.addItems([exp.name for exp in experiments])
            # Set first experiment as current
            self.experiment_service.set_current_experiment(experiments[0])
            self.experiment_changed.emit(experiments[0])
    
    def refresh_experiments(self):
        """Refresh the experiment list."""
        current_text = self.experiment_dropdown.currentText()
        
        # Refresh experiments from file system
        self.experiment_service.refresh_experiments()
        
        # Update dropdown
        self.experiment_dropdown.clear()
        experiments = self.experiment_service.get_experiments()
        
        if experiments:
            self.experiment_dropdown.addItems([exp.name for exp in experiments])
            
            # Try to restore previous selection
            index = self.experiment_dropdown.findText(current_text)
            if index >= 0:
                self.experiment_dropdown.setCurrentIndex(index)
            else:
                self.experiment_service.set_current_experiment(experiments[0])
                self.experiment_changed.emit(experiments[0])
        
        # Publish refresh event for other components
        event_bus.publish(Event(
            event_type=EventType.EXPERIMENT_REFRESHED,
            source="experiment_manager"
        ))
    
    def on_experiment_changed(self, index):
        """Handle experiment dropdown change."""
        experiments = self.experiment_service.get_experiments()
        if 0 <= index < len(experiments):
            selected_experiment = experiments[index]
            self.experiment_service.set_current_experiment(selected_experiment)
            self.experiment_changed.emit(selected_experiment)
            
            # Publish global event
            event_bus.publish(Event(
                event_type=EventType.EXPERIMENT_CHANGED,
                data={"experiment": selected_experiment},
                source="experiment_manager"
            ))
    
    def get_current_experiment(self):
        """Get the currently selected experiment."""
        return self.experiment_service.get_current_experiment()
