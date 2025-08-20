# Barkus Application Layout

This document outlines the modular architecture of the Barkus PDF barcode splitter application.

## 1. Main Entry Point (`barkus_main.py`)

The application is initiated from `barkus_main.py`. This script is responsible for:

-   **Command-Line Argument Parsing**: It uses the `argparse` module to define and parse command-line arguments such as the input PDF file, output directory, DPI, and other processing options.
-   **Logging Setup**: It configures the application's logging based on the provided arguments (e.g., `--debug`, `--quiet`).
-   **Application Instantiation**: It creates an instance of the `BarkusApplication` class from the `application` module.
-   **Orchestration**: It calls the `process_pdf` method of the `BarkusApplication` instance, passing the parsed command-line arguments.
-   **Result Display**: It displays the final processing results to the user.

## 2. Core Application Logic (`barkus_modules/application.py`)

The `BarkusApplication` class in this module acts as the central orchestrator. Its key responsibilities include:

-   **Initialization**: It initializes instances of `PDFProcessor` and `FileOperations`.
-   **Processing Flow**: The `process_pdf` method defines the main workflow:
    1.  Validates the input file.
    2.  Calls `pdf_processor.split_pdf_by_barcodes` to perform the main splitting logic.
    3.  Handles pages without barcodes based on the user's selected mode.
    4.  Writes a CSV log of the extracted data using `file_operations`.
-   **Information Provider**: It contains methods to provide application information, system requirements, and processing time estimates.

## 3. Module Interconnections

The modules within `barkus_modules` are designed to be cohesive and loosely coupled. Here's how they interact:

### `barkus_modules/pdf_processor.py`

-   **Depends on**: `BarcodeDetector`, `VerbosityHandler`.
-   **Functionality**: This module is responsible for the core PDF manipulation tasks.
    -   It uses `BarcodeDetector` to extract barcodes from each page of the PDF.
    -   It groups pages based on the detected barcodes.
    -   It uses the `pikepdf` library to create new PDF files for each barcode group.
    -   It contains logic to handle pages without barcodes in various ways (e.g., creating a separate file, assigning them to the previous group).

### `barkus_modules/barcode_detector.py`

-   **Depends on**: `VerbosityHandler`, `zxing-cpp`, `pdf2image`, `opencv-python`.
-   **Functionality**: This module focuses on finding and interpreting barcodes.
    -   It converts PDF pages to images using `pdf2image`.
    -   It uses `zxing-cpp` to detect barcodes within the images.
    -   The `BarcodeClassifier` nested class categorizes barcodes as either "delivery number" or "customer name" based on their content.
    -   It includes retry logic with image enhancement (`opencv-python`) to improve detection rates for hard-to-read barcodes.

### `barkus_modules/file_operations.py`

-   **Depends on**: `VerbosityHandler`.
-   **Functionality**: This module provides a set of file system utilities.
    -   Creating and validating directories.
    -   Writing data to CSV log files.
    -   Generating safe filenames by removing invalid characters.
    -   Checking for file existence and size.

### `barkus_modules/logging_handler.py`

-   **Depends on**: `logging`, `sys`.
-   **Functionality**: This module provides a `VerbosityHandler` class for managing logging.
    -   It can write log messages to both the console and a specified log file.
    -   It supports different log levels (INFO, WARNING, ERROR, DEBUG).
    -   It ensures that all parts of the application have a consistent way of logging information.

## 4. Data Flow Summary

1.  `barkus_main.py` captures user input and starts `BarkusApplication`.
2.  `BarkusApplication` calls `PDFProcessor` to start the splitting process.
3.  `PDFProcessor` uses `BarcodeDetector` to get barcode data for each page.
4.  `BarcodeDetector` converts PDF pages to images and uses `zxing-cpp` to find barcodes.
5.  `PDFProcessor` receives the barcode data, groups the pages, and uses `pikepdf` to write new PDF files, with filenames cleaned by `FileOperations`.
6.  `BarkusApplication` uses `FileOperations` to write a summary CSV log.
7.  Throughout the process, all modules use `VerbosityHandler` for logging.
