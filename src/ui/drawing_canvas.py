"""
Drawing canvas with multi-tool support for mask creation and editing.
"""

from PySide6.QtWidgets import QLabel, QApplication
from PySide6.QtGui import QPainter, QImage, QPen, QColor, QWheelEvent
from PySide6.QtCore import Qt, QPoint, QRect, QByteArray, QBuffer, QIODevice, Signal
from utils.image_processing import threshold_image
import numpy as np
import cv2
from ui.placeholder_image import create_placeholder_image
from core.events import event_bus, Event, EventType
from core.base import ToolType


class DrawingCanvas(QLabel):
    """
    Interactive canvas for image display and mask editing with multiple tools.
    """
    
    # Signals
    point_clicked = Signal(QPoint)  # For SAM marker placement
    mask_changed = Signal()
    
    def __init__(self):
        super().__init__()
        self.image = QImage()
        self.mask = QImage()
        self.scaled_image = QImage()
        self.scaled_mask = QImage()
        
        # Drawing state
        self.drawing = False
        self.erasing = False
        self.panning = False
        self.current_tool = ToolType.BRUSH
        
        # Mouse tracking
        self.lastPoint = QPoint()
        self.panStart = QPoint()
        self.panOffset = QPoint()
        self.current_pos = QPoint()
        self.show_cursor = False
        
        # Drawing properties
        self.penColor = Qt.blue
        self.penWidth = 25
        self.opacity = 50
        self.scale_factor = 0.18
        self.min_scale_factor = 0.18  # Will be updated based on image size
        
        # SAM markers
        self.sam_markers = []  # List of QPoint markers for SAM
        
        # Enable mouse tracking
        self.setMouseTracking(True)
        
        # Connect to events
        self.connect_events()
    
    def connect_events(self):
        """Connect to application events."""
        event_bus.subscribe(EventType.TOOL_CHANGED, self.on_tool_changed)
        event_bus.subscribe(EventType.MASK_CLEARED, self.on_mask_cleared)
    
    def on_tool_changed(self, event):
        """Handle tool change event."""
        tool_value = event.data["tool"]
        # Convert string value back to ToolType enum
        if tool_value == "brush":
            self.current_tool = ToolType.BRUSH
        elif tool_value == "marker":
            self.current_tool = ToolType.MARKER
        elif tool_value == "eraser":
            self.current_tool = ToolType.ERASER
        
        # Clear SAM markers when switching away from marker tool
        if self.current_tool != ToolType.MARKER:
            self.sam_markers.clear()
            self.update()
    
    def on_mask_cleared(self, event):
        """Handle mask clear event."""
        self.clearMask()
        self.sam_markers.clear()
    
    def paintEvent(self, event):
        """Paint the canvas."""
        painter = QPainter(self)
        
        if not self.scaled_image.isNull():
            # Calculate the drawing rectangle
            rect = QRect(self.panOffset.x(), self.panOffset.y(), 
                        self.scaled_image.width(), self.scaled_image.height())
            painter.drawImage(rect, self.scaled_image)
            
            # Set the opacity for the mask
            painter.setOpacity(self.opacity / 100.0)
            painter.drawImage(rect, self.scaled_mask)
            painter.setOpacity(1.0)  # Reset opacity
            
            # Draw SAM markers
            self.draw_sam_markers(painter, rect)
        
        # Draw the ghost cursor
        if self.show_cursor and self.current_tool == ToolType.BRUSH:
            cursor_radius = int(self.penWidth / 2 * self.scale_factor)
            painter.setPen(QPen(Qt.red, 1, Qt.SolidLine))
            painter.drawEllipse(self.current_pos, cursor_radius, cursor_radius)
        elif self.show_cursor and self.current_tool == ToolType.MARKER:
            # Draw crosshair for marker tool
            painter.setPen(QPen(Qt.red, 2, Qt.SolidLine))
            painter.drawLine(self.current_pos.x() - 10, self.current_pos.y(),
                           self.current_pos.x() + 10, self.current_pos.y())
            painter.drawLine(self.current_pos.x(), self.current_pos.y() - 10,
                           self.current_pos.x(), self.current_pos.y() + 10)

    def draw_sam_markers(self, painter, image_rect):
        """Draw SAM markers on the canvas."""
        painter.setPen(QPen(Qt.red, 3, Qt.SolidLine))
        for i, marker in enumerate(self.sam_markers):
            # Convert marker position to screen coordinates
            screen_pos = QPoint(
                int(marker.x() * self.scale_factor + image_rect.x()),
                int(marker.y() * self.scale_factor + image_rect.y())
            )
            
            # Draw marker as a circle with number
            painter.drawEllipse(screen_pos, 8, 8)
            painter.drawText(screen_pos.x() - 4, screen_pos.y() + 4, str(i + 1))

    def mousePressEvent(self, event):
        """Handle mouse press events."""
        if self.current_tool == ToolType.BRUSH:
            if event.button() == Qt.LeftButton:
                self.drawing = True
                self.erasing = False
                self.lastPoint = self.convert_to_image_coords(event.pos())
            elif event.button() == Qt.RightButton:
                self.drawing = False
                self.erasing = True
                self.lastPoint = self.convert_to_image_coords(event.pos())
        
        elif self.current_tool == ToolType.MARKER:
            if event.button() == Qt.LeftButton:
                # Add SAM marker
                image_pos = self.convert_to_image_coords(event.pos())
                self.sam_markers.append(image_pos)
                self.point_clicked.emit(image_pos)
                self.update()
                
                # Publish event for SAM processing
                event_bus.publish(Event(
                    event_type=EventType.SAM_MARKER_ADDED,
                    data={"point": image_pos, "markers": self.sam_markers},
                    source="canvas"
                ))
            elif event.button() == Qt.RightButton:
                # Remove nearest SAM marker
                image_pos = self.convert_to_image_coords(event.pos())
                self.remove_nearest_marker(image_pos)
                self.update()
        
        if event.button() == Qt.MiddleButton:
            self.panning = True
            self.panStart = event.pos()

    def mouseMoveEvent(self, event):
        """Handle mouse move events."""
        self.current_pos = event.pos()
        self.show_cursor = True
        
        if self.current_tool == ToolType.BRUSH and not self.mask.isNull():
            if (event.buttons() & Qt.LeftButton) and self.drawing:
                current_point = self.convert_to_image_coords(event.pos())
                painter = QPainter(self.mask)
                if painter.isActive():
                    painter.setPen(QPen(self.penColor, self.penWidth, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                    painter.drawLine(self.lastPoint, current_point)
                    painter.end()
                self.lastPoint = current_point
                self.update_scaled_image()
                self.mask_changed.emit()
            elif (event.buttons() & Qt.RightButton) and self.erasing:
                current_point = self.convert_to_image_coords(event.pos())
                painter = QPainter(self.mask)
                if painter.isActive():
                    painter.setCompositionMode(QPainter.CompositionMode_Clear)
                    painter.setPen(QPen(Qt.transparent, self.penWidth, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                    painter.drawLine(self.lastPoint, current_point)
                    painter.end()
                self.lastPoint = current_point
                self.update_scaled_image()
                self.mask_changed.emit()
        
        if self.panning:
            delta = event.pos() - self.panStart
            self.panOffset += delta
            self.panStart = event.pos()
            self.adjust_pan_offset()
        
        self.update()  # Always update to show the cursor

    def mouseReleaseEvent(self, event):
        """Handle mouse release events."""
        if event.button() == Qt.LeftButton:
            self.drawing = False
        elif event.button() == Qt.RightButton:
            self.erasing = False
        elif event.button() == Qt.MiddleButton:
            self.panning = False

    def leaveEvent(self, event):
        """Handle mouse leave events."""
        self.show_cursor = False
        self.update()

    def enterEvent(self, event):
        """Handle mouse enter events."""
        self.show_cursor = True
        self.update()

    def wheelEvent(self, event: QWheelEvent):
        """Handle wheel events for zooming toward cursor position."""
        if self.image.isNull():
            return
        
        # Get the mouse position in widget coordinates
        mouse_pos = event.position().toPoint()
        
        # Convert mouse position to image coordinates before scaling
        image_pos_before = self.convert_to_image_coords(mouse_pos)
        
        # Apply zoom
        if event.angleDelta().y() > 0:
            self.scale_factor *= 1.1
        else:
            self.scale_factor /= 1.1
        
        # Prevent zooming out beyond the minimum scale (80% canvas coverage)
        if self.scale_factor < self.min_scale_factor:
            self.scale_factor = self.min_scale_factor
        
        # Update the scaled image with new scale
        self.update_scaled_image()
        
        # Calculate where the same image point would be after scaling
        new_widget_pos = QPoint(
            int(image_pos_before.x() * self.scale_factor + self.panOffset.x()),
            int(image_pos_before.y() * self.scale_factor + self.panOffset.y())
        )
        
        # Adjust pan offset to keep the mouse cursor over the same image point
        self.panOffset += mouse_pos - new_widget_pos
        
        # Ensure pan offset stays within bounds
        self.adjust_pan_offset()
        self.update()

    def loadImage(self, filePath):
        """Load an image."""
        self.image.load(filePath)
        if not self.image.isNull():
            # Auto-fit the image to canvas while respecting minimum zoom
            self.auto_fit_image()
            self.update_scaled_image()
            self.center_image()
        self.update()
        
    def loadMask(self, filePath):
        """Load a mask."""
        self.mask.load(filePath)
        if not self.mask.isNull():
            self.update_scaled_image()
            self.update()
            
    def applyThreshold(self, threshold_value, filepath):
        """Apply threshold to create mask."""
        self.mask = threshold_image(filepath, threshold_value)
        self.update_scaled_image()
        self.update()
        self.mask_changed.emit()
            
    def displayPlaceholder(self, message_type="default"):
        """Display placeholder image."""
        self.image = create_placeholder_image(500, 500, message_type)
        self.clearMask()
        self.update_scaled_image()
        self.update()
            
    def clearMask(self):
        """Clear the current mask."""
        if not self.image.isNull():
            self.mask = QImage(self.image.size(), QImage.Format_ARGB32)
            self.mask.fill(Qt.transparent)
        else:
            self.mask = QImage()
        self.sam_markers.clear()
        self.update_scaled_image()
        self.update()
        self.mask_changed.emit()
    
    def force_update(self):
        """Force a repaint."""
        self.repaint()
        QApplication.processEvents()

    def resizeEvent(self, event):
        """Handle resize events."""
        if not self.image.isNull():
            # Recalculate auto-fit when canvas is resized
            self.auto_fit_image()
            self.update_scaled_image()
            self.center_image()

    def update_scaled_image(self):
        """Update scaled versions of image and mask."""
        if not self.image.isNull():
            size = self.image.size() * self.scale_factor
            self.scaled_image = self.image.scaled(size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.scaled_mask = self.mask.scaled(size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.adjust_pan_offset()
        self.update()

    def convert_to_image_coords(self, pos):
        """Convert screen coordinates to image coordinates."""
        x = (pos.x() - self.panOffset.x()) / self.scale_factor
        y = (pos.y() - self.panOffset.y()) / self.scale_factor
        return QPoint(int(x), int(y))

    def set_opacity(self, value):
        """Set mask opacity."""
        self.opacity = value
        self.update()
        
    def set_penWidth(self, value):
        """Set pen width."""
        self.penWidth = value
        self.update()

    def set_image(self, image):
        """Set the image."""
        self.image = image
        self.update()

    def QImageToCvMat(self, incomingImage):
        """Convert QImage to OpenCV Mat format."""
        ba = QByteArray()
        buff = QBuffer(ba)
        buff.open(QIODevice.ReadWrite)
        incomingImage.save(buff, "PNG")
        fBytes = np.asarray(bytearray(ba.data()), dtype=np.uint8)
        return cv2.imdecode(fBytes, cv2.IMREAD_COLOR)

    def crop_by_mask(self):
        """Crop image by mask."""
        if self.image.isNull() or self.mask.isNull():
            return
        
        cropped_image = self.image.copy()
        
        for y in range(self.image.height()):
            for x in range(self.image.width()):
                if self.mask.pixelColor(x, y).alpha() == 0:
                    cropped_image.setPixelColor(x, y, QColor(Qt.white))
        
        cropped_np = self.QImageToCvMat(cropped_image)
        return cropped_np

    def get_mask(self):
        """Get the current mask."""
        return self.mask

    def set_mask(self, mask):
        """Set the mask."""
        self.mask = mask
        self.update_scaled_image()
        self.update()
        self.mask_changed.emit()
        
        # Publish mask created event
        event_bus.publish(Event(
            event_type=EventType.MASK_CREATED,
            data={"mask": mask},
            source="canvas"
        ))

    def auto_fit_image(self):
        """Auto-fit image to canvas and set minimum zoom for 80% coverage."""
        if self.image.isNull() or self.width() <= 0 or self.height() <= 0:
            return
        
        # Calculate scale to fit image in canvas (with some padding)
        canvas_width = max(self.width() - 20, 100)  # Leave 10px padding on each side
        canvas_height = max(self.height() - 20, 100)
        
        # Calculate scale factors for width and height
        scale_x = canvas_width / self.image.width()
        scale_y = canvas_height / self.image.height()
        
        # Use the smaller scale to ensure image fits entirely
        fit_scale = min(scale_x, scale_y)
        
        # Set this as the initial scale
        self.scale_factor = fit_scale
        
        # Calculate minimum scale for 80% canvas coverage
        coverage_target = 0.8
        min_scale_x = (canvas_width * coverage_target) / self.image.width()
        min_scale_y = (canvas_height * coverage_target) / self.image.height()
        self.min_scale_factor = min(min_scale_x, min_scale_y)

    def center_image(self):
        """Center the image in the widget."""
        if not self.scaled_image.isNull():
            self.panOffset = QPoint(
                (self.width() - self.scaled_image.width()) // 2,
                (self.height() - self.scaled_image.height()) // 2
            )

    def adjust_pan_offset(self):
        """Adjust pan offset to keep image in bounds."""
        if not self.scaled_image.isNull():
            max_offset_x = max(0, (self.width() - self.scaled_image.width()) // 2)
            max_offset_y = max(0, (self.height() - self.scaled_image.height()) // 2)
            self.panOffset.setX(max(min(self.panOffset.x(), max_offset_x), 
                                  -(self.scaled_image.width() - self.width() + max_offset_x)))
            self.panOffset.setY(max(min(self.panOffset.y(), max_offset_y), 
                                  -(self.scaled_image.height() - self.height() + max_offset_y)))
    
    def get_sam_markers(self):
        """Get list of SAM markers in image coordinates."""
        return self.sam_markers.copy()
    
    def remove_nearest_marker(self, position, threshold=20):
        """
        Remove the nearest SAM marker to the given position.
        
        Args:
            position (QPoint): Position to check for nearest marker
            threshold (int): Maximum distance in pixels to consider for removal
        """
        if not self.sam_markers:
            return
        
        nearest_index = -1
        min_distance = float('inf')
        
        # Find the nearest marker
        for i, marker in enumerate(self.sam_markers):
            distance = ((marker.x() - position.x()) ** 2 + (marker.y() - position.y()) ** 2) ** 0.5
            if distance < min_distance and distance <= threshold:
                min_distance = distance
                nearest_index = i
        
        # Remove the nearest marker if found
        if nearest_index >= 0:
            removed_marker = self.sam_markers.pop(nearest_index)

            
            # Publish event for marker removal
            event_bus.publish(Event(
                event_type=EventType.SAM_MARKER_REMOVED,
                data={"removed_point": removed_marker, "markers": self.sam_markers},
                source="canvas"
            ))
    
    def clear_sam_markers(self):
        """Clear all SAM markers."""
        self.sam_markers.clear()
        self.update()
