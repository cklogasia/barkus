#!/usr/bin/env python3
"""
Barkus - PDF Barcode Splitter (Backward Compatibility Wrapper)

This file maintains backward compatibility with the original barkus.py interface
while using the new modular architecture internally.
"""

import sys
import os

# Add the current directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from barkus_modules.application import BarkusApplication
from barkus_modules.logging_handler import configure_logging


def process_pdf(input_pdf_path, output_directory="output", handle_no_barcode="ignore", dpi=300, verbose=True):
    """
    Main processing function - maintains original interface.
    
    Args:
        input_pdf_path (str): Path to the input PDF file
        output_directory (str): Directory to save split PDFs
        handle_no_barcode (str): How to handle pages without barcodes
        dpi (int): DPI for rendering PDF pages for barcode detection
        verbose (bool): Whether to display progress information
    
    Returns:
        dict: Processing results
    """
    configure_logging()
    app = BarkusApplication()
    return app.process_pdf(input_pdf_path, output_directory, handle_no_barcode, dpi, verbose)


def main():
    """Main function - maintains original interface."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Split PDF by delivery number and customer name barcodes")
    parser.add_argument("input_pdf", help="Path to input PDF file")
    parser.add_argument("--output-dir", "-o", default="output", help="Output directory")
    parser.add_argument("--dpi", type=int, default=300, help="DPI for barcode detection")
    parser.add_argument("--handle-no-barcode", choices=["ignore", "separate", "keep_with_previous", "sequential"],
                      default="ignore", help="How to handle pages without barcodes")
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress progress output")
    parser.add_argument("--log-file", default=None, help="Path to log file (default: no log file)")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()
    
    # Configure logging based on command-line options
    configure_logging()
    
    if args.debug:
        import logging
        logging.getLogger('barkus').setLevel(logging.DEBUG)
    
    if args.log_file:
        import logging
        file_handler = logging.FileHandler(args.log_file)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logging.getLogger('barkus').addHandler(file_handler)
    
    verbose = not args.quiet
    
    from barkus_modules.logging_handler import VerbosityHandler
    vh = VerbosityHandler(verbose)
    
    try:
        results = process_pdf(args.input_pdf, args.output_dir, args.handle_no_barcode, args.dpi, verbose)
        
        if "error" in results:
            vh.error(results["error"])
            return 1
        
        if not args.quiet:
            print(f"\nSplit PDF into {results['barcode_count']} files in {results['output_directory']}")
            print(f"Each file is named using the delivery number and customer name from barcodes")
            
            if "no_barcode_pages" in results and results["no_barcode_pages"] > 0:
                print(f"Found {results['no_barcode_pages']} pages without both required barcodes")
                if args.handle_no_barcode == "separate":
                    print("These pages were saved to no_barcode.pdf")
                elif args.handle_no_barcode == "keep_with_previous":
                    print("These pages were included with their preceding barcode groups")
                elif args.handle_no_barcode == "sequential":
                    print("These pages were included with the last detected barcode until a new one was found")
                else:
                    print("These pages were ignored (not included in any output file)")
                    
        import logging
        logging.getLogger('barkus').info(f"Successfully processed {args.input_pdf} into {results['barcode_count']} files")
        return 0
        
    except Exception as e:
        vh.error(f"An error occurred: {str(e)}")
        import logging
        logging.getLogger('barkus').exception("Unhandled exception in main")
        return 1
    finally:
        vh.close()


if __name__ == "__main__":
    sys.exit(main())