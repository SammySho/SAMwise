import cv2
import numpy as np
from PySide6.QtGui import QImage

def threshold_image(filepath: str, threshold: int) -> QImage:
    # Load the 16-bit image using OpenCV
    image = cv2.imread(filepath, cv2.IMREAD_UNCHANGED)
    
    if image is None:
        raise ValueError("Image not found or unable to load.")

    # Check if the image is 16-bit
    if image.dtype != np.uint16:
        raise ValueError("Image is not 16-bit.")

    # Normalize the 16-bit image to 8-bit
    image_8bit = cv2.convertScaleAbs(image, alpha=(255.0/65535.0))

    # Normalize the 16-bit image to 8-bit
    image_8bit = cv2.convertScaleAbs(image, alpha=(255.0 / 65535.0))

    # Apply the threshold
    _, binary_mask = cv2.threshold(image_8bit, threshold, 255, cv2.THRESH_BINARY)

    # Create an empty ARGB image
    height, width = binary_mask.shape
    mask = np.zeros((height, width, 4), dtype=np.uint8)

    # Set white pixels to transparent
    mask[binary_mask == 255] = [0, 0, 0, 0]

    # Set black pixels to fully red
    mask[binary_mask == 0] = [255, 0, 0, 255]

    # Convert the mask to QImage
    qimage = QImage(mask.data, width, height, QImage.Format_ARGB32)
    
    return qimage