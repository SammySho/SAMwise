"""
Drawing tools widget with brush, marker, and clear buttons.
"""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QButtonGroup, QVBoxLayout, QLabel, QSlider, QCheckBox, QGroupBox
from PySide6.QtCore import Qt, Signal
from core.events import event_bus, Event, EventType
from core.base import ToolType


class DrawingTools(QWidget):
    """Widget containing drawing tools and controls."""
    
    # Signals for tool changes
    tool_changed = Signal(str)  # ToolType value
    brush_size_changed = Signal(int)
    opacity_changed = Signal(int)
    auto_sam_toggled = Signal(bool)  # Auto SAM checkbox state
    threshold_applied = Signal(int)  # Threshold value
    
    def __init__(self):
        super().__init__()
        self.current_tool = ToolType.BRUSH
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface."""
        main_layout = QVBoxLayout()
        
        # Main mask tools group
        mask_tools_group = QGroupBox("Mask Tools")
        mask_tools_layout = QVBoxLayout()
        
        # Brush tools section
        brush_group = QGroupBox("Brush")
        brush_layout = QVBoxLayout()
        
        # Brush button
        self.brush_btn = QPushButton("Brush")
        self.brush_btn.setCheckable(True)
        self.brush_btn.setChecked(True)
        self.brush_btn.setToolTip("Draw mask manually")
        brush_layout.addWidget(self.brush_btn)
        
        # Brush controls
        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("Size:"))
        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setRange(1, 200)
        self.size_slider.setValue(25)
        self.size_label = QLabel("25")
        size_layout.addWidget(self.size_slider)
        size_layout.addWidget(self.size_label)
        brush_layout.addLayout(size_layout)
        
        opacity_layout = QHBoxLayout()
        opacity_layout.addWidget(QLabel("Opacity:"))
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(50)
        self.opacity_label = QLabel("50%")
        opacity_layout.addWidget(self.opacity_slider)
        opacity_layout.addWidget(self.opacity_label)
        brush_layout.addLayout(opacity_layout)
        
        brush_group.setLayout(brush_layout)
        
        # SAM tools section
        sam_group = QGroupBox("SAM")
        sam_layout = QVBoxLayout()
        
        # Marker button
        self.marker_btn = QPushButton("Marker")
        self.marker_btn.setCheckable(True)
        self.marker_btn.setToolTip("Click to place markers for SAM segmentation")
        sam_layout.addWidget(self.marker_btn)
        
        # Auto SAM checkbox on same row as marker
        auto_sam_row = QHBoxLayout()
        self.auto_sam_checkbox = QCheckBox("Auto SAM")
        self.auto_sam_checkbox.setToolTip("Automatically apply SAM using the largest region in the image")
        self.auto_sam_checkbox.stateChanged.connect(self.on_auto_sam_toggled)
        auto_sam_row.addWidget(self.auto_sam_checkbox)
        auto_sam_row.addStretch()  # Push checkbox to left
        sam_layout.addLayout(auto_sam_row)
        
        sam_group.setLayout(sam_layout)
        
        # Threshold section
        threshold_group = QGroupBox("Threshold")
        threshold_layout = QVBoxLayout()
        
        # Threshold button
        self.threshold_button = QPushButton("Apply Threshold")
        self.threshold_button.clicked.connect(self.on_threshold_clicked)
        threshold_layout.addWidget(self.threshold_button)
        
        # Threshold slider
        threshold_slider_layout = QHBoxLayout()
        self.threshold_slider = QSlider(Qt.Horizontal)
        self.threshold_slider.setRange(0, 255)
        self.threshold_slider.setValue(127)
        self.threshold_slider.valueChanged.connect(self.on_threshold_changed)
        self.threshold_label = QLabel("127")
        self.threshold_label.setMinimumWidth(30)
        threshold_slider_layout.addWidget(self.threshold_slider)
        threshold_slider_layout.addWidget(self.threshold_label)
        threshold_layout.addLayout(threshold_slider_layout)
        
        threshold_group.setLayout(threshold_layout)
        
        # Clear button
        self.clear_btn = QPushButton("Clear Mask")
        self.clear_btn.setToolTip("Clear current mask")
        
        # Add all sections to mask tools
        mask_tools_layout.addWidget(brush_group)
        mask_tools_layout.addWidget(sam_group)
        mask_tools_layout.addWidget(threshold_group)
        mask_tools_layout.addWidget(self.clear_btn)
        
        mask_tools_group.setLayout(mask_tools_layout)
        main_layout.addWidget(mask_tools_group)
        
        self.setLayout(main_layout)
        
        # Create button group for exclusive tool selection
        self.tool_group = QButtonGroup()
        self.tool_group.addButton(self.brush_btn, 0)
        self.tool_group.addButton(self.marker_btn, 1)
        
        # Connect signals
        self.tool_group.buttonClicked.connect(self.on_tool_changed)
        self.clear_btn.clicked.connect(self.on_clear_clicked)
        self.size_slider.valueChanged.connect(self.on_size_changed)
        self.opacity_slider.valueChanged.connect(self.on_opacity_changed)
        self.threshold_slider.valueChanged.connect(self.on_threshold_changed)
    
    def on_tool_changed(self, button):
        """Handle tool selection change."""
        if button == self.brush_btn:
            self.current_tool = ToolType.BRUSH
        elif button == self.marker_btn:
            self.current_tool = ToolType.MARKER
        
        # Emit local signal
        self.tool_changed.emit(self.current_tool.value)
        
        # Publish global event
        event_bus.publish(Event(
            event_type=EventType.TOOL_CHANGED,
            data={"tool": self.current_tool.value},
            source="drawing_tools"
        ))
    
    def on_clear_clicked(self):
        """Handle clear button click."""
        event_bus.publish(Event(
            event_type=EventType.MASK_CLEARED,
            source="drawing_tools"
        ))
    
    def on_size_changed(self, value):
        """Handle brush size change."""
        self.size_label.setText(str(value))
        self.brush_size_changed.emit(value)
    
    def on_opacity_changed(self, value):
        """Handle opacity change."""
        self.opacity_label.setText(f"{value}%")
        self.opacity_changed.emit(value)
    
    def on_auto_sam_toggled(self, state):
        """Handle Auto SAM checkbox state change."""
        # Use the checkbox's isChecked() method for reliable state detection
        is_checked = self.auto_sam_checkbox.isChecked()

        self.auto_sam_toggled.emit(is_checked)
        
        # Publish global event
        event_bus.publish(Event(
            event_type=EventType.AUTO_SAM_TOGGLED,
            data={"enabled": is_checked},
            source="drawing_tools"
        ))
    
    def on_threshold_changed(self, value):
        """Handle threshold slider change."""
        self.threshold_label.setText(str(value))
    
    def on_threshold_clicked(self):
        """Handle threshold button click."""
        threshold_value = self.threshold_slider.value()
        self.threshold_applied.emit(threshold_value)
    
    def get_current_tool(self) -> ToolType:
        """Get the currently selected tool."""
        return self.current_tool
    
    def set_tool(self, tool: ToolType):
        """Programmatically set the current tool."""
        if tool == ToolType.BRUSH:
            self.brush_btn.setChecked(True)
        elif tool == ToolType.MARKER:
            self.marker_btn.setChecked(True)
        
        self.current_tool = tool
    
    def is_auto_sam_enabled(self) -> bool:
        """Check if Auto SAM checkbox is enabled."""
        return self.auto_sam_checkbox.isChecked()
    
    def set_tools_enabled(self, enabled: bool):
        """Enable/disable drawing tools based on image availability."""
        self.brush_btn.setEnabled(enabled)
        self.marker_btn.setEnabled(enabled)
        self.auto_sam_checkbox.setEnabled(enabled)
        self.threshold_button.setEnabled(enabled)
        self.clear_btn.setEnabled(enabled)
