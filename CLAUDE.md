# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Barkus is a modular Python utility that analyzes PDF documents to detect delivery number and customer name barcodes on each page, then splits the PDF into separate files based on these barcode combinations. The application has been optimized for Windows 11 compatibility with zxing-cpp for superior barcode detection.

## Development Commands

### Installation and Setup
```bash
pip install -r requirements.txt
```

### Running the Application
```bash
# Basic usage
python barkus_main.py input.pdf --output-dir output

# With options
python barkus_main.py document.pdf --dpi 600 --handle-no-barcode sequential --debug
```

### Testing
```bash
# Test core PDF functionality
python tests/test_pikepdf.py

# Generate test data with barcodes
python tests/test.py

# Test with generated data
python barkus_main.py test_data/test_barcodes.pdf --output-dir test_output
```

### Windows 11 Compilation
```bash
# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate

# Install dependencies
pip install -r requirements.txt
pip install pyinstaller

# Create executable using spec file
pyinstaller barkus_win.spec
```

## Architecture

### Modular Structure
The application follows Clean Code principles with clear separation of concerns:

```
barkus_modules/
├── application.py           # Main orchestration and workflow
├── barcode_detector.py      # Barcode detection with zxing-cpp + retry logic
├── pdf_processor.py         # PDF manipulation and splitting
├── file_operations.py       # File I/O, CSV logging, filename sanitization
└── logging_handler.py       # Logging configuration with VerbosityHandler
```

### Key Components

- **BarkusApplication**: Main controller that orchestrates the entire workflow
- **PDFProcessor**: Handles PDF loading, page processing, and splitting using pikepdf
- **BarcodeDetector**: Detects barcodes using zxing-cpp with intelligent 16-attempt retry system and image enhancement
- **FileOperations**: Manages output directories, CSV logging, and filename sanitization
- **VerbosityHandler**: Provides consistent logging across all modules

### Data Flow

1. `barkus_main.py` processes CLI arguments and initializes `BarkusApplication`
2. `BarkusApplication` uses `PDFProcessor` to load PDF and process each page
3. `PDFProcessor` converts pages to images and calls `BarcodeDetector`
4. `BarcodeDetector` applies intelligent retry with image enhancements (up to 16 attempts)
5. Pages are grouped by barcode combinations and split into separate PDFs
6. `FileOperations` handles CSV logging and file management

### Intelligent Retry System

The barcode detector includes a robust retry mechanism:
- **Level 1**: Contrast adjustment (5 attempts)
- **Level 2**: Contrast + noise reduction (5 attempts)  
- **Level 3**: Contrast + noise reduction + morphological cleanup (5 attempts)
- **Total**: Up to 16 attempts per page (1 original + 15 enhanced)

## Dependencies

### Core Runtime Dependencies
- **pikepdf>=9.0.0**: PDF manipulation (requires Python 3.9+)
- **pdf2image>=1.16.0**: PDF to image conversion (requires Poppler)
- **opencv-python==4.8.1.78**: Image processing
- **zxing-cpp>=2.0.0**: Barcode detection (Windows 11 compatible)
- **numpy<2.0.0**: Numerical operations (compatibility constraint)

### Test Dependencies
- **reportlab==4.0.9**: Test PDF generation
- **qrcode==7.4.2**: QR code generation for tests
- **Pillow>=10.0.0**: Image handling in tests

### System Requirements
- **Python 3.9+** (required for pikepdf compatibility)
- **Poppler**: Required for pdf2image functionality
  - Windows: Download from https://github.com/oschwartz10612/poppler-windows/releases
  - Linux: `apt install poppler-utils` or `dnf install poppler-utils`
  - macOS: `brew install poppler`

## Key Features

- Detects both delivery number and customer name barcodes
- Groups pages by barcode combinations
- Handles pages without barcodes (ignore, separate, keep_with_previous, sequential modes)
- Automatic CSV logging with timestamps
- Configurable DPI for barcode detection
- Cross-platform Windows 11/Linux/macOS support
- Comprehensive logging with configurable verbosity

## Output

- Split PDFs named with barcode combinations (e.g., `AJC_DO250500001.pdf`)
- CSV log files: `extraction_log_YYYYMMDD_HHMMSS.csv` with sequence numbers, timestamps, barcodes, and output paths
- Detailed logging to console or file with debug mode available