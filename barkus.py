#!/usr/bin/env python3
"""
Barkus - PDF Barcode Splitter

This module processes PDF documents to detect both delivery number and customer name barcodes on each page,
and splits the PDF into separate files based on these barcode values.

Each output file is named using a combination of the delivery number and customer name barcodes found on its pages.
All pages with the same delivery number and customer name barcodes are grouped together into a single output PDF.

Main features:
- Detects two types of barcodes (delivery number and customer name) on each page
- Groups pages with identical barcode combinations
- Splits the PDF into separate files based on these barcode combinations 
- Names each output file using both barcode data values
- Preserves original page sequence in the new PDFs
"""

import os
import sys
import pikepdf
import cv2
import numpy as np
from pdf2image import convert_from_path
from pyzbar.pyzbar import decode
from collections import defaultdict
import logging
import csv
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('barkus')

# Class to handle verbosity for both console and log output
class VerbosityHandler:
    def __init__(self, verbose=True):
        self.verbose = verbose
        
    def info(self, message):
        logger.info(message)
        if self.verbose:
            print(message)
            
    def warning(self, message):
        logger.warning(message)
        if self.verbose:
            print(f"Warning: {message}")
    
    def error(self, message):
        logger.error(message)
        print(f"Error: {message}", file=sys.stderr)

def extract_barcodes_from_pdf(pdf_path, dpi=300, verbose=True):
    """Extract delivery number and customer name barcodes from each page of a PDF document.
    
    Args:
        pdf_path (str): Path to the PDF file
        dpi (int): DPI for rendering PDF pages (higher values may improve barcode detection)
        verbose (bool): Whether to display progress information
        
    Returns:
        dict: Dictionary mapping page numbers to barcode information containing
              'delivery_number' and 'customer_name' keys
    """
    vh = VerbosityHandler(verbose)
    page_barcodes = {}
    
    try:
        # Load PDF with pikepdf
        with pikepdf.open(pdf_path) as pdf_document:
            total_pages = len(pdf_document.pages)
            
            vh.info(f"Processing {total_pages} pages for barcodes...")
            
            # Convert PDF to images using pdf2image
            images = convert_from_path(pdf_path, dpi=dpi)
            
            for page_num, img in enumerate(images):
                if total_pages > 10 and page_num % 5 == 0:
                    vh.info(f"  Processing page {page_num+1}/{total_pages}...")
                    
                try:
                    # Convert PIL Image to OpenCV format
                    img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
                    
                    # Detect barcodes
                    detected_barcodes = decode(img_cv)
                    
                    if detected_barcodes:
                        barcode_info = {
                            'delivery_number': None,
                            'customer_name': None
                        }
                        
                        # We need to identify which barcode is which (delivery_number or customer_name)
                        if len(detected_barcodes) >= 2:
                            # Extract all barcode strings
                            barcode_strings = [bc.data.decode('utf-8') for bc in detected_barcodes]

                            # Identify which barcode is on the left (customer_name) and which is on the right (delivery_number)
                            # Sort barcodes by horizontal position (x-coordinate)
                            # Only consider barcodes that are significantly different in horizontal position
                            left_barcodes = []
                            right_barcodes = []

                            # First pass: detect range of horizontal positions
                            x_positions = [bc.rect.left for bc in detected_barcodes]
                            min_x = min(x_positions)
                            max_x = max(x_positions)
                            x_range = max_x - min_x

                            # Use 40% of the range as a threshold to distinguish left vs right
                            # This handles cases where there might be multiple barcodes on one side
                            threshold = min_x + (x_range * 0.4)

                            for bc in detected_barcodes:
                                if bc.rect.left < threshold:
                                    left_barcodes.append(bc)
                                else:
                                    right_barcodes.append(bc)

                            # Validation
                            if not left_barcodes:
                                vh.warning(f"No left-side (customer name) barcodes found on page {page_num+1}")
                            elif not right_barcodes:
                                vh.warning(f"No right-side (delivery order) barcodes found on page {page_num+1}")

                            # Take the first barcode from each side
                            if left_barcodes:
                                barcode_info['customer_name'] = left_barcodes[0].data.decode('utf-8')
                                if len(left_barcodes) > 1:
                                    extra_left = [bc.data.decode('utf-8') for bc in left_barcodes[1:]]
                                    vh.warning(f"  Multiple left-side barcodes found, using first one: {barcode_info['customer_name']}")
                                    vh.warning(f"  Unused left-side barcodes: {', '.join(extra_left)}")

                            if right_barcodes:
                                barcode_info['delivery_number'] = right_barcodes[0].data.decode('utf-8')
                                if len(right_barcodes) > 1:
                                    extra_right = [bc.data.decode('utf-8') for bc in right_barcodes[1:]]
                                    vh.warning(f"  Multiple right-side barcodes found, using first one: {barcode_info['delivery_number']}")
                                    vh.warning(f"  Unused right-side barcodes: {', '.join(extra_right)}")

                            vh.info(f"  Found barcodes on page {page_num+1}:")
                            vh.info(f"    Customer Name (left): {barcode_info.get('customer_name', 'UNKNOWN')}")
                            vh.info(f"    Delivery Number (right): {barcode_info.get('delivery_number', 'UNKNOWN')}")
                        
                        elif len(detected_barcodes) == 1:
                            # Only one barcode found - determine if it's on the left or right side
                            barcode_data = detected_barcodes[0].data.decode('utf-8')
                            bc = detected_barcodes[0]

                            # Check the position relative to the page width to decide if it's left or right
                            # Get image width
                            img_width = img_cv.shape[1]

                            # If barcode is in the left half of the page, it's customer name
                            if bc.rect.left < (img_width / 2):
                                barcode_info['customer_name'] = barcode_data
                                vh.warning(f"  Only one barcode found on page {page_num+1} (left side): {barcode_data}")
                                vh.warning(f"  Treating as Customer Name. No Delivery Number found.")
                            else:
                                # Right side barcode is delivery number
                                barcode_info['delivery_number'] = barcode_data
                                vh.warning(f"  Only one barcode found on page {page_num+1} (right side): {barcode_data}")
                                vh.warning(f"  Treating as Delivery Number. No Customer Name found.")

                            vh.warning(f"  Expected two barcodes (customer name on left, delivery number on right)")
                        
                        # Store the barcode information for this page
                        page_barcodes[page_num] = barcode_info
                
                except Exception as e:
                    vh.warning(f"Error processing page {page_num+1}: {str(e)}")
                    logger.exception(f"Exception while processing page {page_num+1}")
                    continue
            
            vh.info(f"Barcode detection complete. Found barcodes on {len(page_barcodes)}/{total_pages} pages.")
        
    except Exception as e:
        vh.error(f"Failed to process PDF: {str(e)}")
        logger.exception("Exception in extract_barcodes_from_pdf")
        raise
    
    return page_barcodes

def group_pages_by_barcode(page_barcodes):
    """Group page numbers by combined delivery number and customer name barcodes.
    
    Args:
        page_barcodes (dict): Dictionary mapping page numbers to barcode info dictionaries
                             with 'delivery_number' and 'customer_name' keys
                             
    Returns:
        dict: Dictionary mapping (delivery_number, customer_name) tuples to lists of page numbers
    """
    barcode_pages = defaultdict(list)
    
    for page_num, barcode_info in page_barcodes.items():
        delivery_number = barcode_info.get('delivery_number', 'UNKNOWN')
        customer_name = barcode_info.get('customer_name', 'UNKNOWN')
        
        # Use a tuple of both barcode types as the key to group pages
        barcode_key = (delivery_number, customer_name)
        barcode_pages[barcode_key].append(page_num)
    
    return barcode_pages

def split_pdf_by_barcodes(input_pdf_path, output_dir, dpi=300, verbose=True):
    """Split PDF into multiple files based on barcode groups.
    
    Args:
        input_pdf_path (str): Path to the input PDF file
        output_dir (str): Directory to save split PDFs
        dpi (int): DPI for rendering PDF pages for barcode detection
        verbose (bool): Whether to display progress information
        
    Returns:
        tuple: (barcode_pages dict, extraction_details list)
               barcode_pages: Dictionary mapping (delivery_number, customer_name) tuples to lists of page numbers
               extraction_details: List of dicts with CSV data for each created PDF
    """
    vh = VerbosityHandler(verbose)
    
    try:
        os.makedirs(output_dir, exist_ok=True)
        
        vh.info(f"Reading PDF: {input_pdf_path}")
        
        page_barcodes = extract_barcodes_from_pdf(input_pdf_path, dpi, verbose)
        barcode_pages = group_pages_by_barcode(page_barcodes)
        
        if not barcode_pages:
            vh.warning(f"No barcodes found in {input_pdf_path}")
            return {}, []
        
        vh.info(f"Found {len(barcode_pages)} unique barcode combinations. Creating output PDFs...")
        
        extraction_details = []
        sequence_no = 1
        current_datetime = datetime.now().strftime('%Y%m%d %H%M%S')
        
        # Open the source PDF with pikepdf
        with pikepdf.open(input_pdf_path) as pdf_document:
            
            for barcode_tuple, page_numbers in barcode_pages.items():
                delivery_number, customer_name = barcode_tuple
                
                # Create a filename that incorporates both customer name and delivery number
                # Only replace characters that cause issues on Windows filesystems
                # Windows disallows: < > : " / \ | ? *
                invalid_chars = '<>:"/\\|?*'
                safe_delivery = ''.join('_' if c in invalid_chars else c for c in str(delivery_number))
                safe_customer = ''.join('_' if c in invalid_chars else c for c in str(customer_name))
                
                # Use both values in filename if both are available
                # Put customer name first, then delivery number in the filename
                if delivery_number != 'UNKNOWN' and customer_name != 'UNKNOWN':
                    filename = f"{safe_customer}_{safe_delivery}.pdf"
                elif delivery_number != 'UNKNOWN':
                    filename = f"{safe_delivery}.pdf"
                elif customer_name != 'UNKNOWN':
                    filename = f"{safe_customer}.pdf"
                else:
                    filename = "unknown_barcode.pdf"
                    
                output_path = os.path.join(output_dir, filename)
                
                # Log which barcode values we're using
                barcode_info = f"Delivery: {delivery_number}"
                if customer_name != 'UNKNOWN':
                    barcode_info += f", Customer: {customer_name}"
                
                vh.info(f"  Creating PDF with {len(page_numbers)} pages: {output_path}")
                vh.info(f"    Barcode info: {barcode_info}")
                
                try:
                    # Create a new PDF
                    new_pdf = pikepdf.Pdf.new()
                    sorted_pages = sorted(page_numbers)
                    
                    # Copy pages from source to destination PDF
                    for page_num in sorted_pages:
                        new_pdf.pages.append(pdf_document.pages[page_num])
                    
                    # Save the new PDF
                    new_pdf.save(output_path)
                    logger.debug(f"Successfully created {output_path}")
                    
                    # Add extraction details for CSV log
                    extraction_details.append({
                        'SequenceNo': sequence_no,
                        'DateTime': current_datetime,
                        'Barcode1': customer_name if customer_name != 'UNKNOWN' else '',
                        'Barcode2': delivery_number if delivery_number != 'UNKNOWN' else '',
                        'OutputPath': output_path
                    })
                    sequence_no += 1
                    
                except Exception as e:
                    vh.error(f"Failed to create PDF for barcodes {barcode_tuple}: {str(e)}")
                    logger.exception(f"Exception creating PDF for barcodes {barcode_tuple}")
        
        vh.info(f"PDF splitting complete. Created {len(barcode_pages)} files in {output_dir}")
        
    except Exception as e:
        vh.error(f"Error splitting PDF: {str(e)}")
        logger.exception("Exception in split_pdf_by_barcodes")
        raise
    
    return barcode_pages, extraction_details

def write_csv_log(output_directory, extraction_data, verbose=True):
    """Write CSV log file with extraction details.
    
    Args:
        output_directory (str): Directory where CSV log will be saved
        extraction_data (list): List of dictionaries containing extraction details
        verbose (bool): Whether to display progress information
    """
    vh = VerbosityHandler(verbose)
    
    csv_filename = os.path.join(output_directory, f"extraction_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    
    try:
        with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['SequenceNo', 'DateTime', 'Barcode1', 'Barcode2', 'OutputPath']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            
            for row in extraction_data:
                writer.writerow(row)
        
        vh.info(f"CSV log written to: {csv_filename}")
        return csv_filename
        
    except Exception as e:
        vh.error(f"Failed to write CSV log: {str(e)}")
        logger.exception("Exception writing CSV log")
        return None

def process_pdf(input_pdf_path, output_directory="output", handle_no_barcode="ignore", dpi=300, verbose=True):
    """Main processing function.
    
    Args:
        input_pdf_path (str): Path to the input PDF file
        output_directory (str): Directory to save split PDFs
        handle_no_barcode (str): How to handle pages without barcodes:
                                 - "ignore": Skip pages without barcodes (default)
                                 - "separate": Create a separate PDF for pages without barcodes
                                 - "keep_with_previous": Include pages with the previous barcode group
                                 - "sequential": Include pages with no barcode with the last detected barcode until a new barcode is found
        dpi (int): DPI for rendering PDF pages for barcode detection
        verbose (bool): Whether to display progress information
    """
    vh = VerbosityHandler(verbose)
    
    if not os.path.exists(input_pdf_path):
        return {"error": f"Input file not found: {input_pdf_path}"}
    
    try:
        results, csv_data = split_pdf_by_barcodes(input_pdf_path, output_directory, dpi, verbose)
        
        # Optionally handle pages without barcodes
        with pikepdf.open(input_pdf_path) as pdf_document:
            total_pages = len(pdf_document.pages)
            no_barcode_pages = []
            
            # Find pages without barcodes
            for page_num in range(total_pages):
                found = False
                for pages in results.values():
                    if page_num in pages:
                        found = True
                        break
                
                if not found:
                    no_barcode_pages.append(page_num)
            
            if no_barcode_pages:
                vh.info(f"Found {len(no_barcode_pages)} pages without barcodes.")
            
            # Handle pages without barcodes based on the specified option
            if no_barcode_pages and handle_no_barcode != "ignore":
                if handle_no_barcode == "separate":
                    # Create a separate PDF for pages without barcodes
                    output_path = os.path.join(output_directory, "no_barcode.pdf")
                    vh.info(f"Creating separate PDF for pages without barcodes: {output_path}")
                    
                    try:
                        # Create a new PDF
                        new_pdf = pikepdf.Pdf.new()
                        
                        # Copy pages from source to destination PDF
                        for page_num in sorted(no_barcode_pages):
                            new_pdf.pages.append(pdf_document.pages[page_num])
                        
                        # Save the new PDF
                        new_pdf.save(output_path)
                        results[("NO_BARCODE", "NO_BARCODE")] = no_barcode_pages
                        vh.info(f"  Created no_barcode.pdf with {len(no_barcode_pages)} pages")
                        
                        # Add to CSV data
                        csv_data.append({
                            'SequenceNo': len(csv_data) + 1,
                            'DateTime': datetime.now().strftime('%Y%m%d %H%M%S'),
                            'Barcode1': '',
                            'Barcode2': '',
                            'OutputPath': output_path
                        })
                    except Exception as e:
                        vh.error(f"Failed to create PDF for pages without barcodes: {str(e)}")
                        logger.exception("Exception creating PDF for pages without barcodes")
                    
                elif handle_no_barcode == "keep_with_previous":
                    # Assign pages without barcodes to the previous barcode group
                    vh.info("Keeping pages without barcodes with previous barcode group")
                    prev_barcode_tuple = None
                    all_pages = sorted(list(range(total_pages)))
                    reassignments = {}  # Track reassignments for logging
                    
                    for page_num in all_pages:
                        # Find which barcode this page belongs to, if any
                        current_barcode_tuple = None
                        for barcode_tuple, pages in results.items():
                            if page_num in pages:
                                current_barcode_tuple = barcode_tuple
                                prev_barcode_tuple = barcode_tuple
                                break
                        
                        # If no barcode and we have a previous barcode, add to that group
                        if current_barcode_tuple is None and prev_barcode_tuple is not None and page_num in no_barcode_pages:
                            results[prev_barcode_tuple].append(page_num)
                            if prev_barcode_tuple not in reassignments:
                                reassignments[prev_barcode_tuple] = []
                            reassignments[prev_barcode_tuple].append(page_num)
                    
                    # Log reassignments
                    for barcode_tuple, pages in reassignments.items():
                        delivery_num, customer_name = barcode_tuple
                        barcode_info = f"Delivery: {delivery_num}"
                        if customer_name != 'UNKNOWN':
                            barcode_info += f", Customer: {customer_name}"
                        vh.info(f"  Reassigned {len(pages)} pages to barcodes '{barcode_info}'")
                
                elif handle_no_barcode == "sequential":
                    # Sequentially group pages - pages with no barcode belong to the last seen barcode
                    # until a new barcode is encountered
                    vh.info("Using sequential mode: pages with no barcode will be included with the last seen barcode")
                    
                    # Sort pages by their original order in the document
                    all_pages = list(range(total_pages))
                    
                    # Create a mapping of page number to barcode tuple
                    page_to_barcode = {}
                    for barcode_tuple, pages in results.items():
                        for page_num in pages:
                            page_to_barcode[page_num] = barcode_tuple
                    
                    # Process pages sequentially
                    current_barcode = None
                    reassignments = {}  # Track reassignments for logging
                    
                    for page_num in all_pages:
                        # If this page has a barcode, update the current barcode
                        if page_num in page_to_barcode:
                            current_barcode = page_to_barcode[page_num]
                        # If this page has no barcode but we have a current barcode, assign it to that group
                        elif current_barcode is not None and page_num in no_barcode_pages:
                            results[current_barcode].append(page_num)
                            if current_barcode not in reassignments:
                                reassignments[current_barcode] = []
                            reassignments[current_barcode].append(page_num)
                    
                    # Log reassignments
                    for barcode_tuple, pages in reassignments.items():
                        delivery_num, customer_name = barcode_tuple
                        barcode_info = f"Delivery: {delivery_num}"
                        if customer_name != 'UNKNOWN':
                            barcode_info += f", Customer: {customer_name}"
                        vh.info(f"  Sequentially assigned {len(pages)} pages to barcodes '{barcode_info}'")
                            
                    # Recreate PDFs with updated page assignments
                    for barcode_tuple, page_numbers in results.items():
                        if barcode_tuple == ("NO_BARCODE", "NO_BARCODE"):
                            continue
                            
                        delivery_number, customer_name = barcode_tuple
                        
                        # Create a filename that incorporates both customer name and delivery number
                        # Only replace characters that cause issues on Windows filesystems
                        # Windows disallows: < > : " / \ | ? *
                        invalid_chars = '<>:"/\\|?*'
                        safe_delivery = ''.join('_' if c in invalid_chars else c for c in str(delivery_number))
                        safe_customer = ''.join('_' if c in invalid_chars else c for c in str(customer_name))
                        
                        # Use both values in filename if both are available
                        # Put customer name first, then delivery number in the filename
                        if delivery_number != 'UNKNOWN' and customer_name != 'UNKNOWN':
                            filename = f"{safe_customer}_{safe_delivery}.pdf"
                        elif delivery_number != 'UNKNOWN':
                            filename = f"{safe_delivery}.pdf"
                        elif customer_name != 'UNKNOWN':
                            filename = f"{safe_customer}.pdf"
                        else:
                            filename = "unknown_barcode.pdf"
                        
                        output_path = os.path.join(output_directory, filename)
                        
                        # Log which barcode values we're using
                        barcode_info = f"Delivery: {delivery_number}"
                        if customer_name != 'UNKNOWN':
                            barcode_info += f", Customer: {customer_name}"
                        
                        try:
                            vh.info(f"  Recreating PDF with updated pages: {output_path}")
                            vh.info(f"    Barcode info: {barcode_info}")
                            
                            # Create a new PDF
                            new_pdf = pikepdf.Pdf.new()
                            sorted_pages = sorted(page_numbers)
                            
                            # Copy pages from source to destination PDF
                            for page_num in sorted_pages:
                                new_pdf.pages.append(pdf_document.pages[page_num])
                            
                            # Save the new PDF
                            new_pdf.save(output_path)
                        except Exception as e:
                            vh.error(f"Failed to update PDF for barcodes {barcode_tuple}: {str(e)}")
                            logger.exception(f"Exception updating PDF for barcodes {barcode_tuple}")
        
        # Write CSV log if there's any data to write
        csv_file_path = None
        if csv_data:
            csv_file_path = write_csv_log(output_directory, csv_data, verbose)
        
        # Prepare results in a format suitable for return
        processed_results = {}
        for barcode_tuple, pages in results.items():
            delivery_number, customer_name = barcode_tuple
            key = f"{delivery_number}_{customer_name}"
            
            processed_results[key] = {
                "delivery_number": delivery_number,
                "customer_name": customer_name,
                "pages": pages
            }
        
        return {
            "input_file": input_pdf_path,
            "output_directory": output_directory,
            "barcode_count": len(results),
            "no_barcode_pages": len(no_barcode_pages),
            "csv_log_file": csv_file_path,
            "results": processed_results
        }
    except Exception as e:
        logger.exception("Exception in process_pdf")
        return {"error": str(e)}

def main():
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
    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    if args.log_file:
        file_handler = logging.FileHandler(args.log_file)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(file_handler)
    
    verbose = not args.quiet
    
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
                else:
                    print("These pages were ignored (not included in any output file)")
                    
        logger.info(f"Successfully processed {args.input_pdf} into {results['barcode_count']} files")
        return 0
        
    except Exception as e:
        vh.error(f"An error occurred: {str(e)}")
        logger.exception("Unhandled exception in main")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())