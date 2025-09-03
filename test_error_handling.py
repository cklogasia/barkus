#!/usr/bin/env python3
"""
Test script to verify error handling for missing barcodes.
"""

import os
import sys
import tempfile
import shutil
from barkus_modules.pdf_processor import PDFProcessor

def test_filename_generation():
    """Test filename generation with error tags."""
    processor = PDFProcessor()
    
    print("Testing filename generation...")
    
    # Test normal case (no error)
    filename = processor._create_safe_filename("DO123456", "ACME Corp", False)
    print(f"Normal case: {filename}")
    assert filename == "ACME Corp_DO123456.pdf"
    
    # Test with error tag
    filename = processor._create_safe_filename("DO123456", "ACME Corp", True)
    print(f"With error: {filename}")
    assert filename == "ACME Corp_DO123456_error.pdf"
    
    # Test with missing delivery number
    filename = processor._create_safe_filename("UNKNOWN", "ACME Corp", True)
    print(f"Missing delivery: {filename}")
    assert filename == "ACME Corp_error.pdf"
    
    # Test with missing customer name
    filename = processor._create_safe_filename("DO123456", "UNKNOWN", True)
    print(f"Missing customer: {filename}")
    assert filename == "DO123456_error.pdf"
    
    # Test with both missing
    filename = processor._create_safe_filename("UNKNOWN", "UNKNOWN", True)
    print(f"Both missing: {filename}")
    assert filename == "unknown_barcode_error.pdf"
    
    print("✓ All filename generation tests passed!")

def test_barcode_filtering():
    """Test that pages with missing barcodes are now included."""
    processor = PDFProcessor()
    
    # Mock verbosity handler for testing
    class MockVH:
        def warning(self, msg): pass
        def error(self, msg): pass
    
    vh = MockVH()
    
    print("\nTesting barcode filtering...")
    
    # Test data with missing barcodes
    barcode_pages = {
        ("DO123456", "ACME Corp"): [0, 1, 2],  # Complete barcodes
        ("UNKNOWN", "XYZ Corp"): [3, 4],       # Missing delivery number
        ("DO789012", "UNKNOWN"): [5],          # Missing customer name
        ("UNKNOWN", "UNKNOWN"): [6, 7]         # Missing both
    }
    
    processed_pages, invalid_pages = processor._filter_valid_barcodes(barcode_pages, vh)
    
    print(f"Input barcode groups: {len(barcode_pages)}")
    print(f"Processed barcode groups: {len(processed_pages)}")
    print(f"Invalid pages: {len(invalid_pages)}")
    
    # All pages should now be included
    assert len(processed_pages) == 4, f"Expected 4 groups, got {len(processed_pages)}"
    assert len(invalid_pages) == 0, f"Expected 0 invalid pages, got {len(invalid_pages)}"
    
    print("✓ Barcode filtering test passed!")

if __name__ == "__main__":
    print("Running error handling tests...")
    try:
        test_filename_generation()
        test_barcode_filtering()
        print("\n✅ All tests passed! Error handling is working correctly.")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)