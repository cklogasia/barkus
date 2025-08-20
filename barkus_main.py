#!/usr/bin/env python3
"""
Barkus - PDF Barcode Splitter (Main Entry Point)

This is the main entry point for the Barkus PDF barcode splitter application.
It provides a command-line interface and orchestrates all the modular components.

Usage:
    python barkus_main.py input.pdf [options]

The application has been modularized following Clean Code principles:
- logging_handler: Handles all logging operations
- barcode_detector: Detects and classifies barcodes
- pdf_processor: Processes and splits PDF documents
- file_operations: Manages file I/O operations
- application: Main application orchestration
"""

import sys
import argparse
from typing import Optional

from barkus_modules.application import BarkusApplication
from barkus_modules.logging_handler import VerbosityHandler


def create_argument_parser() -> argparse.ArgumentParser:
    """
    Create and configure the command-line argument parser.
    
    Returns:
        argparse.ArgumentParser: Configured argument parser
    """
    parser = argparse.ArgumentParser(
        description="Split PDF by delivery number and customer name barcodes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s document.pdf
    %(prog)s document.pdf --output-dir results
    %(prog)s document.pdf --handle-no-barcode sequential --dpi 600
    %(prog)s document.pdf --quiet --log-file processing.log

Handle No Barcode Options:
    ignore              Skip pages without barcodes (default)
    separate            Create separate PDF for pages without barcodes
    keep_with_previous  Include pages with previous barcode group
    sequential          Include pages with last detected barcode until new one found
        """
    )
    
    # Required arguments (made optional when using --info)
    parser.add_argument(
        "input_pdf",
        nargs='?',
        help="Path to input PDF file"
    )
    
    # Optional arguments
    parser.add_argument(
        "--output-dir", "-o",
        default="output",
        help="Output directory (default: output)"
    )
    
    parser.add_argument(
        "--dpi",
        type=int,
        default=300,
        help="DPI for barcode detection (default: 300)"
    )
    
    parser.add_argument(
        "--handle-no-barcode",
        choices=["ignore", "separate", "keep_with_previous", "sequential"],
        default="ignore",
        help="How to handle pages without barcodes (default: ignore)"
    )
    
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress progress output"
    )
    
    parser.add_argument(
        "--log-file",
        default=None,
        help="Path to log file (default: auto-generated in output directory)"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="Barkus PDF Barcode Splitter 1.0.0"
    )
    
    parser.add_argument(
        "--info",
        action="store_true",
        help="Show application information and exit"
    )
    
    parser.add_argument(
        "--estimate",
        action="store_true",
        help="Estimate processing time and exit"
    )
    
    return parser


def setup_logging(debug: bool = False) -> None:
    """
    Set up application logging.
    
    Args:
        debug (bool): Whether to enable debug logging
    """
    import logging
    from barkus_modules.logging_handler import configure_logging
    
    configure_logging()
    
    if debug:
        logging.getLogger('barkus').setLevel(logging.DEBUG)


def validate_arguments(args: argparse.Namespace) -> tuple[bool, Optional[str]]:
    """
    Validate command-line arguments.
    
    Args:
        args (argparse.Namespace): Parsed command-line arguments
        
    Returns:
        tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    # Validate DPI range
    if args.dpi < 50 or args.dpi > 1200:
        return False, "DPI must be between 50 and 1200"
    
    # Validate input file extension
    if not args.input_pdf.lower().endswith('.pdf'):
        return False, "Input file must be a PDF file"
    
    return True, None


def handle_info_request(app: BarkusApplication) -> None:
    """
    Handle the --info flag by displaying application information.
    
    Args:
        app (BarkusApplication): Application instance
    """
    info = app.get_application_info()
    requirements = app.get_system_requirements()
    
    print("=" * 60)
    print(f"Application: {info['name']}")
    print(f"Version: {info['version']}")
    print(f"Description: {info['description']}")
    print()
    print("Supported Formats:")
    for fmt in info['supported_formats']:
        print(f"  - {fmt}")
    print()
    print("Barcode Types:")
    for barcode_type in info['barcode_types']:
        print(f"  - {barcode_type}")
    print()
    print("System Requirements:")
    print(f"  Python: {requirements['python_version']}")
    print(f"  RAM: {requirements['minimum_ram']} (minimum), {requirements['recommended_ram']} (recommended)")
    print(f"  Disk Space: {requirements['disk_space']}")
    print()
    print("Required Packages:")
    for package in requirements['required_packages']:
        print(f"  - {package}")
    print()
    print("System Dependencies:")
    for dep in requirements['system_dependencies']:
        print(f"  - {dep}")
    print("=" * 60)


def handle_estimate_request(app: BarkusApplication, input_pdf: str, dpi: int) -> None:
    """
    Handle the --estimate flag by displaying processing time estimate.
    
    Args:
        app (BarkusApplication): Application instance
        input_pdf (str): Path to input PDF
        dpi (int): DPI setting
    """
    estimate = app.estimate_processing_time(input_pdf, dpi)
    
    if estimate is not None:
        minutes = int(estimate // 60)
        seconds = int(estimate % 60)
        
        print(f"Estimated processing time: {minutes}m {seconds}s")
        print(f"  - Based on DPI: {dpi}")
        print(f"  - Input file: {input_pdf}")
        
        # Show file size
        from barkus_modules.file_operations import FileOperations
        file_size = FileOperations.get_file_size(input_pdf)
        size_mb = file_size / (1024 * 1024)
        print(f"  - File size: {size_mb:.1f} MB")
    else:
        print("Could not estimate processing time (file may not be accessible)")


def display_results(results: dict, args: argparse.Namespace) -> None:
    """
    Display processing results to the user.
    
    Args:
        results (dict): Processing results
        args (argparse.Namespace): Command-line arguments
    """
    if not args.quiet:
        print(f"\nProcessing completed successfully!")
        print(f"Split PDF into {results['barcode_count']} files in {results['output_directory']}")
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
                print("These pages were ignored (not included in any output files)")
        
        if results.get("csv_log_file"):
            print(f"CSV summary: {results['csv_log_file']}")
        
        if results.get("detailed_log_file"):
            print(f"Detailed log: {results['detailed_log_file']}")


def main() -> int:
    """
    Main entry point for the Barkus application.
    
    Returns:
        int: Exit code (0 for success, 1 for error)
    """
    # Parse command-line arguments
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Create application instance
    app = BarkusApplication()
    
    # Handle special flags
    if args.info:
        handle_info_request(app)
        return 0
    
    if args.estimate:
        if not args.input_pdf:
            print("Error: --estimate requires an input PDF file", file=sys.stderr)
            return 1
        handle_estimate_request(app, args.input_pdf, args.dpi)
        return 0
    
    # Set up logging
    setup_logging(args.debug)
    
    # Check if input_pdf is required
    if not args.input_pdf:
        print("Error: input_pdf is required", file=sys.stderr)
        return 1
    
    # Validate arguments
    is_valid, error_message = validate_arguments(args)
    if not is_valid:
        print(f"Error: {error_message}", file=sys.stderr)
        return 1
    
    # Create verbosity handler for main function
    verbose = not args.quiet
    vh = VerbosityHandler(verbose)
    
    try:
        # Process the PDF
        results = app.process_pdf(
            input_pdf_path=args.input_pdf,
            output_directory=args.output_dir,
            handle_no_barcode=args.handle_no_barcode,
            dpi=args.dpi,
            verbose=verbose
        )
        
        # Check for errors
        if "error" in results:
            vh.error(results["error"])
            return 1
        
        # Display results
        display_results(results, args)
        
        # Log success
        import logging
        logging.getLogger('barkus').info(f"Successfully processed {args.input_pdf} into {results['barcode_count']} files")
        
        return 0
        
    except KeyboardInterrupt:
        vh.error("Processing interrupted by user")
        return 1
    except Exception as e:
        vh.error(f"An unexpected error occurred: {str(e)}")
        import logging
        logging.getLogger('barkus').exception("Unhandled exception in main")
        return 1
    finally:
        vh.close()


if __name__ == "__main__":
    sys.exit(main())