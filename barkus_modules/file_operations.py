"""
File Operations Module

This module handles file operations for the Barkus PDF barcode splitter.
Includes CSV logging and file management utilities.
"""

import os
import csv
from datetime import datetime
from typing import List, Dict, Any, Optional

from .logging_handler import VerbosityHandler


class FileOperations:
    """
    Handles file operations and CSV logging for the Barkus application.
    
    This class provides utilities for writing CSV logs and managing
    file operations related to the PDF processing workflow.
    """
    
    @staticmethod
    def write_csv_log(output_directory: str, extraction_data: List[Dict[str, Any]], verbose: bool = True) -> Optional[str]:
        """
        Write CSV log file with extraction details.
        
        Args:
            output_directory (str): Directory where CSV log will be saved
            extraction_data (List[Dict[str, Any]]): List of dictionaries containing extraction details
            verbose (bool): Whether to display progress information
            
        Returns:
            Optional[str]: Path to the created CSV file, or None if failed
        """
        vh = VerbosityHandler(verbose)
        
        csv_filename = os.path.join(output_directory, f"extraction_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        
        try:
            with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['SequenceNo', 'DateTime', 'Barcode1', 'Barcode2', 'OutputPath']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                
                for row in extraction_data:
                    writer.writerow(row)
            
            vh.info(f"CSV log written to: {csv_filename}")
            return csv_filename
            
        except Exception as e:
            vh.error(f"Failed to write CSV log: {str(e)}")
            import logging
            logging.getLogger('barkus').exception("Exception writing CSV log")
            return None
        finally:
            vh.close()
    
    @staticmethod
    def create_log_file_path(output_directory: str, prefix: str = "barkus_detailed_log") -> str:
        """
        Create a timestamped log file path.
        
        Args:
            output_directory (str): Directory where log file will be saved
            prefix (str): Prefix for the log filename
            
        Returns:
            str: Path to the log file
        """
        os.makedirs(output_directory, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return os.path.join(output_directory, f"{prefix}_{timestamp}.log")
    
    @staticmethod
    def ensure_directory_exists(directory_path: str) -> None:
        """
        Ensure a directory exists, creating it if necessary.
        
        Args:
            directory_path (str): Path to the directory
        """
        os.makedirs(directory_path, exist_ok=True)
    
    @staticmethod
    def validate_input_file(file_path: str) -> bool:
        """
        Validate that an input file exists and is accessible.
        
        Args:
            file_path (str): Path to the input file
            
        Returns:
            bool: True if file exists and is accessible, False otherwise
        """
        return os.path.exists(file_path) and os.path.isfile(file_path)
    
    @staticmethod
    def get_file_size(file_path: str) -> int:
        """
        Get the size of a file in bytes.
        
        Args:
            file_path (str): Path to the file
            
        Returns:
            int: File size in bytes, or 0 if file doesn't exist
        """
        try:
            return os.path.getsize(file_path)
        except (OSError, FileNotFoundError):
            return 0
    
    @staticmethod
    def clean_filename(filename: str) -> str:
        """
        Clean a filename by removing or replacing invalid characters.
        
        Args:
            filename (str): Original filename
            
        Returns:
            str: Cleaned filename safe for filesystem use
        """
        # Characters that are problematic on various filesystems
        invalid_chars = '<>:"/\\|?*'
        return ''.join('_' if c in invalid_chars else c for c in filename)
    
    @staticmethod
    def create_backup_filename(original_path: str) -> str:
        """
        Create a backup filename with timestamp.
        
        Args:
            original_path (str): Path to the original file
            
        Returns:
            str: Backup filename with timestamp
        """
        directory = os.path.dirname(original_path)
        filename = os.path.basename(original_path)
        name, ext = os.path.splitext(filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return os.path.join(directory, f"{name}_backup_{timestamp}{ext}")
    
    @staticmethod
    def get_available_disk_space(directory: str) -> int:
        """
        Get available disk space in bytes for a directory.
        
        Args:
            directory (str): Directory path to check
            
        Returns:
            int: Available disk space in bytes
        """
        try:
            stat = os.statvfs(directory)
            return stat.f_bavail * stat.f_frsize
        except (OSError, AttributeError):
            # AttributeError for Windows (statvfs not available)
            # Return a large number as fallback
            return 10 * 1024 * 1024 * 1024  # 10 GB
    
    @staticmethod
    def list_pdf_files(directory: str) -> List[str]:
        """
        List all PDF files in a directory.
        
        Args:
            directory (str): Directory to search
            
        Returns:
            List[str]: List of PDF file paths
        """
        pdf_files = []
        try:
            for filename in os.listdir(directory):
                if filename.lower().endswith('.pdf'):
                    pdf_files.append(os.path.join(directory, filename))
        except (OSError, FileNotFoundError):
            pass
        return sorted(pdf_files)
    
    @staticmethod
    def count_files_in_directory(directory: str, extension: str = None) -> int:
        """
        Count files in a directory, optionally filtered by extension.
        
        Args:
            directory (str): Directory to count files in
            extension (str): Optional file extension to filter by (e.g., '.pdf')
            
        Returns:
            int: Number of files found
        """
        try:
            files = os.listdir(directory)
            if extension:
                files = [f for f in files if f.lower().endswith(extension.lower())]
            return len(files)
        except (OSError, FileNotFoundError):
            return 0