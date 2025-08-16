"""
Organoid Segmentation Application

A PyQt-based desktop application for segmenting organoid images using 
manual drawing tools, threshold-based segmentation, and the Segment 
Anything Model (SAM) for semi-automated annotation.

This application is designed for research purposes and provides an 
intuitive interface for creating precise masks for organoid analysis.
"""

import sys
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow
from utils.logging_config import setup_logging, get_logger

def main():
    """Initialize and run the application."""
    # Set up logging before anything else
    setup_logging()
    logger = get_logger(__name__)
    
    logger.info("Starting Organoid Segmentation Application")
    app = QApplication(sys.argv)

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