"""
Application Module

Main application logic for the Barkus PDF barcode splitter.
Orchestrates all components to process PDF documents.
"""

import os
from typing import Dict, Any, Optional

from .logging_handler import VerbosityHandler, configure_logging
from .pdf_processor import PDFProcessor
from .file_operations import FileOperations


class BarkusApplication:
    """
    Main application class for the Barkus PDF barcode splitter.
    
    This class orchestrates all components to process PDF documents,
    extract barcodes, and split them into separate files.
    """
    
    def __init__(self):
        """Initialize the Barkus application."""
        configure_logging()
        self.pdf_processor = PDFProcessor()
        self.file_operations = FileOperations()
    
    def process_pdf(self, input_pdf_path: str, output_directory: str = "output", 
                   handle_no_barcode: str = "ignore", dpi: int = 300, verbose: bool = True) -> Dict[str, Any]:
        """
        Main processing function for PDF barcode splitting.
        
        Args:
            input_pdf_path (str): Path to the input PDF file
            output_directory (str): Directory to save split PDFs
            handle_no_barcode (str): How to handle pages without barcodes:
                                     - "ignore": Skip pages without barcodes (default)
                                     - "separate": Create a separate PDF for pages without barcodes
                                     - "keep_with_previous": Include pages with the previous barcode group
                                     - "sequential": Include pages with no barcode with the last detected barcode
            dpi (int): DPI for rendering PDF pages for barcode detection
            verbose (bool): Whether to display progress information
            
        Returns:
            Dict[str, Any]: Processing results including file paths and statistics
        """
        # Validate input file
        if not self.file_operations.validate_input_file(input_pdf_path):
            return {"error": f"Input file not found: {input_pdf_path}"}
        
        # Create output directory and log file
        self.file_operations.ensure_directory_exists(output_directory)
        log_file = self.file_operations.create_log_file_path(output_directory)
        
        vh = VerbosityHandler(verbose, log_file)
        
        try:
            # Step 1: Split PDF by barcodes
            barcode_pages, csv_data, no_barcode_pages = self.pdf_processor.split_pdf_by_barcodes(
                input_pdf_path, output_directory, dpi, verbose, log_file
            )
            
            # Step 2: Handle pages without barcodes if requested
            if handle_no_barcode != "ignore":
                barcode_pages = self.pdf_processor.handle_pages_without_barcodes(
                    input_pdf_path, output_directory, barcode_pages, no_barcode_pages, handle_no_barcode, verbose, log_file
                )
            
            # Step 3: Count pages without barcodes
            no_barcode_page_count = len(no_barcode_pages) if handle_no_barcode == "ignore" else 0
            
            # Step 4: Write CSV log if there's data
            csv_file_path = None
            if csv_data:
                csv_file_path = self.file_operations.write_csv_log(output_directory, csv_data, verbose)
            
            # Step 5: Prepare results
            processed_results = self._prepare_results(barcode_pages)
            
            return {
                "input_file": input_pdf_path,
                "output_directory": output_directory,
                "barcode_count": len(barcode_pages),
                "no_barcode_pages": no_barcode_page_count,
                "csv_log_file": csv_file_path,
                "detailed_log_file": log_file,
                "results": processed_results
            }
            
        except Exception as e:
            vh.error(f"Processing failed: {str(e)}")
            import logging
            logging.getLogger('barkus').exception("Exception in process_pdf")
            return {"error": str(e)}
        finally:
            vh.close()
    
    def _count_pages_without_barcodes(self, input_pdf_path: str, barcode_pages: Dict) -> int:
        """
        Count pages that don't have barcodes.
        
        Args:
            input_pdf_path (str): Path to the input PDF
            barcode_pages (Dict): Dictionary of barcode pages
            
        Returns:
            int: Number of pages without barcodes
        """
        try:
            import pikepdf
            with pikepdf.open(input_pdf_path) as pdf_document:
                total_pages = len(pdf_document.pages)
                pages_with_barcodes = set()
                
                for pages in barcode_pages.values():
                    pages_with_barcodes.update(pages)
                
                return total_pages - len(pages_with_barcodes)
        except Exception:
            return 0
    
    def _prepare_results(self, barcode_pages: Dict) -> Dict[str, Dict[str, Any]]:
        """
        Prepare processing results in a standardized format.
        
        Args:
            barcode_pages (Dict): Dictionary of barcode pages
            
        Returns:
            Dict[str, Dict[str, Any]]: Formatted results
        """
        processed_results = {}
        
        for barcode_tuple, pages in barcode_pages.items():
            delivery_number, customer_name = barcode_tuple
            key = f"{delivery_number}_{customer_name}"
            
            processed_results[key] = {
                "delivery_number": delivery_number,
                "customer_name": customer_name,
                "pages": pages,
                "page_count": len(pages)
            }
        
        return processed_results
    
    def get_application_info(self) -> Dict[str, Any]:
        """
        Get information about the application.
        
        Returns:
            Dict[str, Any]: Application information
        """
        return {
            "name": "Barkus PDF Barcode Splitter",
            "version": "1.0.0",
            "description": "Splits PDF documents based on barcode detection",
            "supported_formats": ["PDF"],
            "barcode_types": ["Delivery Numbers (DO* or numeric)", "Customer Names"]
        }
    
    def validate_configuration(self, config: Dict[str, Any]) -> tuple[bool, str]:
        """
        Validate application configuration.
        
        Args:
            config (Dict[str, Any]): Configuration dictionary
            
        Returns:
            tuple[bool, str]: (is_valid, error_message)
        """
        required_keys = ["input_pdf", "output_dir"]
        
        for key in required_keys:
            if key not in config:
                return False, f"Missing required configuration key: {key}"
        
        # Validate input file
        if not self.file_operations.validate_input_file(config["input_pdf"]):
            return False, f"Input PDF file not found: {config['input_pdf']}"
        
        # Validate DPI
        if "dpi" in config and not isinstance(config["dpi"], int):
            return False, "DPI must be an integer"
        
        if "dpi" in config and config["dpi"] < 50:
            return False, "DPI must be at least 50"
        
        # Validate handle_no_barcode option
        valid_handle_options = ["ignore", "separate", "keep_with_previous", "sequential"]
        if "handle_no_barcode" in config and config["handle_no_barcode"] not in valid_handle_options:
            return False, f"Invalid handle_no_barcode option. Must be one of: {valid_handle_options}"
        
        return True, ""
    
    def estimate_processing_time(self, input_pdf_path: str, dpi: int = 300) -> Optional[float]:
        """
        Estimate processing time for a PDF file.
        
        Args:
            input_pdf_path (str): Path to the input PDF
            dpi (int): DPI for processing
            
        Returns:
            Optional[float]: Estimated processing time in seconds, or None if cannot estimate
        """
        try:
            import pikepdf
            with pikepdf.open(input_pdf_path) as pdf_document:
                page_count = len(pdf_document.pages)
                
                # Rough estimate: 0.5 seconds per page at 300 DPI
                base_time_per_page = 0.5
                dpi_factor = dpi / 300.0
                
                return page_count * base_time_per_page * dpi_factor
                
        except Exception:
            return None
    
    def get_system_requirements(self) -> Dict[str, Any]:
        """
        Get system requirements for the application.
        
        Returns:
            Dict[str, Any]: System requirements information
        """
        return {
            "python_version": "3.7+",
            "required_packages": [
                "pikepdf",
                "opencv-python",
                "numpy",
                "pdf2image",
                "zxing-cpp"
            ],
            "system_dependencies": [
                "poppler-utils (for pdf2image)"
            ],
            "minimum_ram": "2 GB",
            "recommended_ram": "4 GB",
            "disk_space": "Varies based on input PDF size"
        }