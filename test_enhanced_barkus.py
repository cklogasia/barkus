#!/usr/bin/env python3
"""
Comprehensive unit tests for the enhanced Barkus PDF barcode splitter.

Tests the enhanced functionality including:
- Barcode detection state tracking
- Differentiation between non-existent vs unrecognized barcodes
- Enhanced sequential logic for page assignment
- Retry logic with image enhancement
- Error reporting and logging

Author: Senior Python Engineer with 20 years of barcode experience
"""

import unittest
import tempfile
import os
import shutil
from unittest.mock import Mock, patch, MagicMock
import numpy as np
import cv2
from typing import Dict, List, Tuple

# Import the enhanced modules
from barkus_modules.barcode_detector import (
    BarcodeDetector, BarcodeClassifier, BarcodeDetectionResult, BarcodeDetectionStatus
)
from barkus_modules.pdf_processor import PDFProcessor
from barkus_modules.application import BarkusApplication
from barkus_modules.logging_handler import VerbosityHandler


class TestBarcodeDetectionStatus(unittest.TestCase):
    """Test the BarcodeDetectionStatus enum."""
    
    def test_enum_values(self):
        """Test that all enum values are correctly defined."""
        self.assertEqual(BarcodeDetectionStatus.SUCCESS.value, "success")
        self.assertEqual(BarcodeDetectionStatus.NO_PATTERNS_FOUND.value, "no_patterns_found")
        self.assertEqual(BarcodeDetectionStatus.PATTERNS_UNREADABLE.value, "patterns_unreadable")
        self.assertEqual(BarcodeDetectionStatus.PATTERNS_CORRUPTED.value, "patterns_corrupted")
        self.assertEqual(BarcodeDetectionStatus.MULTIPLE_CONFLICTS.value, "multiple_conflicts")
        self.assertEqual(BarcodeDetectionStatus.RETRY_EXHAUSTED.value, "retry_exhausted")


class TestBarcodeDetectionResult(unittest.TestCase):
    """Test the BarcodeDetectionResult dataclass."""
    
    def test_default_initialization(self):
        """Test default initialization of BarcodeDetectionResult."""
        result = BarcodeDetectionResult()
        self.assertIsNone(result.delivery_number)
        self.assertIsNone(result.customer_name)
        self.assertEqual(result.detection_status, BarcodeDetectionStatus.NO_PATTERNS_FOUND)
        self.assertEqual(result.patterns_found, 0)
        self.assertEqual(result.readable_patterns, 0)
        self.assertEqual(result.retry_count, 0)
        self.assertIsNone(result.error_details)
    
    def test_has_complete_barcodes(self):
        """Test has_complete_barcodes method."""
        # Test with both barcodes and success status
        result = BarcodeDetectionResult(
            delivery_number="DO123456",
            customer_name="ACME Corp",
            detection_status=BarcodeDetectionStatus.SUCCESS
        )
        self.assertTrue(result.has_complete_barcodes())
        
        # Test with both barcodes but non-success status
        result.detection_status = BarcodeDetectionStatus.PATTERNS_CORRUPTED
        self.assertFalse(result.has_complete_barcodes())
        
        # Test with missing barcode
        result.customer_name = None
        result.detection_status = BarcodeDetectionStatus.SUCCESS
        self.assertFalse(result.has_complete_barcodes())
    
    def test_has_any_barcode(self):
        """Test has_any_barcode method."""
        result = BarcodeDetectionResult()
        self.assertFalse(result.has_any_barcode())
        
        result.delivery_number = "DO123456"
        self.assertTrue(result.has_any_barcode())
        
        result.delivery_number = None
        result.customer_name = "ACME Corp"
        self.assertTrue(result.has_any_barcode())
    
    def test_needs_retry(self):
        """Test needs_retry method."""
        result = BarcodeDetectionResult()
        self.assertFalse(result.needs_retry())
        
        result.detection_status = BarcodeDetectionStatus.PATTERNS_UNREADABLE
        self.assertTrue(result.needs_retry())
        
        result.detection_status = BarcodeDetectionStatus.PATTERNS_CORRUPTED
        self.assertTrue(result.needs_retry())
        
        result.detection_status = BarcodeDetectionStatus.NO_PATTERNS_FOUND
        self.assertFalse(result.needs_retry())


class TestBarcodeClassifier(unittest.TestCase):
    """Test the BarcodeClassifier class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.classifier = BarcodeClassifier()
    
    def test_is_delivery_number_with_do_prefix(self):
        """Test delivery number detection with DO prefix."""
        self.assertTrue(self.classifier.is_delivery_number("DO123456"))
        self.assertTrue(self.classifier.is_delivery_number("do123456"))
        self.assertTrue(self.classifier.is_delivery_number("Do123456"))
        self.assertTrue(self.classifier.is_delivery_number("dO123456"))
    
    def test_is_delivery_number_with_digit_prefix(self):
        """Test delivery number detection with digit prefix."""
        self.assertTrue(self.classifier.is_delivery_number("123456"))
        self.assertTrue(self.classifier.is_delivery_number("7890"))
        self.assertTrue(self.classifier.is_delivery_number("0123"))
    
    def test_is_delivery_number_customer_names(self):
        """Test that customer names are not classified as delivery numbers."""
        self.assertFalse(self.classifier.is_delivery_number("ACME Corp"))
        self.assertFalse(self.classifier.is_delivery_number("Customer Name"))
        self.assertFalse(self.classifier.is_delivery_number("XYZ Company"))
    
    def test_is_delivery_number_edge_cases(self):
        """Test edge cases for delivery number detection."""
        self.assertFalse(self.classifier.is_delivery_number(""))
        self.assertFalse(self.classifier.is_delivery_number("   "))
        self.assertFalse(self.classifier.is_delivery_number(None))


class TestBarcodeDetector(unittest.TestCase):
    """Test the enhanced BarcodeDetector class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.detector = BarcodeDetector(max_retries=3)
        self.vh = VerbosityHandler(verbose=False)
        
        # Create a mock image
        self.mock_image = np.zeros((100, 200, 3), dtype=np.uint8)
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.vh.close()
    
    @patch('barkus_modules.barcode_detector.zxingcpp')
    def test_detect_barcode_patterns_no_barcodes(self, mock_zxing):
        """Test pattern detection when no barcodes are present."""
        mock_zxing.read_barcodes.return_value = []
        
        total_patterns, readable_barcodes = self.detector._detect_barcode_patterns(self.mock_image)
        
        self.assertEqual(len(readable_barcodes), 0)
        # Should detect some potential patterns even if none are readable
        self.assertGreaterEqual(total_patterns, 0)
    
    @patch('barkus_modules.barcode_detector.zxingcpp')
    def test_detect_barcode_patterns_with_barcodes(self, mock_zxing):
        """Test pattern detection when barcodes are present."""
        mock_barcode = Mock()
        mock_barcode.text = "DO123456"
        mock_zxing.read_barcodes.return_value = [mock_barcode]
        
        total_patterns, readable_barcodes = self.detector._detect_barcode_patterns(self.mock_image)
        
        self.assertEqual(len(readable_barcodes), 1)
        self.assertEqual(readable_barcodes[0].text, "DO123456")
        self.assertGreaterEqual(total_patterns, 1)
    
    @patch('barkus_modules.barcode_detector.zxingcpp')
    def test_detect_barcodes_from_image_success(self, mock_zxing):
        """Test successful barcode detection from image."""
        # Mock successful detection
        mock_delivery = Mock()
        mock_delivery.text = "DO123456"
        mock_customer = Mock()
        mock_customer.text = "ACME Corp"
        mock_zxing.read_barcodes.return_value = [mock_delivery, mock_customer]
        
        result = self.detector._detect_barcodes_from_image(self.mock_image, 0, self.vh)
        
        self.assertEqual(result.delivery_number, "DO123456")
        self.assertEqual(result.customer_name, "ACME Corp")
        self.assertEqual(result.detection_status, BarcodeDetectionStatus.SUCCESS)
        self.assertTrue(result.has_complete_barcodes())
    
    @patch('barkus_modules.barcode_detector.zxingcpp')
    def test_detect_barcodes_from_image_corrupted(self, mock_zxing):
        """Test detection with corrupted barcodes."""
        # Mock corrupted barcode (empty text)
        mock_corrupted = Mock()
        mock_corrupted.text = ""
        mock_zxing.read_barcodes.return_value = [mock_corrupted]
        
        result = self.detector._detect_barcodes_from_image(self.mock_image, 0, self.vh)
        
        self.assertIsNone(result.delivery_number)
        self.assertIsNone(result.customer_name)
        self.assertEqual(result.detection_status, BarcodeDetectionStatus.PATTERNS_CORRUPTED)
        self.assertFalse(result.has_any_barcode())
    
    def test_apply_image_enhancements(self):
        """Test image enhancement techniques."""
        # Test different enhancement levels
        enhanced_0 = self.detector._apply_image_enhancements(self.mock_image, 0)
        enhanced_1 = self.detector._apply_image_enhancements(self.mock_image, 1)
        enhanced_2 = self.detector._apply_image_enhancements(self.mock_image, 2)
        enhanced_3 = self.detector._apply_image_enhancements(self.mock_image, 3)
        
        # Level 0 should return original image
        np.testing.assert_array_equal(enhanced_0, self.mock_image)
        
        # Enhanced images should have same shape
        self.assertEqual(enhanced_1.shape, self.mock_image.shape)
        self.assertEqual(enhanced_2.shape, self.mock_image.shape)
        self.assertEqual(enhanced_3.shape, self.mock_image.shape)
    
    def test_is_better_result(self):
        """Test result comparison logic."""
        # Complete result is better than partial
        complete_result = BarcodeDetectionResult(
            delivery_number="DO123456",
            customer_name="ACME Corp",
            detection_status=BarcodeDetectionStatus.SUCCESS
        )
        
        partial_result = BarcodeDetectionResult(
            delivery_number="DO123456",
            detection_status=BarcodeDetectionStatus.SUCCESS
        )
        
        self.assertTrue(self.detector._is_better_result(complete_result, partial_result))
        self.assertFalse(self.detector._is_better_result(partial_result, complete_result))
        
        # More barcodes is better
        more_barcodes = BarcodeDetectionResult(
            delivery_number="DO123456",
            customer_name="ACME Corp"
        )
        
        fewer_barcodes = BarcodeDetectionResult(
            delivery_number="DO123456"
        )
        
        self.assertTrue(self.detector._is_better_result(more_barcodes, fewer_barcodes))
    
    def test_get_detection_statistics(self):
        """Test detection statistics calculation."""
        # Create mock detection results
        page_barcodes = {
            0: BarcodeDetectionResult(
                delivery_number="DO123456",
                customer_name="ACME Corp",
                detection_status=BarcodeDetectionStatus.SUCCESS,
                patterns_found=2,
                readable_patterns=2
            ),
            1: BarcodeDetectionResult(
                detection_status=BarcodeDetectionStatus.NO_PATTERNS_FOUND,
                patterns_found=0,
                readable_patterns=0
            ),
            2: BarcodeDetectionResult(
                detection_status=BarcodeDetectionStatus.PATTERNS_UNREADABLE,
                patterns_found=3,
                readable_patterns=0
            )
        }
        
        stats = self.detector.get_detection_statistics(page_barcodes)
        
        self.assertEqual(stats['total_pages'], 3)
        self.assertEqual(stats['pages_with_barcodes'], 1)
        self.assertEqual(stats['pages_complete_barcodes'], 1)
        self.assertEqual(stats['pages_no_patterns'], 1)
        self.assertEqual(stats['pages_unreadable_patterns'], 1)
        self.assertEqual(stats['total_patterns_found'], 5)
        self.assertEqual(stats['total_readable_patterns'], 2)


class TestPDFProcessor(unittest.TestCase):
    """Test the enhanced PDFProcessor class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.processor = PDFProcessor()
        self.temp_dir = tempfile.mkdtemp()
        self.vh = VerbosityHandler(verbose=False)
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.vh.close()
        shutil.rmtree(self.temp_dir)
    
    def test_assign_sequentially_enhanced(self):
        """Test the enhanced sequential assignment logic."""
        # Mock barcode pages
        barcode_pages = {
            ('DO123456', 'ACME Corp'): [0, 1],
            ('DO789012', 'XYZ Company'): [5, 6]
        }
        
        # Mock pages without barcodes
        no_barcode_pages = {
            2: BarcodeDetectionResult(detection_status=BarcodeDetectionStatus.NO_PATTERNS_FOUND),
            3: BarcodeDetectionResult(detection_status=BarcodeDetectionStatus.PATTERNS_UNREADABLE),
            4: BarcodeDetectionResult(detection_status=BarcodeDetectionStatus.NO_PATTERNS_FOUND),
            7: BarcodeDetectionResult(detection_status=BarcodeDetectionStatus.NO_PATTERNS_FOUND)
        }
        
        updated_pages = self.processor._assign_sequentially_enhanced(
            barcode_pages, no_barcode_pages, 8, self.vh
        )
        
        # Pages 2, 3, 4 should be assigned to the first barcode group
        self.assertIn(2, updated_pages[('DO123456', 'ACME Corp')])
        self.assertIn(3, updated_pages[('DO123456', 'ACME Corp')])
        self.assertIn(4, updated_pages[('DO123456', 'ACME Corp')])
        
        # Page 7 should be assigned to the second barcode group
        self.assertIn(7, updated_pages[('DO789012', 'XYZ Company')])
    
    def test_create_safe_filename(self):
        """Test safe filename creation."""
        # Test with both delivery number and customer name
        filename = self.processor._create_safe_filename("DO123456", "ACME Corp")
        self.assertEqual(filename, "ACME Corp_DO123456.pdf")
        
        # Test with invalid characters
        filename = self.processor._create_safe_filename("DO<123>456", "ACME/Corp")
        self.assertEqual(filename, "ACME_Corp_DO_123_456.pdf")
        
        # Test with unknown values
        filename = self.processor._create_safe_filename("UNKNOWN", "ACME Corp")
        self.assertEqual(filename, "ACME Corp.pdf")
        
        filename = self.processor._create_safe_filename("DO123456", "UNKNOWN")
        self.assertEqual(filename, "DO123456.pdf")
        
        filename = self.processor._create_safe_filename("UNKNOWN", "UNKNOWN")
        self.assertEqual(filename, "unknown_barcode.pdf")


class TestBarkusApplication(unittest.TestCase):
    """Test the enhanced BarkusApplication class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.app = BarkusApplication()
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
    
    def test_validate_configuration(self):
        """Test configuration validation."""
        # Test invalid configuration (non-existent file)
        config = {
            "input_pdf": "non_existent_file.pdf",
            "output_dir": self.temp_dir,
            "dpi": 300,
            "handle_no_barcode": "sequential"
        }
        
        is_valid, error = self.app.validate_configuration(config)
        # This will fail because the file doesn't exist
        self.assertFalse(is_valid)
        self.assertIn("not found", error)
        
        # Test missing required key
        config = {"output_dir": self.temp_dir}
        is_valid, error = self.app.validate_configuration(config)
        self.assertFalse(is_valid)
        self.assertIn("Missing required", error)
        
        # Test invalid DPI (first create a dummy valid file)
        dummy_file = os.path.join(self.temp_dir, "dummy.pdf")
        with open(dummy_file, 'w') as f:
            f.write("dummy content")
        
        config = {
            "input_pdf": dummy_file,
            "output_dir": self.temp_dir,
            "dpi": "invalid"
        }
        is_valid, error = self.app.validate_configuration(config)
        self.assertFalse(is_valid)
        self.assertIn("DPI must be an integer", error)
        
        # Test invalid handle_no_barcode option  
        config = {
            "input_pdf": dummy_file,
            "output_dir": self.temp_dir,
            "handle_no_barcode": "invalid_option"
        }
        is_valid, error = self.app.validate_configuration(config)
        self.assertFalse(is_valid)
        self.assertIn("Invalid handle_no_barcode option", error)
    
    def test_estimate_processing_time(self):
        """Test processing time estimation."""
        # This will fail for a non-PDF file, but tests the logic
        time_estimate = self.app.estimate_processing_time(__file__)
        self.assertIsNone(time_estimate)
    
    def test_get_system_requirements(self):
        """Test system requirements retrieval."""
        requirements = self.app.get_system_requirements()
        
        self.assertIn("python_version", requirements)
        self.assertIn("required_packages", requirements)
        self.assertIn("system_dependencies", requirements)
        self.assertIn("minimum_ram", requirements)
        self.assertIn("recommended_ram", requirements)
        self.assertIn("disk_space", requirements)
        
        # Check that required packages are listed
        self.assertIn("pikepdf", requirements["required_packages"])
        self.assertIn("opencv-python", requirements["required_packages"])
        self.assertIn("numpy", requirements["required_packages"])
        self.assertIn("pdf2image", requirements["required_packages"])
        self.assertIn("zxing-cpp", requirements["required_packages"])


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete enhanced system."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.detector = BarcodeDetector(max_retries=2)
        self.processor = PDFProcessor()
        self.vh = VerbosityHandler(verbose=False)
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.vh.close()
        shutil.rmtree(self.temp_dir)
    
    def test_end_to_end_barcode_detection_workflow(self):
        """Test the complete workflow from detection to page assignment."""
        # Create mock detection results
        page_barcodes = {
            0: BarcodeDetectionResult(
                delivery_number="DO123456",
                customer_name="ACME Corp",
                detection_status=BarcodeDetectionStatus.SUCCESS
            ),
            1: BarcodeDetectionResult(
                detection_status=BarcodeDetectionStatus.NO_PATTERNS_FOUND
            ),
            2: BarcodeDetectionResult(
                detection_status=BarcodeDetectionStatus.PATTERNS_UNREADABLE
            ),
            3: BarcodeDetectionResult(
                delivery_number="DO789012",
                customer_name="XYZ Company",
                detection_status=BarcodeDetectionStatus.SUCCESS
            ),
            4: BarcodeDetectionResult(
                detection_status=BarcodeDetectionStatus.NO_PATTERNS_FOUND
            )
        }
        
        # Group pages by barcode
        barcode_pages, no_barcode_pages = self.detector.group_pages_by_barcode(page_barcodes)
        
        # Verify grouping
        self.assertEqual(len(barcode_pages), 2)
        self.assertEqual(len(no_barcode_pages), 3)
        
        # Verify that pages with barcodes are correctly grouped
        self.assertIn(('DO123456', 'ACME Corp'), barcode_pages)
        self.assertIn(('DO789012', 'XYZ Company'), barcode_pages)
        
        # Verify no-barcode pages are correctly identified
        self.assertIn(1, no_barcode_pages)
        self.assertIn(2, no_barcode_pages)
        self.assertIn(4, no_barcode_pages)
        
        # Test sequential assignment
        updated_pages = self.processor._assign_sequentially_enhanced(
            barcode_pages, no_barcode_pages, 5, self.vh
        )
        
        # Pages 1, 2 should be assigned to first barcode group
        self.assertIn(1, updated_pages[('DO123456', 'ACME Corp')])
        self.assertIn(2, updated_pages[('DO123456', 'ACME Corp')])
        
        # Page 4 should be assigned to second barcode group
        self.assertIn(4, updated_pages[('DO789012', 'XYZ Company')])
    
    def test_detection_statistics_accuracy(self):
        """Test that detection statistics are calculated correctly."""
        page_barcodes = {
            0: BarcodeDetectionResult(
                delivery_number="DO123456",
                customer_name="ACME Corp",
                detection_status=BarcodeDetectionStatus.SUCCESS,
                patterns_found=2,
                readable_patterns=2
            ),
            1: BarcodeDetectionResult(
                delivery_number="DO789012",
                detection_status=BarcodeDetectionStatus.SUCCESS,
                patterns_found=1,
                readable_patterns=1
            ),
            2: BarcodeDetectionResult(
                detection_status=BarcodeDetectionStatus.NO_PATTERNS_FOUND,
                patterns_found=0,
                readable_patterns=0
            ),
            3: BarcodeDetectionResult(
                detection_status=BarcodeDetectionStatus.PATTERNS_UNREADABLE,
                patterns_found=2,
                readable_patterns=0
            ),
            4: BarcodeDetectionResult(
                detection_status=BarcodeDetectionStatus.PATTERNS_CORRUPTED,
                patterns_found=1,
                readable_patterns=0
            )
        }
        
        stats = self.detector.get_detection_statistics(page_barcodes)
        
        # Verify statistics
        self.assertEqual(stats['total_pages'], 5)
        self.assertEqual(stats['pages_with_barcodes'], 2)
        self.assertEqual(stats['pages_complete_barcodes'], 1)
        self.assertEqual(stats['pages_no_patterns'], 1)
        self.assertEqual(stats['pages_unreadable_patterns'], 1)
        self.assertEqual(stats['pages_corrupted_patterns'], 1)
        self.assertEqual(stats['total_patterns_found'], 6)
        self.assertEqual(stats['total_readable_patterns'], 3)


if __name__ == '__main__':
    # Configure test runner
    unittest.main(verbosity=2, buffer=True)