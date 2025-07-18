"""
PDF Processing Module

This module handles PDF splitting and page processing for the Barkus PDF barcode splitter.
Includes validation to prevent invalid PDF generation and page reassignment logic.
"""

import os
import pikepdf
from typing import Dict, List, Tuple, Optional, Any
from collections import defaultdict

from .logging_handler import VerbosityHandler
from .barcode_detector import BarcodeDetector, BarcodeDetectionResult, BarcodeDetectionStatus


class PDFProcessor:
    """
    Handles PDF processing operations including splitting and page management.
    
    This class manages the splitting of PDF documents based on barcode combinations
    and handles various edge cases like missing barcodes and page reassignment.
    """
    
    def __init__(self):
        """Initialize the PDF processor."""
        self.barcode_detector = BarcodeDetector()
    
    def _create_safe_filename(self, delivery_number: str, customer_name: str) -> str:
        """
        Create a safe filename from delivery number and customer name.
        
        Args:
            delivery_number (str): The delivery number
            customer_name (str): The customer name
            
        Returns:
            str: A safe filename for the PDF
        """
        # Only replace characters that cause issues on Windows filesystems
        # Windows disallows: < > : " / \ | ? *
        invalid_chars = '<>:"/\\|?*'
        safe_delivery = ''.join('_' if c in invalid_chars else c for c in str(delivery_number))
        safe_customer = ''.join('_' if c in invalid_chars else c for c in str(customer_name))
        
        # Use both values in filename if both are available
        # Put customer name first, then delivery number in the filename
        if delivery_number != 'UNKNOWN' and customer_name != 'UNKNOWN':
            return f"{safe_customer}_{safe_delivery}.pdf"
        elif delivery_number != 'UNKNOWN':
            return f"{safe_delivery}.pdf"
        elif customer_name != 'UNKNOWN':
            return f"{safe_customer}.pdf"
        else:
            return "unknown_barcode.pdf"
    
    def _filter_valid_barcodes(self, barcode_pages: Dict[Tuple[str, str], List[int]], vh: VerbosityHandler) -> Tuple[Dict[Tuple[str, str], List[int]], List[int]]:
        """
        Filter out barcode combinations with None values to prevent invalid PDF generation.
        
        Args:
            barcode_pages (Dict[Tuple[str, str], List[int]]): Original barcode pages mapping
            vh (VerbosityHandler): Verbosity handler for logging
            
        Returns:
            Tuple[Dict[Tuple[str, str], List[int]], List[int]]: Valid barcode pages and invalid pages
        """
        valid_barcode_pages = {}
        invalid_pages = []
        
        for barcode_tuple, page_numbers in barcode_pages.items():
            delivery_number, customer_name = barcode_tuple
            
            # Skip combinations where either value is None or 'UNKNOWN'
            if delivery_number in [None, 'UNKNOWN'] or customer_name in [None, 'UNKNOWN']:
                invalid_pages.extend(page_numbers)
                vh.error(f"Skipping {len(page_numbers)} pages with incomplete barcode data: Delivery='{delivery_number}', Customer='{customer_name}'")
                for page_num in page_numbers:
                    vh.error(f"  Page {page_num+1} has incomplete barcode data and will not be processed")
            else:
                valid_barcode_pages[barcode_tuple] = page_numbers
        
        return valid_barcode_pages, invalid_pages
    
    def _create_pdf_from_pages(self, pdf_document: pikepdf.Pdf, page_numbers: List[int], output_path: str, vh: VerbosityHandler) -> bool:
        """
        Create a new PDF from specified pages.
        
        Args:
            pdf_document (pikepdf.Pdf): Source PDF document
            page_numbers (List[int]): List of page numbers to include
            output_path (str): Path for the output PDF
            vh (VerbosityHandler): Verbosity handler for logging
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create a new PDF
            new_pdf = pikepdf.Pdf.new()
            sorted_pages = sorted(page_numbers)
            
            # Copy pages from source to destination PDF
            for page_num in sorted_pages:
                new_pdf.pages.append(pdf_document.pages[page_num])
            
            # Save the new PDF
            new_pdf.save(output_path)
            return True
            
        except Exception as e:
            vh.error(f"Failed to create PDF {output_path}: {str(e)}")
            import logging
            logging.getLogger('barkus').exception(f"Exception creating PDF {output_path}")
            return False
    
    def split_pdf_by_barcodes(self, input_pdf_path: str, output_dir: str, dpi: int = 300, verbose: bool = True, log_file: str = None) -> Tuple[Dict[Tuple[str, str], List[int]], List[Dict[str, Any]], Dict[int, BarcodeDetectionResult]]:
        """
        Split PDF into multiple files based on barcode groups.
        
        Args:
            input_pdf_path (str): Path to the input PDF file
            output_dir (str): Directory to save split PDFs
            dpi (int): DPI for rendering PDF pages for barcode detection
            verbose (bool): Whether to display progress information
            log_file (str): Path to log file for detailed logging
            
        Returns:
            Tuple[Dict[Tuple[str, str], List[int]], List[Dict[str, Any]], Dict[int, BarcodeDetectionResult]]: 
                - Dictionary mapping barcode tuples to page numbers
                - List of extraction details for CSV logging
                - Dictionary mapping page numbers to detection results for pages without barcodes
        """
        vh = VerbosityHandler(verbose, log_file)
        
        try:
            os.makedirs(output_dir, exist_ok=True)
            
            vh.info(f"Reading PDF: {input_pdf_path}")
            
            # Extract barcodes from PDF
            page_barcodes = self.barcode_detector.extract_barcodes_from_pdf(input_pdf_path, dpi, verbose, log_file)
            barcode_pages, no_barcode_pages = self.barcode_detector.group_pages_by_barcode(page_barcodes)
            
            # Print detection statistics
            stats = self.barcode_detector.get_detection_statistics(page_barcodes)
            vh.info(f"Detection Statistics:")
            vh.info(f"  Total pages: {stats['total_pages']}")
            vh.info(f"  Pages with barcodes: {stats['pages_with_barcodes']}")
            vh.info(f"  Pages with complete barcodes: {stats['pages_complete_barcodes']}")
            vh.info(f"  Pages with no patterns: {stats['pages_no_patterns']}")
            vh.info(f"  Pages with unreadable patterns: {stats['pages_unreadable_patterns']}")
            vh.info(f"  Pages with corrupted patterns: {stats['pages_corrupted_patterns']}")
            
            # Filter out invalid barcode combinations
            valid_barcode_pages, invalid_pages = self._filter_valid_barcodes(barcode_pages, vh)
            barcode_pages = valid_barcode_pages
            
            if not barcode_pages:
                vh.warning(f"No valid barcodes found in {input_pdf_path}")
                return {}, [], no_barcode_pages
            
            vh.info(f"Found {len(barcode_pages)} unique valid barcode combinations. Creating output PDFs...")
            
            extraction_details = []
            sequence_no = 1
            from datetime import datetime
            current_datetime = datetime.now().strftime('%Y%m%d %H%M%S')
            
            # Open the source PDF with pikepdf
            with pikepdf.open(input_pdf_path) as pdf_document:
                
                for barcode_tuple, page_numbers in barcode_pages.items():
                    delivery_number, customer_name = barcode_tuple
                    
                    # Create filename
                    filename = self._create_safe_filename(delivery_number, customer_name)
                    output_path = os.path.join(output_dir, filename)
                    
                    # Log which barcode values we're using
                    barcode_info = f"Delivery: {delivery_number}"
                    if customer_name != 'UNKNOWN':
                        barcode_info += f", Customer: {customer_name}"
                    
                    vh.info(f"  Creating PDF with {len(page_numbers)} pages: {output_path}")
                    vh.info(f"    Barcode info: {barcode_info}")
                    
                    # Create PDF from pages
                    if self._create_pdf_from_pages(pdf_document, page_numbers, output_path, vh):
                        # Add extraction details for CSV log
                        extraction_details.append({
                            'SequenceNo': sequence_no,
                            'DateTime': current_datetime,
                            'Barcode1': customer_name if customer_name != 'UNKNOWN' else '',
                            'Barcode2': delivery_number if delivery_number != 'UNKNOWN' else '',
                            'OutputPath': output_path
                        })
                        sequence_no += 1
            
            vh.info(f"PDF splitting complete. Created {len(barcode_pages)} files in {output_dir}")
            
        except Exception as e:
            vh.error(f"Error splitting PDF: {str(e)}")
            import logging
            logging.getLogger('barkus').exception("Exception in split_pdf_by_barcodes")
            raise
        finally:
            vh.close()
        
        return barcode_pages, extraction_details, no_barcode_pages
    
    def handle_pages_without_barcodes(self, input_pdf_path: str, output_dir: str, barcode_pages: Dict[Tuple[str, str], List[int]], 
                                    no_barcode_pages: Dict[int, BarcodeDetectionResult], handle_mode: str, 
                                    verbose: bool = True, log_file: str = None) -> Dict[Tuple[str, str], List[int]]:
        """
        Handle pages without barcodes based on the specified mode.
        
        Args:
            input_pdf_path (str): Path to the input PDF file
            output_dir (str): Directory to save split PDFs
            barcode_pages (Dict[Tuple[str, str], List[int]]): Current barcode pages mapping
            no_barcode_pages (Dict[int, BarcodeDetectionResult]): Pages without barcodes and their detection results
            handle_mode (str): How to handle pages without barcodes
            verbose (bool): Whether to display progress information
            log_file (str): Path to log file for detailed logging
            
        Returns:
            Dict[Tuple[str, str], List[int]]: Updated barcode pages mapping
        """
        vh = VerbosityHandler(verbose, log_file)
        
        try:
            with pikepdf.open(input_pdf_path) as pdf_document:
                total_pages = len(pdf_document.pages)
                
                if no_barcode_pages:
                    # Categorize pages without barcodes by their detection status
                    truly_empty_pages = []
                    unreadable_pages = []
                    corrupted_pages = []
                    
                    for page_num, result in no_barcode_pages.items():
                        if result.detection_status == BarcodeDetectionStatus.NO_PATTERNS_FOUND:
                            truly_empty_pages.append(page_num)
                        elif result.detection_status == BarcodeDetectionStatus.PATTERNS_UNREADABLE:
                            unreadable_pages.append(page_num)
                        else:
                            corrupted_pages.append(page_num)
                    
                    vh.info(f"Found {len(no_barcode_pages)} pages without barcodes:")
                    vh.info(f"  Truly empty pages (no patterns): {len(truly_empty_pages)}")
                    vh.info(f"  Unreadable barcode patterns: {len(unreadable_pages)}")
                    vh.info(f"  Corrupted/error pages: {len(corrupted_pages)}")
                    
                    all_no_barcode_page_nums = list(no_barcode_pages.keys())
                    
                    if handle_mode == "separate":
                        self._create_separate_pdf_for_no_barcodes(pdf_document, all_no_barcode_page_nums, output_dir, vh)
                        barcode_pages[("NO_BARCODE", "NO_BARCODE")] = all_no_barcode_page_nums
                    elif handle_mode == "keep_with_previous":
                        barcode_pages = self._assign_to_previous_barcode(barcode_pages, all_no_barcode_page_nums, total_pages, vh)
                    elif handle_mode == "sequential":
                        barcode_pages = self._assign_sequentially_enhanced(barcode_pages, no_barcode_pages, total_pages, vh)
                        # Recreate PDFs with updated assignments
                        self._recreate_pdfs_with_updated_pages(pdf_document, barcode_pages, output_dir, vh)
        
        except Exception as e:
            vh.error(f"Error handling pages without barcodes: {str(e)}")
            import logging
            logging.getLogger('barkus').exception("Exception in handle_pages_without_barcodes")
        finally:
            vh.close()
        
        return barcode_pages
    
    def _create_separate_pdf_for_no_barcodes(self, pdf_document: pikepdf.Pdf, no_barcode_pages: List[int], output_dir: str, vh: VerbosityHandler) -> None:
        """Create a separate PDF for pages without barcodes."""
        output_path = os.path.join(output_dir, "no_barcode.pdf")
        vh.info(f"Creating separate PDF for pages without barcodes: {output_path}")
        
        if self._create_pdf_from_pages(pdf_document, no_barcode_pages, output_path, vh):
            vh.info(f"  Created no_barcode.pdf with {len(no_barcode_pages)} pages")
    
    def _assign_to_previous_barcode(self, barcode_pages: Dict[Tuple[str, str], List[int]], no_barcode_pages: List[int], 
                                  total_pages: int, vh: VerbosityHandler) -> Dict[Tuple[str, str], List[int]]:
        """Assign pages without barcodes to the previous barcode group."""
        vh.info("Keeping pages without barcodes with previous barcode group")
        prev_barcode_tuple = None
        all_pages = sorted(list(range(total_pages)))
        reassignments = {}
        
        for page_num in all_pages:
            # Find which barcode this page belongs to, if any
            current_barcode_tuple = None
            for barcode_tuple, pages in barcode_pages.items():
                if page_num in pages:
                    current_barcode_tuple = barcode_tuple
                    prev_barcode_tuple = barcode_tuple
                    break
            
            # If no barcode and we have a previous barcode, add to that group
            if current_barcode_tuple is None and prev_barcode_tuple is not None and page_num in no_barcode_pages:
                barcode_pages[prev_barcode_tuple].append(page_num)
                if prev_barcode_tuple not in reassignments:
                    reassignments[prev_barcode_tuple] = []
                reassignments[prev_barcode_tuple].append(page_num)
        
        # Log reassignments
        for barcode_tuple, pages in reassignments.items():
            delivery_num, customer_name = barcode_tuple
            barcode_info = f"Delivery: {delivery_num}"
            if customer_name != 'UNKNOWN':
                barcode_info += f", Customer: {customer_name}"
            vh.info(f"  Reassigned {len(pages)} pages to barcodes '{barcode_info}'")
        
        return barcode_pages
    
    def _assign_sequentially(self, barcode_pages: Dict[Tuple[str, str], List[int]], no_barcode_pages: List[int], 
                           total_pages: int, vh: VerbosityHandler) -> Dict[Tuple[str, str], List[int]]:
        """Sequentially assign pages without barcodes to the last seen barcode."""
        vh.info("Using sequential mode: pages with no barcode will be included with the last seen barcode")
        
        # Create a mapping of page number to barcode tuple
        page_to_barcode = {}
        for barcode_tuple, pages in barcode_pages.items():
            for page_num in pages:
                page_to_barcode[page_num] = barcode_tuple
        
        # Process pages sequentially
        current_barcode = None
        reassignments = {}
        
        for page_num in range(total_pages):
            # If this page has a barcode, update the current barcode
            if page_num in page_to_barcode:
                current_barcode = page_to_barcode[page_num]
            # If this page has no barcode but we have a current barcode, assign it to that group
            elif current_barcode is not None and page_num in no_barcode_pages:
                barcode_pages[current_barcode].append(page_num)
                if current_barcode not in reassignments:
                    reassignments[current_barcode] = []
                reassignments[current_barcode].append(page_num)
        
        # Log reassignments
        for barcode_tuple, pages in reassignments.items():
            delivery_num, customer_name = barcode_tuple
            barcode_info = f"Delivery: {delivery_num}"
            if customer_name != 'UNKNOWN':
                barcode_info += f", Customer: {customer_name}"
            vh.info(f"  Sequentially assigned {len(pages)} pages to barcodes '{barcode_info}'")
        
        return barcode_pages
    
    def _assign_sequentially_enhanced(self, barcode_pages: Dict[Tuple[str, str], List[int]], 
                                    no_barcode_pages: Dict[int, BarcodeDetectionResult], 
                                    total_pages: int, vh: VerbosityHandler) -> Dict[Tuple[str, str], List[int]]:
        """Enhanced sequential assignment with proper barcode detection status handling."""
        vh.info("Using enhanced sequential mode: pages with no barcode will be appended to the previous PDF until a new barcode is found")
        
        # Create a mapping of page number to barcode tuple
        page_to_barcode = {}
        for barcode_tuple, pages in barcode_pages.items():
            for page_num in pages:
                page_to_barcode[page_num] = barcode_tuple
        
        # Process pages sequentially - this is the corrected logic
        current_barcode_group = None
        reassignments = {}
        
        for page_num in range(total_pages):
            # Check if this page has a barcode
            if page_num in page_to_barcode:
                # NEW BARCODE FOUND - update current group
                current_barcode_group = page_to_barcode[page_num]
                vh.debug(f"  Page {page_num+1}: Found new barcode group {current_barcode_group}")
                
            elif page_num in no_barcode_pages:
                # NO BARCODE ON THIS PAGE
                result = no_barcode_pages[page_num]
                
                if current_barcode_group is not None:
                    # Assign to the current barcode group
                    barcode_pages[current_barcode_group].append(page_num)
                    if current_barcode_group not in reassignments:
                        reassignments[current_barcode_group] = []
                    reassignments[current_barcode_group].append(page_num)
                    
                    # Log the reason for assignment
                    if result.detection_status == BarcodeDetectionStatus.NO_PATTERNS_FOUND:
                        vh.debug(f"  Page {page_num+1}: No barcode patterns found, appending to current group")
                    elif result.detection_status == BarcodeDetectionStatus.PATTERNS_UNREADABLE:
                        vh.warning(f"  Page {page_num+1}: Unreadable barcode patterns, appending to current group")
                    else:
                        vh.warning(f"  Page {page_num+1}: {result.detection_status.value}, appending to current group")
                else:
                    # No previous barcode group to assign to
                    vh.warning(f"  Page {page_num+1}: No barcode found and no previous group to assign to")
        
        # Log reassignments with detailed information
        for barcode_tuple, pages in reassignments.items():
            delivery_num, customer_name = barcode_tuple
            barcode_info = f"Delivery: {delivery_num}"
            if customer_name != 'UNKNOWN':
                barcode_info += f", Customer: {customer_name}"
            
            # Count different types of pages assigned
            truly_empty = 0
            unreadable = 0
            corrupted = 0
            
            for page_num in pages:
                if page_num in no_barcode_pages:
                    result = no_barcode_pages[page_num]
                    if result.detection_status == BarcodeDetectionStatus.NO_PATTERNS_FOUND:
                        truly_empty += 1
                    elif result.detection_status == BarcodeDetectionStatus.PATTERNS_UNREADABLE:
                        unreadable += 1
                    else:
                        corrupted += 1
            
            assignment_details = f"empty: {truly_empty}, unreadable: {unreadable}, corrupted: {corrupted}"
            vh.info(f"  Sequentially assigned {len(pages)} pages to '{barcode_info}' ({assignment_details})")
        
        return barcode_pages
    
    def _recreate_pdfs_with_updated_pages(self, pdf_document: pikepdf.Pdf, barcode_pages: Dict[Tuple[str, str], List[int]], 
                                        output_dir: str, vh: VerbosityHandler) -> None:
        """Recreate PDFs with updated page assignments."""
        for barcode_tuple, page_numbers in barcode_pages.items():
            if barcode_tuple == ("NO_BARCODE", "NO_BARCODE"):
                continue
                
            delivery_number, customer_name = barcode_tuple
            filename = self._create_safe_filename(delivery_number, customer_name)
            output_path = os.path.join(output_dir, filename)
            
            # Log which barcode values we're using
            barcode_info = f"Delivery: {delivery_number}"
            if customer_name != 'UNKNOWN':
                barcode_info += f", Customer: {customer_name}"
            
            vh.info(f"  Recreating PDF with updated pages: {output_path}")
            vh.info(f"    Barcode info: {barcode_info}")
            
            if self._create_pdf_from_pages(pdf_document, page_numbers, output_path, vh):
                vh.info(f"  Successfully recreated PDF: {output_path}")
            else:
                vh.error(f"  Failed to recreate PDF: {output_path}")