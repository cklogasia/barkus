# Barkus - PDF Barcode Splitter

A Python utility that analyzes PDF documents to detect delivery number and customer name barcodes on each page, and splits the PDF into separate files based on these barcode values.

## Features

- Detects both delivery number and customer name barcodes on each page of a PDF document
- Groups pages with identical delivery number and customer name combinations
- Splits the PDF into separate files based on these barcode combinations
- Names each output file using both barcode values (delivery number and customer name)
- Preserves original page sequence in the new PDFs
- **Generates CSV log files** with detailed extraction information for each run

## Installation

```bash
pip install -r requirements.txt
```

## Dependencies

- **Core Dependencies**:
  - pikepdf>=9.0.0 - For PDF manipulation
  - pdf2image>=1.16.0 - For converting PDF to images
  - opencv-python==4.8.1.78 - For image processing
  - pyzbar==0.1.9 - For barcode detection
  - numpy>=1.22.0 - For numerical operations

- **Test Dependencies**:
  - reportlab==4.0.9 - For creating test PDFs
  - qrcode==7.4.2 - For generating QR codes in test PDFs
  - Pillow>=10.0.0 - For image handling in tests

## System Requirements

- Python 3.7+
- A bash shell (PowerShell is not supported). For Windows, please use WSL2 with either Ubuntu or Fedora.

This script uses an older version of NumPy which may not be compatible with the latest Python (3.13 as time of writing). Ensure that the appropriate python build dependencies are available on your system.

For Fedora/Red Hat:
```bash
sudo dnf install gcc python3-devel redhat-rpm-config
```

For Ubuntu/Debian
```bash
sudo apt update
sudo apt install build-essential python3-dev python3-pip python3-setuptools
```

For MacOS
```bash
xcode-select --install
```

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
  - `sequential`: Include pages with no barcode with the last detected barcode until a new barcode is found
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

### Sequential Processing of Pages Without Barcodes

```bash
python barkus.py invoice.pdf --output-dir split_invoices --handle-no-barcode sequential
```

This will:
1. Read invoice.pdf
2. Detect delivery number and customer name barcodes on each page
3. Process pages sequentially from beginning to end
4. For pages with barcodes, track the most recently seen barcode
5. For pages without barcodes, include them with the most recently seen barcode group
6. Start a new group only when a new barcode is detected
7. Save all PDFs to the split_invoices directory

This mode is particularly useful for multi-page documents where some pages naturally belong with the preceding barcode page (like continuation pages or detailed information related to the barcode page).

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

## Testing the Installation

To verify that all required dependencies are properly installed and working:

```bash
python test_pikepdf.py
```

This will test the core PDF manipulation functionality using the pikepdf and pdf2image libraries.

## CSV Logging

Starting from this version, Barkus automatically generates a CSV log file after each PDF processing run. The CSV file contains detailed information about each extracted PDF file.

### CSV File Format

The CSV log file is saved in the output directory with the filename format: `extraction_log_YYYYMMDD_HHMMSS.csv`

The CSV contains the following columns:

| Column | Description |
|--------|-------------|
| `SequenceNo` | Sequential number for each extracted PDF (1, 2, 3, etc.) |
| `DateTime` | Date and time when the processing was performed (format: YYYYMMDD HHMMSS) |
| `Barcode1` | Customer name barcode (left-side barcode) |
| `Barcode2` | Delivery number barcode (right-side barcode) |
| `OutputPath` | Full path to the extracted PDF file |

### CSV Example

```csv
SequenceNo,DateTime,Barcode1,Barcode2,OutputPath
1,20250528 143025,AJC,DO250500001,/home/user/output/AJC_DO250500001.pdf
2,20250528 143025,CPS,86474,/home/user/output/CPS_86474.pdf
3,20250528 143025,RTG,103338,/home/user/output/RTG_103338.pdf
4,20250528 143025,SL,25698,/home/user/output/SL_25698.pdf
```

### Notes

- The CSV log is automatically generated for every successful run
- If a page has missing barcodes, the corresponding CSV fields will be empty
- The CSV file uses UTF-8 encoding to support special characters in barcode data
- Each run creates a new CSV file with a unique timestamp to prevent overwrites