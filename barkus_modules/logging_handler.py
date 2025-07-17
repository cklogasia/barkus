"""
Logging Handler Module

This module provides logging functionality for the Barkus PDF barcode splitter.
Handles both console output and file logging with timestamps.
"""

import sys
import logging
from datetime import datetime


class VerbosityHandler:
    """
    Handles logging output to both console and file.
    
    This class provides a unified interface for logging messages at different levels
    (info, warning, error) while supporting both console output and file logging.
    """
    
    def __init__(self, verbose: bool = True, log_file: str = None):
        """
        Initialize the verbosity handler.
        
        Args:
            verbose (bool): Whether to display messages to console
            log_file (str): Path to log file for detailed logging
        """
        self.verbose = verbose
        self.log_file = log_file
        self.log_file_handle = None
        
        if self.log_file:
            self._open_log_file()
    
    def _open_log_file(self) -> None:
        """Open the log file for writing."""
        try:
            self.log_file_handle = open(self.log_file, 'a', encoding='utf-8')
        except Exception as e:
            print(f"Warning: Could not open log file {self.log_file}: {e}", file=sys.stderr)
    
    def _write_to_log_file(self, message: str) -> None:
        """
        Write a message to the log file with timestamp.
        
        Args:
            message (str): The message to write
        """
        if self.log_file_handle:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.log_file_handle.write(f"[{timestamp}] {message}\n")
            self.log_file_handle.flush()
    
    def info(self, message: str) -> None:
        """
        Log an info message.
        
        Args:
            message (str): The info message to log
        """
        logger = logging.getLogger('barkus')
        logger.info(message)
        self._write_to_log_file(f"INFO: {message}")
        if self.verbose:
            print(message)
    
    def warning(self, message: str) -> None:
        """
        Log a warning message.
        
        Args:
            message (str): The warning message to log
        """
        logger = logging.getLogger('barkus')
        logger.warning(message)
        self._write_to_log_file(f"WARNING: {message}")
        if self.verbose:
            print(f"Warning: {message}")
    
    def error(self, message: str) -> None:
        """
        Log an error message.
        
        Args:
            message (str): The error message to log
        """
        logger = logging.getLogger('barkus')
        logger.error(message)
        self._write_to_log_file(f"ERROR: {message}")
        print(f"Error: {message}", file=sys.stderr)
    
    def close(self) -> None:
        """Close the log file handle."""
        if self.log_file_handle:
            self.log_file_handle.close()
            self.log_file_handle = None


def configure_logging() -> None:
    """Configure the basic logging settings for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )