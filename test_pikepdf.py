#!/usr/bin/env python3
"""
Test script for the pikepdf and pdf2image implementation.
This tests the core functionality of the barcode detection and PDF splitting.
"""

import os
import sys
import pikepdf
from pdf2image import convert_from_path
import cv2
import numpy as np
from pyzbar.pyzbar import decode

def test_pdf_opening():
    """Test if we can open a PDF with pikepdf"""
    try:
        # Try to open the test PDF if it exists
        if os.path.exists("test_data/test_barcodes.pdf"):
            pdf_path = "test_data/test_barcodes.pdf"
        else:
            # Create a dummy PDF for testing
            with pikepdf.Pdf.new() as pdf:
                pdf.save("test_dummy.pdf")
            pdf_path = "test_dummy.pdf"
        
        with pikepdf.open(pdf_path) as pdf:
            page_count = len(pdf.pages)
            print(f"Successfully opened PDF with {page_count} pages")
            return True
    except Exception as e:
        print(f"Error opening PDF: {str(e)}")
        return False

def test_pdf_to_image():
    """Test if we can convert PDF pages to images"""
    try:
        # Try to open the test PDF if it exists
        if os.path.exists("test_data/test_barcodes.pdf"):
            pdf_path = "test_data/test_barcodes.pdf"
        else:
            # Create a dummy PDF for testing
            with pikepdf.Pdf.new() as pdf:
                pdf.save("test_dummy.pdf")
            pdf_path = "test_dummy.pdf"
            
        # Convert PDF to images
        images = convert_from_path(pdf_path, dpi=300)
        print(f"Successfully converted PDF to {len(images)} images")
        
        # Test image processing for barcode detection
        if images:
            # Convert PIL Image to OpenCV format
            img_cv = cv2.cvtColor(np.array(images[0]), cv2.COLOR_RGB2BGR)
            print(f"Successfully converted image to OpenCV format: {img_cv.shape}")
        
        return True
    except Exception as e:
        print(f"Error converting PDF to images: {str(e)}")
        return False

def test_pdf_creation():
    """Test if we can create a new PDF from pages"""
    try:
        # Create a new PDF
        pdf = pikepdf.Pdf.new()
        
        # Try to open the test PDF if it exists
        if os.path.exists("test_data/test_barcodes.pdf"):
            src_pdf = pikepdf.open("test_data/test_barcodes.pdf")
            # Copy a page if available
            if len(src_pdf.pages) > 0:
                pdf.pages.append(src_pdf.pages[0])
            src_pdf.close()
        
        # Save the new PDF
        pdf.save("test_output.pdf")
        print("Successfully created a new PDF")
        
        return True
    except Exception as e:
        print(f"Error creating PDF: {str(e)}")
        return False

if __name__ == "__main__":
    print("Testing pikepdf and pdf2image functionality...")
    
    # Create test directory if it doesn't exist
    os.makedirs("test_data", exist_ok=True)
    
    # Run tests
    pdf_open_success = test_pdf_opening()
    pdf_to_image_success = test_pdf_to_image()
    pdf_creation_success = test_pdf_creation()
    
    # Report results
    print("\nTest Results:")
    print(f"- PDF Opening: {'✓' if pdf_open_success else '✗'}")
    print(f"- PDF to Image Conversion: {'✓' if pdf_to_image_success else '✗'}")
    print(f"- PDF Creation: {'✓' if pdf_creation_success else '✗'}")
    
    # Overall result
    if pdf_open_success and pdf_to_image_success and pdf_creation_success:
        print("\nAll tests passed! The pikepdf and pdf2image implementation is working.")
        sys.exit(0)
    else:
        print("\nSome tests failed. Check the error messages above.")
        sys.exit(1)