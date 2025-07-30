# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Barkus is a Python-based PDF barcode splitter that detects delivery number and customer name barcodes on PDF pages and splits the document into separate files based on these barcode combinations. The application uses a modular architecture with dedicated modules for barcode detection, PDF processing, logging, and file operations.

## Key Commands

### Development and Testing
```bash
# Main application execution
python barkus_main.py input.pdf --output-dir output

# Run basic tests
python test.py  # Generate test data with barcodes
python test_pikepdf.py  # Test PDF manipulation functionality
python test_zxing_integration.py  # Test barcode detection
python test_enhanced_barkus.py  # Enhanced functionality tests
python test_integration_enhanced.py  # Integration tests

# Install dependencies
pip install -r requirements.txt
```

### Build and Distribution
```bash
# Create Windows executable (on Windows)
pip install pyinstaller
pyinstaller --onefile --add-data "requirements.txt;." --paths "C:\Poppler\bin" --add-binary "C:\path\to\zxingcpp.cp311-win_amd64.pyd;." barkus_main.py

# Alternative setup.py installation
python setup.py install
```

## Architecture

### Module Structure
The codebase follows a clean modular architecture:

- **`barkus_main.py`**: Main entry point with command-line interface
- **`barkus_modules/`**: Core application modules
  - **`application.py`**: Main application orchestration and workflow
  - **`barcode_detector.py`**: Barcode detection using zxing-cpp with retry logic and content-based classification
  - **`pdf_processor.py`**: PDF manipulation, splitting, and page management using pikepdf
  - **`file_operations.py`**: File I/O operations and validation
  - **`logging_handler.py`**: Logging configuration and verbosity management

### Key Dependencies
- **pikepdf>=9.0.0**: PDF manipulation (requires Python 3.9+)
- **pdf2image>=1.16.0**: PDF to image conversion (requires Poppler)
- **opencv-python==4.8.1.78**: Image processing for barcode detection
- **zxing-cpp>=2.0.0**: Barcode detection library (replaced pyzbar for Windows 11 compatibility)
- **numpy<2.0.0**: Numerical operations with compatibility constraints

### Barcode Detection Logic
The application detects two types of barcodes:
1. **Customer Name Barcode**: Left-side barcode containing customer information
2. **Delivery Number Barcode**: Right-side barcode containing delivery order numbers

Pages are grouped by unique combinations of both barcodes, with configurable handling for pages missing barcodes (ignore, separate, keep_with_previous, sequential).

### Output Generation
- Creates separate PDF files for each unique barcode combination
- Generates CSV log files with detailed extraction information
- Supports multiple barcode handling strategies for edge cases
- Uses safe filename generation to handle special characters

## Platform-Specific Notes

### Windows 11 Compatibility
- Uses zxing-cpp instead of pyzbar for superior Windows compatibility
- Requires Poppler for Windows (must be in PATH or specified explicitly)
- PyInstaller compilation supported with specific binary inclusions
- No longer requires Visual C++ Redistributable packages

### Cross-Platform Support
- Full Linux/macOS support with system package dependencies
- Requires build tools and development packages on Linux distributions
- macOS requires Xcode command line tools and Homebrew for Poppler

## Common Workflows

### Processing PDFs
1. Validate input PDF exists and is readable
2. Convert PDF pages to images at specified DPI (default 300)
3. Detect barcodes on each page using zxing-cpp
4. Group pages by barcode combinations
5. Split PDF into separate files based on groups
6. Generate CSV log with processing details

### Testing and Validation
1. Use `test.py` to generate sample PDFs with test barcodes
2. Run `test_pikepdf.py` to verify PDF manipulation works
3. Use integration tests to validate end-to-end functionality
4. Check output directory for generated files and CSV logs

### Build Process
1. Install all dependencies from requirements.txt
2. For Windows distribution, ensure Poppler is available
3. Use PyInstaller with specific binary inclusions for standalone executable
4. Test executable on target platform before distribution