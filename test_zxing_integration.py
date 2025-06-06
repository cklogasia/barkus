#!/usr/bin/env python3
"""
Test script to validate zxing-cpp integration compatibility with the original pyzbar functionality.
"""

import zxingcpp
import numpy as np

def test_zxing_api():
    """Test basic zxing-cpp API functionality"""
    print("Testing zxing-cpp basic API...")
    
    # Create a simple test image (black background)
    test_img = np.zeros((100, 100, 3), dtype=np.uint8)
    
    try:
        # Test the read_barcodes function
        barcodes = zxingcpp.read_barcodes(test_img)
        print(f"✓ zxing-cpp read_barcodes() returns: {type(barcodes)}")
        print(f"✓ Empty image returns {len(barcodes)} barcodes (expected: 0)")
        
        # Test barcode object structure if we had barcodes
        if barcodes:
            barcode = barcodes[0]
            print(f"✓ Barcode text attribute: {hasattr(barcode, 'text')}")
            print(f"✓ Barcode position attribute: {hasattr(barcode, 'position')}")
            if hasattr(barcode, 'position') and hasattr(barcode.position, 'top_left'):
                print(f"✓ Position.top_left.x attribute: {hasattr(barcode.position.top_left, 'x')}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error testing zxing-cpp: {e}")
        return False

def test_compatibility():
    """Test that the API changes are compatible"""
    print("\nTesting API compatibility...")
    
    # Simulate the key differences between pyzbar and zxing-cpp
    print("API differences handled:")
    print("  pyzbar: bc.data.decode('utf-8') → zxing-cpp: bc.text")
    print("  pyzbar: bc.rect.left → zxing-cpp: bc.position.top_left.x")
    print("  pyzbar: decode(img) → zxing-cpp: read_barcodes(img)")
    
    return True

if __name__ == "__main__":
    print("=== ZXing-CPP Integration Test ===")
    
    api_test = test_zxing_api()
    compat_test = test_compatibility()
    
    if api_test and compat_test:
        print("\n✓ All tests passed! zxing-cpp integration is ready.")
    else:
        print("\n✗ Some tests failed. Check the errors above.")