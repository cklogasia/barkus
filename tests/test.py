#!/usr/bin/env python3
"""
Test script for barkus - creates a test PDF with barcodes to verify functionality.
This script requires reportlab and qrcode packages in addition to the main requirements.
"""

import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import qrcode
from PIL import Image
import tempfile
import pikepdf

def create_test_pdf(output_path, barcode_data_list):
    """Create a test PDF with barcodes on different pages"""
    c = canvas.Canvas(output_path, pagesize=letter)
    width, height = letter
    
    # Create pages with different barcodes
    for i, barcode_data in enumerate(barcode_data_list):
        # Add page number and some text
        c.setFont("Helvetica", 12)
        c.drawString(100, height - 50, f"Page {i+1}")
        c.drawString(100, height - 70, f"Testing barcode: {barcode_data}")
        
        # Create QR code (as a simple barcode example)
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(barcode_data)
        qr.make(fit=True)
        
        # Create and save QR code image
        img = qr.make_image(fill_color="black", back_color="white")
        temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        img.save(temp_file.name)
        
        # Add QR code to PDF
        c.drawImage(temp_file.name, 100, height - 300, width=200, height=200)
        
        # Clean up temp file
        temp_file.close()
        os.unlink(temp_file.name)
        
        # Add a new page
        if i < len(barcode_data_list) - 1:
            c.showPage()
    
    c.save()

def main():
    """Create a test PDF with various barcode patterns for testing"""
    # Test data - we'll create 7 pages with 3 different barcodes
    # Pages 0, 3, 6 will have 'TEST-001'
    # Pages 1, 4 will have 'TEST-002'
    # Pages 2, 5 will have 'TEST-003'
    barcode_data = [
        'TEST-001',  # Page 0
        'TEST-002',  # Page 1
        'TEST-003',  # Page 2
        'TEST-001',  # Page 3
        'TEST-002',  # Page 4
        'TEST-003',  # Page 5
        'TEST-001',  # Page 6
    ]
    
    output_dir = "test_data"
    os.makedirs(output_dir, exist_ok=True)
    test_pdf_path = os.path.join(output_dir, "test_barcodes.pdf")
    
    create_test_pdf(test_pdf_path, barcode_data)
    print(f"Created test PDF at {test_pdf_path}")
    print("Expected output: 3 PDFs with the following barcode values:")
    print("  - TEST-001.pdf (pages 1, 4, 7 from original)")
    print("  - TEST-002.pdf (pages 2, 5 from original)")
    print("  - TEST-003.pdf (pages 3, 6 from original)")
    
    print("\nTo run the test:")
    print(f"python barkus.py {test_pdf_path} --output-dir test_output")

if __name__ == "__main__":
    main()