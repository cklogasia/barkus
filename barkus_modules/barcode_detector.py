"""
Barcode Detection Module

This module handles barcode detection and validation for the Barkus PDF barcode splitter.
Includes content-based classification and retry logic for missing barcodes.
"""

import cv2
import numpy as np
from pdf2image import convert_from_path
import zxingcpp
from typing import Dict, List, Optional, Tuple

from .logging_handler import VerbosityHandler


class BarcodeClassifier:
    """
    Handles classification of barcodes based on their content.
    
    This class determines whether a barcode represents a delivery number
    or customer name based on predefined rules.
    """
    
    @staticmethod
    def is_delivery_number(barcode_text: str) -> bool:
        """
        Check if a barcode text represents a delivery number.
        
        Delivery numbers start with 'DO' (case insensitive) or with a digit.
        
        Args:
            barcode_text (str): The barcode text to check
            
        Returns:
            bool: True if the text appears to be a delivery number, False otherwise
        """
        if not barcode_text:
            return False
        
        text = str(barcode_text).strip().upper()
        if not text:  # Handle empty strings after stripping
            return False
            
        return text.startswith('DO') or text[0].isdigit()


class BarcodeDetector:
    """
    Handles barcode detection from PDF pages with retry logic.
    
    This class processes PDF pages to extract barcodes and classify them
    as delivery numbers or customer names, with retry functionality for
    missing barcodes.
    """
    
    def __init__(self, max_retries: int = 10):
        """
        Initialize the barcode detector.
        
        Args:
            max_retries (int): Maximum number of retry attempts for missing barcodes
        """
        self.max_retries = max_retries
        self.classifier = BarcodeClassifier()
    
    def _detect_barcodes_from_image(self, img_cv: np.ndarray, page_num: int, vh: VerbosityHandler) -> Dict[str, Optional[str]]:
        """
        Extract barcodes from a single page image.
        
        Args:
            img_cv (np.ndarray): OpenCV image of the page
            page_num (int): Page number (0-based)
            vh (VerbosityHandler): Verbosity handler for logging
            
        Returns:
            Dict[str, Optional[str]]: Dictionary with 'delivery_number' and 'customer_name' keys
        """
        # Detect barcodes
        detected_barcodes = zxingcpp.read_barcodes(img_cv)
        
        barcode_info = {
            'delivery_number': None,
            'customer_name': None
        }
        
        if detected_barcodes:
            # Separate barcodes into delivery numbers and customer names based on content
            delivery_barcodes = []
            customer_barcodes = []
            
            for bc in detected_barcodes:
                if self.classifier.is_delivery_number(bc.text):
                    delivery_barcodes.append(bc)
                else:
                    customer_barcodes.append(bc)
            
            # Handle delivery numbers
            if delivery_barcodes:
                barcode_info['delivery_number'] = delivery_barcodes[0].text
                if len(delivery_barcodes) > 1:
                    extra_delivery = [bc.text for bc in delivery_barcodes[1:]]
                    vh.warning(f"  Multiple delivery number barcodes found on page {page_num+1}, using first one: {barcode_info['delivery_number']}")
                    vh.warning(f"  Unused delivery number barcodes: {', '.join(extra_delivery)}")
            
            # Handle customer names
            if customer_barcodes:
                barcode_info['customer_name'] = customer_barcodes[0].text
                if len(customer_barcodes) > 1:
                    extra_customer = [bc.text for bc in customer_barcodes[1:]]
                    vh.warning(f"  Multiple customer name barcodes found on page {page_num+1}, using first one: {barcode_info['customer_name']}")
                    vh.warning(f"  Unused customer name barcodes: {', '.join(extra_customer)}")
        
        return barcode_info
    
    def _detect_with_retry(self, img_cv: np.ndarray, page_num: int, vh: VerbosityHandler) -> Dict[str, Optional[str]]:
        """
        Extract barcodes with retry logic for missing barcode types.
        
        Args:
            img_cv (np.ndarray): OpenCV image of the page
            page_num (int): Page number (0-based)
            vh (VerbosityHandler): Verbosity handler for logging
            
        Returns:
            Dict[str, Optional[str]]: Dictionary with 'delivery_number' and 'customer_name' keys
        """
        for attempt in range(self.max_retries + 1):  # +1 for initial attempt
            barcode_info = self._detect_barcodes_from_image(img_cv, page_num, vh)
            
            # Check if we have both required barcode types
            has_delivery = barcode_info['delivery_number'] is not None
            has_customer = barcode_info['customer_name'] is not None
            
            if has_delivery and has_customer:
                # Both found, we're done
                if attempt > 0:
                    vh.info(f"  Successfully found both barcodes on page {page_num+1} after {attempt} retries")
                return barcode_info
            elif attempt < self.max_retries:
                # Missing one or both, retry
                missing = []
                if not has_delivery:
                    missing.append("delivery number")
                if not has_customer:
                    missing.append("customer name")
                
                vh.warning(f"  Missing {' and '.join(missing)} barcode(s) on page {page_num+1}, retrying... (attempt {attempt+1}/{self.max_retries})")
            else:
                # Final attempt failed
                missing = []
                if not has_delivery:
                    missing.append("delivery number")
                if not has_customer:
                    missing.append("customer name")
                
                error_msg = f"Failed to detect {' and '.join(missing)} barcode(s) on page {page_num+1} after {self.max_retries} retries"
                vh.error(error_msg)
                return barcode_info
        
        return barcode_info
    
    def extract_barcodes_from_pdf(self, pdf_path: str, dpi: int = 300, verbose: bool = True, log_file: str = None) -> Dict[int, Dict[str, Optional[str]]]:
        """
        Extract delivery number and customer name barcodes from each page of a PDF document.
        
        Args:
            pdf_path (str): Path to the PDF file
            dpi (int): DPI for rendering PDF pages (higher values may improve barcode detection)
            verbose (bool): Whether to display progress information
            log_file (str): Path to log file for detailed logging
            
        Returns:
            Dict[int, Dict[str, Optional[str]]]: Dictionary mapping page numbers to barcode information
        """
        import pikepdf
        
        vh = VerbosityHandler(verbose, log_file)
        page_barcodes = {}
        
        try:
            # Load PDF with pikepdf
            with pikepdf.open(pdf_path) as pdf_document:
                total_pages = len(pdf_document.pages)
                
                vh.info(f"Processing {total_pages} pages for barcodes...")
                
                # Convert PDF to images using pdf2image
                images = convert_from_path(pdf_path, dpi=dpi)
                
                for page_num, img in enumerate(images):
                    if total_pages > 10 and page_num % 5 == 0:
                        vh.info(f"  Processing page {page_num+1}/{total_pages}...")
                        
                    try:
                        # Convert PIL Image to OpenCV format
                        img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
                        
                        # Use retry logic to extract barcodes
                        barcode_info = self._detect_with_retry(img_cv, page_num, vh)
                        
                        # Only store if we found at least one barcode
                        if barcode_info['delivery_number'] is not None or barcode_info['customer_name'] is not None:
                            # Log what we found
                            vh.info(f"  Found barcodes on page {page_num+1}:")
                            vh.info(f"    Delivery Number: {barcode_info.get('delivery_number', 'UNKNOWN')}")
                            vh.info(f"    Customer Name: {barcode_info.get('customer_name', 'UNKNOWN')}")
                            
                            # Store the barcode information for this page
                            page_barcodes[page_num] = barcode_info
                    
                    except Exception as e:
                        vh.warning(f"Error processing page {page_num+1}: {str(e)}")
                        import logging
                        logging.getLogger('barkus').exception(f"Exception while processing page {page_num+1}")
                        continue
                
                vh.info(f"Barcode detection complete. Found barcodes on {len(page_barcodes)}/{total_pages} pages.")
            
        except Exception as e:
            vh.error(f"Failed to process PDF: {str(e)}")
            import logging
            logging.getLogger('barkus').exception("Exception in extract_barcodes_from_pdf")
            raise
        finally:
            vh.close()
        
        return page_barcodes
    
    def group_pages_by_barcode(self, page_barcodes: Dict[int, Dict[str, Optional[str]]]) -> Dict[Tuple[str, str], List[int]]:
        """
        Group page numbers by combined delivery number and customer name barcodes.
        
        Args:
            page_barcodes (Dict[int, Dict[str, Optional[str]]]): Dictionary mapping page numbers to barcode info
                                 
        Returns:
            Dict[Tuple[str, str], List[int]]: Dictionary mapping (delivery_number, customer_name) tuples to lists of page numbers
        """
        from collections import defaultdict
        
        barcode_pages = defaultdict(list)
        
        for page_num, barcode_info in page_barcodes.items():
            delivery_number = barcode_info.get('delivery_number', 'UNKNOWN')
            customer_name = barcode_info.get('customer_name', 'UNKNOWN')
            
            # Use a tuple of both barcode types as the key to group pages
            barcode_key = (delivery_number, customer_name)
            barcode_pages[barcode_key].append(page_num)
        
        return barcode_pages