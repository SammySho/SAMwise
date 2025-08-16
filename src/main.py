"""
Organoid Segmentation Application

A PyQt-based desktop application for segmenting organoid images using 
manual drawing tools, threshold-based segmentation, and the Segment 
Anything Model (SAM) for semi-automated annotation.

This application is designed for research purposes and provides an 
intuitive interface for creating precise masks for organoid analysis.
"""
import os
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from ui.main_window import MainWindow
from ui.stylesheet import get_base_stylesheet
from utils.logging_config import setup_logging, get_logger

def setup_application_icon():
    """
    Setup application icon.
    
    Returns:
        QIcon or None: The application icon if found, None otherwise.
    """
    icon_path = os.path.join("Assets", "thumb.png")
    if os.path.isfile(icon_path):
        icon = QIcon(icon_path)
        if not icon.isNull():
            return icon
    
    return None

def main():
    """Initialize and run the application."""
    # Set up logging before anything else
    setup_logging()
    logger = get_logger(__name__)

    # Create the QApplication
    app = QApplication(sys.argv)
    app.setStyleSheet(get_base_stylesheet())

    # Set application icon
    icon = setup_application_icon()
    if icon:
        app.setWindowIcon(icon)
        logger.info("Application icon set successfully")
    
    logger.info("Starting Segment Wise")

    # Create the main window
    window = MainWindow()
    
    # Show the main window
    window.show()
    
    # Execute the application's main loop
    logger.info("Application started successfully")
    exit_code = app.exec()
    logger.info(f"Application exiting with code: {exit_code}")
    sys.exit(exit_code)

if __name__ == '__main__':
    main()