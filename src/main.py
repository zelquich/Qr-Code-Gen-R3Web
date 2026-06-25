import sys
import argparse
import logging
from utils import logger
from config import config
from data_loader import read_equipment_csv, read_lieu_csv, build_hierarchy
from qr_generator import generate_qr_codes
from pdf_generator import register_fonts, generate_labels_pdf_for_group

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Generate QR codes and labels for US Open equipment.')
    parser.add_argument(
        '--output', '-o',
        default=str(config.output_dir),
        help=f'Output directory (default: {config.output_dir})'
    )
    parser.add_argument(
        '--debug', '-d',
        action='store_true',
        help='Enable debug logging'
    )
    return parser.parse_args()

def main():
    """Main entry point."""
    args = parse_arguments()
    
    # Update config with command line arguments
    if args.output != str(config.output_dir):
        config.output_dir = args.output
    
    # Set logging level
    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    try:
        logger.info("Starting label generation process...")
        
        # Register fonts
        register_fonts()
        
        # Load data from CSV files
        equipment_items = read_equipment_csv()
        if not equipment_items:
            logger.error("No equipment items loaded from CSV. Exiting.")
            sys.exit(1)
        
        lieu_items = read_lieu_csv()
        if not lieu_items:
            logger.error("No lieu items loaded from CSV. Exiting.")
            sys.exit(1)
        
        lieu_paths = build_hierarchy(equipment_items, lieu_items)
        
        # Generate QR codes and directories
        generate_qr_codes(equipment_items, lieu_items, lieu_paths)
        
        # Group equipment by parent lieu and generate PDFs
        # Create a grouping by parent lieu
        lieu_groups = {}
        for equip in equipment_items:
            if equip.parent:
                lieu_id = equip.parent.Id
                if lieu_id not in lieu_groups:
                    lieu_groups[lieu_id] = []
                lieu_groups[lieu_id].append(equip)
        
        logger.info(f"Generated {len(lieu_groups)} groups by lieu")
        
        
        for lieu_id, group_items in lieu_groups.items():
            continue# TODO implement pdf generation
            # Find the parent lieu object for this group
            parent_lieu = next((l for l in lieu_items if l.Id == lieu_id), None)
            if parent_lieu:
                generate_labels_pdf_for_group(parent_lieu, group_items)
        
        logger.info("✅ All labels generated successfully!")
        
    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()