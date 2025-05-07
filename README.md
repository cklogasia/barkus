# Barkus - PDF Barcode Splitter

A Python utility that analyzes PDF documents to detect delivery number and customer name barcodes on each page, and splits the PDF into separate files based on these barcode values.

## Features

- Detects both delivery number and customer name barcodes on each page of a PDF document
- Groups pages with identical delivery number and customer name combinations
- Splits the PDF into separate files based on these barcode combinations
- Names each output file using both barcode values (delivery number and customer name)
- Preserves original page sequence in the new PDFs

## Installation

```bash
pip install -r requirements.txt
```

## System Requirements

- Python 3.7+
- For zbar library (pyzbar dependency):
  - On Ubuntu/Debian: `sudo apt-get install libzbar0`
  - On macOS: `brew install zbar`
  - On Windows: No additional steps required (binary included with pyzbar)
- For pdf2image (Poppler dependency):
  - On Ubuntu/Debian: `sudo apt-get install poppler-utils`
  - On macOS: `brew install poppler`
  - On Windows: Download from [poppler-windows](https://github.com/oschwartz10612/poppler-windows/) and add to PATH

## Usage

```bash
python barkus.py input.pdf --output-dir output
```

### Options

- `input_pdf`: Path to input PDF file
- `--output-dir`, `-o`: Output directory (default: "output")
- `--dpi`: DPI for barcode detection (default: 300)
- `--handle-no-barcode`: How to handle pages without barcodes (default: "ignore")
  - `ignore`: Skip pages without barcodes
  - `separate`: Create a separate PDF for pages without barcodes
  - `keep_with_previous`: Include pages with the previous barcode group
- `--quiet`, `-q`: Suppress progress output
- `--log-file`: Path to log file (default: no log file)
- `--debug`: Enable debug logging (more verbose)

## Examples

### Basic Usage

```bash
python barkus.py invoice.pdf --output-dir split_invoices
```

This will:
1. Read invoice.pdf
2. Detect delivery number and customer name barcodes on each page
3. Create a new PDF for each unique combination of delivery number and customer name
4. Save the new PDFs to the split_invoices directory, with filenames containing both barcode values
5. Ignore any pages that don't have both barcodes

### Handling Pages Without Both Required Barcodes

```bash
python barkus.py invoice.pdf --output-dir split_invoices --handle-no-barcode separate
```

This will:
1. Read invoice.pdf
2. Detect delivery number and customer name barcodes on each page
3. Create a new PDF for each unique combination of delivery number and customer name
4. Create an additional PDF called "no_barcode.pdf" containing all pages that don't have both required barcodes
5. Save all PDFs to the split_invoices directory

### Using Logging

```bash
python barkus.py invoice.pdf --log-file barkus.log --debug
```

This will:
1. Process the PDF normally
2. Write detailed logs to barkus.log
3. Enable debug-level logging for more detailed information

### Test Data Generation

The project includes a test script to generate sample PDFs with barcodes:

```bash
python test.py
```

After generating the test data, you can run:

```bash
python barkus.py test_data/test_barcodes.pdf --output-dir test_output
```
