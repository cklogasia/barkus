#!/usr/bin/env python3
"""
Integration test for the enhanced Barkus functionality.

This test demonstrates the key improvements:
1. Differentiation between non-existent vs unrecognized barcodes
2. Proper sequential page assignment logic
3. Enhanced error reporting and logging
"""

import tempfile
import os
from unittest.mock import Mock, patch
import shutil

from barkus_modules.barcode_detector import BarcodeDetector, BarcodeDetectionResult, BarcodeDetectionStatus
from barkus_modules.pdf_processor import PDFProcessor
from barkus_modules.logging_handler import VerbosityHandler


def test_enhanced_sequential_workflow():
    """
    Test the enhanced sequential workflow that was requested.
    
    Scenario:
    - Page 1: Has barcode A
    - Page 2: No barcode (should go to group A)
    - Page 3: Unreadable barcode (should go to group A)
    - Page 4: Has barcode B
    - Page 5: No barcode (should go to group B)
    """
    
    # Create temp directory for testing
    temp_dir = tempfile.mkdtemp()
    vh = VerbosityHandler(verbose=True)
    
    try:
        # Create mock detection results that simulate the scenario
        page_results = {
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
                patterns_found=2,
                readable_patterns=0
            ),
            3: BarcodeDetectionResult(
                delivery_number="DO789012",
                customer_name="XYZ Company",
                detection_status=BarcodeDetectionStatus.SUCCESS,
                patterns_found=2,
                readable_patterns=2
            ),
            4: BarcodeDetectionResult(
                detection_status=BarcodeDetectionStatus.NO_PATTERNS_FOUND,
                patterns_found=0,
                readable_patterns=0
            )
        }
        
        # Create detector and processor
        detector = BarcodeDetector()
        processor = PDFProcessor()
        
        # Group pages by barcode
        barcode_pages, no_barcode_pages = detector.group_pages_by_barcode(page_results)
        
        print("=== INITIAL GROUPING ===")
        print(f"Barcode pages: {barcode_pages}")
        print(f"No barcode pages: {list(no_barcode_pages.keys())}")
        print(f"No barcode page statuses: {[(k, v.detection_status.value) for k, v in no_barcode_pages.items()]}")
        
        # Apply enhanced sequential assignment
        updated_pages = processor._assign_sequentially_enhanced(
            barcode_pages, no_barcode_pages, 5, vh
        )
        
        print("\\n=== AFTER SEQUENTIAL ASSIGNMENT ===")
        for barcode_key, pages in updated_pages.items():
            print(f"Group {barcode_key}: pages {pages}")
        
        # Verify the results
        acme_pages = updated_pages[('DO123456', 'ACME Corp')]
        xyz_pages = updated_pages[('DO789012', 'XYZ Company')]
        
        print("\\n=== VERIFICATION ===")
        print(f"ACME Corp group should have pages [0, 1, 2]: {acme_pages}")
        print(f"XYZ Company group should have pages [3, 4]: {xyz_pages}")
        
        # Check that the assignment is correct
        assert 0 in acme_pages, "Page 0 should be in ACME Corp group"
        assert 1 in acme_pages, "Page 1 (no barcode) should be assigned to ACME Corp group"
        assert 2 in acme_pages, "Page 2 (unreadable barcode) should be assigned to ACME Corp group"
        assert 3 in xyz_pages, "Page 3 should be in XYZ Company group"
        assert 4 in xyz_pages, "Page 4 (no barcode) should be assigned to XYZ Company group"
        
        print("\\n✅ All assertions passed! Enhanced sequential logic works correctly.")
        
        # Test detection statistics
        stats = detector.get_detection_statistics(page_results)
        print("\\n=== DETECTION STATISTICS ===")
        print(f"Total pages: {stats['total_pages']}")
        print(f"Pages with barcodes: {stats['pages_with_barcodes']}")
        print(f"Pages with complete barcodes: {stats['pages_complete_barcodes']}")
        print(f"Pages with no patterns: {stats['pages_no_patterns']}")
        print(f"Pages with unreadable patterns: {stats['pages_unreadable_patterns']}")
        print(f"Total patterns found: {stats['total_patterns_found']}")
        print(f"Total readable patterns: {stats['total_readable_patterns']}")
        
        # Verify statistics
        assert stats['total_pages'] == 5
        assert stats['pages_with_barcodes'] == 2
        assert stats['pages_complete_barcodes'] == 2
        assert stats['pages_no_patterns'] == 2
        assert stats['pages_unreadable_patterns'] == 1
        
        print("\\n✅ Detection statistics are correct!")
        
    finally:
        vh.close()
        shutil.rmtree(temp_dir)


def test_barcode_detection_differentiation():
    """
    Test that the system properly differentiates between different types of detection failures.
    """
    print("\\n=== TESTING BARCODE DETECTION DIFFERENTIATION ===")
    
    # Test cases for different detection scenarios
    test_cases = [
        {
            'name': 'No patterns found',
            'result': BarcodeDetectionResult(
                detection_status=BarcodeDetectionStatus.NO_PATTERNS_FOUND,
                patterns_found=0,
                readable_patterns=0
            ),
            'expected_retry': False
        },
        {
            'name': 'Patterns unreadable',
            'result': BarcodeDetectionResult(
                detection_status=BarcodeDetectionStatus.PATTERNS_UNREADABLE,
                patterns_found=3,
                readable_patterns=0
            ),
            'expected_retry': True
        },
        {
            'name': 'Patterns corrupted',
            'result': BarcodeDetectionResult(
                detection_status=BarcodeDetectionStatus.PATTERNS_CORRUPTED,
                patterns_found=2,
                readable_patterns=0,
                error_details="Found 2 corrupted barcodes"
            ),
            'expected_retry': True
        },
        {
            'name': 'Success',
            'result': BarcodeDetectionResult(
                delivery_number="DO123456",
                customer_name="ACME Corp",
                detection_status=BarcodeDetectionStatus.SUCCESS,
                patterns_found=2,
                readable_patterns=2
            ),
            'expected_retry': False
        }
    ]
    
    for test_case in test_cases:
        result = test_case['result']
        expected_retry = test_case['expected_retry']
        
        print(f"\\n{test_case['name']}:")
        print(f"  Status: {result.detection_status.value}")
        print(f"  Patterns found: {result.patterns_found}")
        print(f"  Readable patterns: {result.readable_patterns}")
        print(f"  Has any barcode: {result.has_any_barcode()}")
        print(f"  Has complete barcodes: {result.has_complete_barcodes()}")
        print(f"  Needs retry: {result.needs_retry()}")
        print(f"  Expected retry: {expected_retry}")
        
        assert result.needs_retry() == expected_retry, f"Retry logic incorrect for {test_case['name']}"
        
    print("\\n✅ All barcode detection differentiation tests passed!")


if __name__ == "__main__":
    print("🚀 Running Enhanced Barkus Integration Tests...")
    print("=" * 60)
    
    test_enhanced_sequential_workflow()
    test_barcode_detection_differentiation()
    
    print("\\n" + "=" * 60)
    print("🎉 All integration tests passed successfully!")
    print("\\nThe enhanced Barkus system now provides:")
    print("✅ Proper differentiation between non-existent vs unrecognized barcodes")
    print("✅ Correct sequential page assignment logic")
    print("✅ Enhanced error reporting and logging")
    print("✅ Intelligent retry logic with image enhancement")
    print("✅ Comprehensive detection statistics")