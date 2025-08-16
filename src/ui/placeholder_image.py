"""
Create a placeholder image for the canvas when no images are loaded.
"""
from PySide6.QtGui import QImage, QPainter, QFont, QColor

def create_placeholder_image(width: int = 500, height: int = 500, message_type: str = "default") -> QImage:
    """Create a placeholder image with app logo/text."""
    # Create image
    image = QImage(width, height, QImage.Format_RGB32)
    image.fill(QColor(240, 240, 240))  # Light gray background
    
    # Create painter
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)
    
    # Draw border
    painter.setPen(QColor(200, 200, 200))
    painter.drawRect(10, 10, width-20, height-20)
    
    # Draw title
    title_font = QFont("Arial", 24, QFont.Bold)
    painter.setFont(title_font)
    painter.setPen(QColor(100, 100, 100))
    
    title_rect = painter.fontMetrics().boundingRect("Image Segmentation")
    title_x = (width - title_rect.width()) // 2
    title_y = height // 2 - 50
    painter.drawText(title_x, title_y, "Image Segmentation")
    
    # Draw instructions
    instruction_font = QFont("Arial", 12)
    painter.setFont(instruction_font)
    painter.setPen(QColor(120, 120, 120))
    
    if message_type == "no_unlabelled":
        instructions = [
            "All images in selected folders have been labelled!",
            "",
            "Options:",
            "• Switch to 'Labelled' view to review masks",
            "• Select different folders",
            "• Add more images to current folders",
        ]
    elif message_type == "no_images":
        instructions = [
            "No images found in selected folders",
            "",
            "Please:",
            "• Check that folders contain image files",
            "• Select different folders",
            "• Verify experiment data directory"
        ]
    else:  # default
        instructions = [
            "1. Select an experiment from the dropdown",
            "2. Choose folders to view images from",
            "3. Click 'Get Random Image' to start",
            "",
            "Use the tools on the left to:",
            "• Draw masks with the brush tool",
            "• Place markers for SAM segmentation",
            "• Apply thresholding for auto-masks"
        ]
    
    y_offset = height // 2 + 20
    for i, instruction in enumerate(instructions):
        if instruction:  # Skip empty lines
            text_rect = painter.fontMetrics().boundingRect(instruction)
            text_x = (width - text_rect.width()) // 2
            painter.drawText(text_x, y_offset + i * 25, instruction)
        else:
            y_offset += 10  # Extra space for empty lines
    
    painter.end()
    return image
