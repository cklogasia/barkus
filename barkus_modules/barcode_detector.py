"""
Barcode Detection Module

This module handles barcode detection and validation for the Barkus PDF barcode splitter.
Includes content-based classification and retry logic for missing barcodes.
"""

import cv2
import numpy as np
from pdf2image import convert_from_path
import zxingcpp
from typing import Dict, List, Optional, Tuple, NamedTuple
from enum import Enum
from dataclasses import dataclass

from .logging_handler import VerbosityHandler


class BarcodeDetectionStatus(Enum):
    """Enumeration of barcode detection states."""
    SUCCESS = "success"
    NO_PATTERNS_FOUND = "no_patterns_found"
    PATTERNS_UNREADABLE = "patterns_unreadable"
    PATTERNS_CORRUPTED = "patterns_corrupted"
    MULTIPLE_CONFLICTS = "multiple_conflicts"
    RETRY_EXHAUSTED = "retry_exhausted"


@dataclass
class BarcodeDetectionResult:
    """Result of barcode detection with detailed status information."""
    delivery_number: Optional[str] = None
    customer_name: Optional[str] = None
    detection_status: BarcodeDetectionStatus = BarcodeDetectionStatus.NO_PATTERNS_FOUND
    patterns_found: int = 0
    readable_patterns: int = 0
    retry_count: int = 0
    error_details: Optional[str] = None
    
    def has_complete_barcodes(self) -> bool:
        """Check if both required barcode types were successfully detected."""
        return (self.delivery_number is not None and 
                self.customer_name is not None and 
                self.detection_status == BarcodeDetectionStatus.SUCCESS)
    
    def has_any_barcode(self) -> bool:
        """Check if at least one barcode was detected."""
        return self.delivery_number is not None or self.customer_name is not None
    
    def needs_retry(self) -> bool:
        """Check if detection should be retried based on status."""
        return self.detection_status in [
            BarcodeDetectionStatus.PATTERNS_UNREADABLE,
            BarcodeDetectionStatus.PATTERNS_CORRUPTED
        ]


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
    
    def _detect_barcode_patterns(self, img_cv: np.ndarray) -> Tuple[int, List]:
        """
        Detect barcode patterns in an image with enhanced detection.
        
        Args:
            img_cv (np.ndarray): OpenCV image of the page
            
        Returns:
            Tuple[int, List]: (total_patterns_found, readable_barcodes)
        """
        # Try multiple detection strategies to differentiate between
        # no patterns vs unreadable patterns
        
        # Strategy 1: Standard detection
        detected_barcodes = zxingcpp.read_barcodes(img_cv)
        readable_count = len(detected_barcodes)
        
        # Strategy 2: Enhanced detection for corrupted/damaged barcodes
        # Apply image preprocessing to detect potential barcode regions
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY) if len(img_cv.shape) == 3 else img_cv
        
        # Look for barcode-like patterns using morphological operations
        # Barcodes typically have alternating black/white vertical lines
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        morph = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
        
        # Find contours that might be barcode regions
        contours, _ = cv2.findContours(morph, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Count potential barcode regions (rectangular regions with appropriate aspect ratio)
        potential_patterns = 0
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = w / h if h > 0 else 0
            area = cv2.contourArea(contour)
            
            # Typical barcode characteristics:
            # - Aspect ratio between 2:1 and 10:1 (width > height)
            # - Minimum area threshold
            # - Rectangular shape
            if (2.0 <= aspect_ratio <= 10.0 and 
                area > 500 and 
                len(cv2.approxPolyDP(contour, 0.02 * cv2.arcLength(contour, True), True)) <= 6):
                potential_patterns += 1
        
        total_patterns = max(readable_count, potential_patterns)
        
        return total_patterns, detected_barcodes
    
    def _detect_barcodes_from_image(self, img_cv: np.ndarray, page_num: int, vh: VerbosityHandler) -> BarcodeDetectionResult:
        """
        Extract barcodes from a single page image with enhanced detection status.
        
        Args:
            img_cv (np.ndarray): OpenCV image of the page
            page_num (int): Page number (0-based)
            vh (VerbosityHandler): Verbosity handler for logging
            
        Returns:
            BarcodeDetectionResult: Detailed detection result with status information
        """
        try:
            # Detect barcode patterns
            total_patterns, detected_barcodes = self._detect_barcode_patterns(img_cv)
            
            result = BarcodeDetectionResult(
                patterns_found=total_patterns,
                readable_patterns=len(detected_barcodes)
            )
            
            # Determine detection status
            if total_patterns == 0:
                result.detection_status = BarcodeDetectionStatus.NO_PATTERNS_FOUND
                vh.debug(f"  Page {page_num+1}: No barcode patterns detected")
                return result
            
            if len(detected_barcodes) == 0:
                result.detection_status = BarcodeDetectionStatus.PATTERNS_UNREADABLE
                vh.warning(f"  Page {page_num+1}: {total_patterns} barcode patterns found but none readable")
                return result
            
            # Process readable barcodes
            delivery_barcodes = []
            customer_barcodes = []
            invalid_barcodes = []
            
            for bc in detected_barcodes:
                if not bc.text or not bc.text.strip():
                    invalid_barcodes.append(bc)
                    continue
                    
                if self.classifier.is_delivery_number(bc.text):
                    delivery_barcodes.append(bc)
                else:
                    customer_barcodes.append(bc)
            
            # Handle invalid/corrupted barcodes
            if invalid_barcodes:
                result.detection_status = BarcodeDetectionStatus.PATTERNS_CORRUPTED
                result.error_details = f"Found {len(invalid_barcodes)} corrupted barcodes"
                vh.warning(f"  Page {page_num+1}: {len(invalid_barcodes)} corrupted barcodes detected")
            
            # Handle delivery numbers
            if delivery_barcodes:
                result.delivery_number = delivery_barcodes[0].text
                if len(delivery_barcodes) > 1:
                    extra_delivery = [bc.text for bc in delivery_barcodes[1:]]
                    vh.warning(f"  Multiple delivery number barcodes found on page {page_num+1}, using first one: {result.delivery_number}")
                    vh.warning(f"  Unused delivery number barcodes: {', '.join(extra_delivery)}")
            
            # Handle customer names
            if customer_barcodes:
                result.customer_name = customer_barcodes[0].text
                if len(customer_barcodes) > 1:
                    extra_customer = [bc.text for bc in customer_barcodes[1:]]
                    vh.warning(f"  Multiple customer name barcodes found on page {page_num+1}, using first one: {result.customer_name}")
                    vh.warning(f"  Unused customer name barcodes: {', '.join(extra_customer)}")
            
            # Set final status
            if result.has_complete_barcodes():
                result.detection_status = BarcodeDetectionStatus.SUCCESS
            elif result.has_any_barcode():
                result.detection_status = BarcodeDetectionStatus.SUCCESS  # Partial success
            elif result.detection_status == BarcodeDetectionStatus.NO_PATTERNS_FOUND:
                # Keep the corrupted status if it was set
                pass
            
            return result
            
        except Exception as e:
            vh.error(f"  Error detecting barcodes on page {page_num+1}: {str(e)}")
            return BarcodeDetectionResult(
                detection_status=BarcodeDetectionStatus.PATTERNS_CORRUPTED,
                error_details=str(e)
            )
    
    def _apply_image_enhancements(self, img_cv: np.ndarray, enhancement_level: int) -> np.ndarray:
        """
        Apply image enhancement techniques for better barcode detection.
        
        Args:
            img_cv (np.ndarray): Original image
            enhancement_level (int): Enhancement level (0-3)
            
        Returns:
            np.ndarray: Enhanced image
        """
        if enhancement_level == 0:
            return img_cv
        
        # Convert to grayscale if needed
        if len(img_cv.shape) == 3:
            gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        else:
            gray = img_cv.copy()
        
        enhanced = gray.copy()
        
        if enhancement_level >= 1:
            # Level 1: Contrast enhancement
            enhanced = cv2.equalizeHist(enhanced)
        
        if enhancement_level >= 2:
            # Level 2: Gaussian blur to reduce noise
            enhanced = cv2.GaussianBlur(enhanced, (3, 3), 0)
        
        if enhancement_level >= 3:
            # Level 3: Morphological operations to clean up
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
            enhanced = cv2.morphologyEx(enhanced, cv2.MORPH_CLOSE, kernel)
        
        # Convert back to BGR if original was color
        if len(img_cv.shape) == 3:
            enhanced = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
        
        return enhanced
    
    def _is_better_result(self, current: BarcodeDetectionResult, previous: BarcodeDetectionResult) -> bool:
        """
        Determine if the current result is better than the previous one.
        
        Args:
            current (BarcodeDetectionResult): Current detection result
            previous (BarcodeDetectionResult): Previous detection result
            
        Returns:
            bool: True if current result is better
        """
        # Priority order:
        # 1. Complete barcodes (both found)
        # 2. More barcodes found
        # 3. Better detection status
        # 4. More readable patterns
        
        if current.has_complete_barcodes() and not previous.has_complete_barcodes():
            return True
        
        if previous.has_complete_barcodes() and not current.has_complete_barcodes():
            return False
        
        current_count = sum(1 for x in [current.delivery_number, current.customer_name] if x is not None)
        previous_count = sum(1 for x in [previous.delivery_number, previous.customer_name] if x is not None)
        
        if current_count > previous_count:
            return True
        
        if current_count < previous_count:
            return False
        
        # Same number of barcodes, check status priority
        status_priority = {
            BarcodeDetectionStatus.SUCCESS: 5,
            BarcodeDetectionStatus.PATTERNS_CORRUPTED: 4,
            BarcodeDetectionStatus.PATTERNS_UNREADABLE: 3,
            BarcodeDetectionStatus.MULTIPLE_CONFLICTS: 2,
            BarcodeDetectionStatus.NO_PATTERNS_FOUND: 1,
            BarcodeDetectionStatus.RETRY_EXHAUSTED: 0
        }
        
        return status_priority.get(current.detection_status, 0) > status_priority.get(previous.detection_status, 0)
    
    def _detect_with_retry(self, img_cv: np.ndarray, page_num: int, vh: VerbosityHandler) -> BarcodeDetectionResult:
        """
        Extract barcodes with intelligent retry logic based on detection status.
        
        Args:
            img_cv (np.ndarray): OpenCV image of the page
            page_num (int): Page number (0-based)
            vh (VerbosityHandler): Verbosity handler for logging
            
        Returns:
            BarcodeDetectionResult: Final detection result with retry information
        """
        best_result = None
        
        for attempt in range(self.max_retries + 1):  # +1 for initial attempt
            # Apply progressive image enhancement
            enhanced_img = self._apply_image_enhancements(img_cv, attempt)
            
            result = self._detect_barcodes_from_image(enhanced_img, page_num, vh)
            result.retry_count = attempt
            
            # Keep track of the best result so far
            if best_result is None or self._is_better_result(result, best_result):
                best_result = result
            
            # Success criteria: both barcodes found or only retryable failures
            if result.has_complete_barcodes():
                if attempt > 0:
                    vh.info(f"  Successfully found both barcodes on page {page_num+1} after {attempt} retries")
                return result
            
            # Don't retry if we found no patterns (likely truly empty page)
            if result.detection_status == BarcodeDetectionStatus.NO_PATTERNS_FOUND:
                vh.debug(f"  Page {page_num+1}: No barcode patterns found, skipping retries")
                break
            
            # Only retry for cases where we might improve with enhancement
            if attempt < self.max_retries and result.needs_retry():
                missing = []
                if result.delivery_number is None:
                    missing.append("delivery number")
                if result.customer_name is None:
                    missing.append("customer name")
                
                vh.warning(f"  Missing {' and '.join(missing)} barcode(s) on page {page_num+1}, enhancing image and retrying... (attempt {attempt+1}/{self.max_retries})")
            else:
                # Either max retries reached or no point in retrying
                break
        
        # Final attempt failed or no more retries warranted
        if best_result.retry_count >= self.max_retries:
            best_result.detection_status = BarcodeDetectionStatus.RETRY_EXHAUSTED
        
        missing = []
        if best_result.delivery_number is None:
            missing.append("delivery number")
        if best_result.customer_name is None:
            missing.append("customer name")
        
        if missing:
            status_msg = f"Status: {best_result.detection_status.value}"
            if best_result.error_details:
                status_msg += f" ({best_result.error_details})"
            vh.error(f"Failed to detect {' and '.join(missing)} barcode(s) on page {page_num+1} after {best_result.retry_count} retries. {status_msg}")
        
        return best_result
    
    def extract_barcodes_from_pdf(self, pdf_path: str, dpi: int = 300, verbose: bool = True, log_file: str = None) -> Dict[int, BarcodeDetectionResult]:
        """
        Extract delivery number and customer name barcodes from each page of a PDF document.
        
        Args:
            pdf_path (str): Path to the PDF file
            dpi (int): DPI for rendering PDF pages (higher values may improve barcode detection)
            verbose (bool): Whether to display progress information
            log_file (str): Path to log file for detailed logging
            
        Returns:
            Dict[int, BarcodeDetectionResult]: Dictionary mapping page numbers to detection results
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
                        result = self._detect_with_retry(img_cv, page_num, vh)
                        
                        # Always store the result (even if no barcodes found)
                        page_barcodes[page_num] = result
                        
                        # Log what we found
                        if result.has_any_barcode():
                            vh.info(f"  Found barcodes on page {page_num+1}:")
                            vh.info(f"    Delivery Number: {result.delivery_number or 'UNKNOWN'}")
                            vh.info(f"    Customer Name: {result.customer_name or 'UNKNOWN'}")
                            vh.info(f"    Detection Status: {result.detection_status.value}")
                            if result.patterns_found > result.readable_patterns:
                                vh.info(f"    Patterns: {result.patterns_found} found, {result.readable_patterns} readable")
                        else:
                            vh.debug(f"  Page {page_num+1}: {result.detection_status.value}")
                            if result.patterns_found > 0:
                                vh.debug(f"    Patterns: {result.patterns_found} found, {result.readable_patterns} readable")
                    
                    except Exception as e:
                        vh.warning(f"Error processing page {page_num+1}: {str(e)}")
                        import logging
                        logging.getLogger('barkus').exception(f"Exception while processing page {page_num+1}")
                        # Store error result
                        page_barcodes[page_num] = BarcodeDetectionResult(
                            detection_status=BarcodeDetectionStatus.PATTERNS_CORRUPTED,
                            error_details=str(e)
                        )
                        continue
                
                successful_pages = sum(1 for result in page_barcodes.values() if result.has_any_barcode())
                vh.info(f"Barcode detection complete. Found barcodes on {successful_pages}/{total_pages} pages.")
            
        except Exception as e:
            vh.error(f"Failed to process PDF: {str(e)}")
            import logging
            logging.getLogger('barkus').exception("Exception in extract_barcodes_from_pdf")
            raise
        finally:
            vh.close()
        
        return page_barcodes
    
    def group_pages_by_barcode(self, page_barcodes: Dict[int, BarcodeDetectionResult]) -> Tuple[Dict[Tuple[str, str], List[int]], Dict[int, BarcodeDetectionResult]]:
        """
        Group page numbers by combined delivery number and customer name barcodes.
        
        Args:
            page_barcodes (Dict[int, BarcodeDetectionResult]): Dictionary mapping page numbers to detection results
                                 
        Returns:
            Tuple[Dict[Tuple[str, str], List[int]], Dict[int, BarcodeDetectionResult]]: 
                - Dictionary mapping (delivery_number, customer_name) tuples to lists of page numbers
                - Dictionary mapping page numbers to detection results for pages without barcodes
        """
        from collections import defaultdict
        
        barcode_pages = defaultdict(list)
        no_barcode_pages = {}
        
        for page_num, result in page_barcodes.items():
            if result.has_any_barcode():
                delivery_number = result.delivery_number or 'UNKNOWN'
                customer_name = result.customer_name or 'UNKNOWN'
                
                # Use a tuple of both barcode types as the key to group pages
                barcode_key = (delivery_number, customer_name)
                barcode_pages[barcode_key].append(page_num)
            else:
                # Store pages without barcodes with their detection results
                no_barcode_pages[page_num] = result
        
        return dict(barcode_pages), no_barcode_pages
    
    def get_detection_statistics(self, page_barcodes: Dict[int, BarcodeDetectionResult]) -> Dict[str, int]:
        """
        Get statistics about barcode detection results.
        
        Args:
            page_barcodes (Dict[int, BarcodeDetectionResult]): Detection results
            
        Returns:
            Dict[str, int]: Statistics about detection results
        """
        stats = {
            'total_pages': len(page_barcodes),
            'pages_with_barcodes': 0,
            'pages_complete_barcodes': 0,
            'pages_no_patterns': 0,
            'pages_unreadable_patterns': 0,
            'pages_corrupted_patterns': 0,
            'pages_retry_exhausted': 0,
            'total_patterns_found': 0,
            'total_readable_patterns': 0
        }
        
        for result in page_barcodes.values():
            if result.has_any_barcode():
                stats['pages_with_barcodes'] += 1
            
            if result.has_complete_barcodes():
                stats['pages_complete_barcodes'] += 1
            
            if result.detection_status == BarcodeDetectionStatus.NO_PATTERNS_FOUND:
                stats['pages_no_patterns'] += 1
            elif result.detection_status == BarcodeDetectionStatus.PATTERNS_UNREADABLE:
                stats['pages_unreadable_patterns'] += 1
            elif result.detection_status == BarcodeDetectionStatus.PATTERNS_CORRUPTED:
                stats['pages_corrupted_patterns'] += 1
            elif result.detection_status == BarcodeDetectionStatus.RETRY_EXHAUSTED:
                stats['pages_retry_exhausted'] += 1
            
            stats['total_patterns_found'] += result.patterns_found
            stats['total_readable_patterns'] += result.readable_patterns
        
        return stats