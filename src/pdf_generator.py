import os
from typing import List, Optional, Tuple
from pathlib import Path
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from models import EquipmentItem
from config import config
from utils import wrap_text_lines, slugify, format_datetime, logger, check_file_exists


def register_fonts() -> bool:
    """
    Register fonts with ReportLab.
    Returns True if at least one font was registered successfully.
    """
    success = False
    
    try:
        bold_path = config.font_bold_path
        if check_file_exists(bold_path, "Bold font"):
            pdfmetrics.registerFont(TTFont(config.font_bold, str(bold_path)))
            logger.info(f"Registered bold font: {bold_path}")
            success = True
        else:
            logger.warning("Bold font not found, text may render incorrectly")
    except Exception as e:
        logger.warning(f"Could not register bold font: {e}")
    
    try:
        medium_path = config.font_medium_path
        if check_file_exists(medium_path, "Medium font"):
            pdfmetrics.registerFont(TTFont(config.font_medium, str(medium_path)))
            logger.info(f"Registered medium font: {medium_path}")
            success = True
        else:
            logger.warning("Medium font not found, text may render incorrectly")
    except Exception as e:
        logger.warning(f"Could not register medium font: {e}")
    
    return success


def draw_label(
    c: canvas.Canvas,
    x_mm: float,
    y_mm: float,
    item: EquipmentItem,
    logo_img: Optional[Path]
) -> None:
    """
    Draw a single label at the specified position.
    
    Args:
        c: ReportLab canvas
        x_mm: X position in millimeters
        y_mm: Y position in millimeters
        item: Equipment item data
        logo_img: Path to logo image (or None)
    """
    x = x_mm * mm
    y = y_mm * mm
    
    label_w = config.label_width_mm * mm
    label_h = config.label_height_mm * mm
    
    # --- Frame ---
    c.setLineWidth(0.4)
    c.rect(x, y, label_w, label_h, stroke=1, fill=0)
    
    # --- Text settings ---
    font_name = config.font_medium
    font_size_piece = config.piece_font_size
    font_size_equip = config.equip_font_size
    line_h_mm = 3
    line_h = line_h_mm * mm
    
    margin_top = config.label_area_margin_top_mm * mm
    margin_bottom = config.label_area_margin_bottom_mm * mm
    max_text_width_mm = config.label_width_mm - 4
    
    piece_txt = item.piece
    equip_txt = item.equipement
    
    # --- TOP TEXT SECTION ---
    # Pièce (2 lines max)
    piece_lines_top = wrap_text_lines(
        piece_txt,
        max_text_width_mm,
        font_name,
        font_size_piece,
        max_lines=config.max_text_lines
    )
    # Équipement (1 line)
    equip_lines_top = wrap_text_lines(
        equip_txt,
        max_text_width_mm,
        font_name,
        font_size_equip,
        max_lines=1
    )
    
    top_lines = piece_lines_top + equip_lines_top
    top_start_y = y + label_h - margin_top - 1 * mm
    y_top_block_bottom = top_start_y - len(top_lines) * line_h
    
    for i, line in enumerate(top_lines):
        if i < len(piece_lines_top):
            # Pièce in blue
            c.setFont(font_name, font_size_piece)
            c.setFillColorRGB(*config.piece_color)
        else:
            # Équipement in black
            c.setFont(font_name, font_size_equip)
            c.setFillColorRGB(0, 0, 0)
        
        c.drawCentredString(x + label_w / 2, top_start_y, line)
        top_start_y -= line_h
    
    # --- BOTTOM TEXT SECTION ---
    # Équipement (1 line)
    equip_lines_bottom = wrap_text_lines(
        equip_txt,
        max_text_width_mm,
        font_name,
        font_size_equip,
        max_lines=1
    )
    # Pièce (2 lines max)
    piece_lines_bottom = wrap_text_lines(
        piece_txt,
        max_text_width_mm,
        font_name,
        font_size_piece,
        max_lines=config.max_text_lines
    )
    
    bottom_lines = equip_lines_bottom + piece_lines_bottom
    bottom_start_y = y + margin_bottom + (len(bottom_lines) - 1) * line_h
    y_bottom_block_top = y + margin_bottom + len(bottom_lines) * line_h
    
    for i, line in enumerate(bottom_lines):
        orig_idx = len(bottom_lines) - 1 - i
        if orig_idx < len(piece_lines_bottom):
            # Pièce in blue
            c.setFont(font_name, font_size_equip)
            c.setFillColorRGB(*config.piece_color)
        else:
            # Équipement in black
            c.setFont(font_name, font_size_piece)
            c.setFillColorRGB(0, 0, 0)
        
        c.drawCentredString(x + label_w / 2, bottom_start_y, line)
        bottom_start_y -= line_h
    
    # Reset color to black
    c.setFillColorRGB(0, 0, 0)
    
    # --- CENTRAL ZONE: QR CODE + LOGO ---
    # Calculate available space for QR code and logo
    center_zone_bottom = y_bottom_block_top + line_h_mm * 0.5 * mm
    center_zone_top = y_top_block_bottom - line_h_mm * 0.5 * mm
    center_zone_h = max(center_zone_top - center_zone_bottom, 5 * mm)
    
    # QR code dimensions
    qr_size_mm = 20
    qr_w = qr_h = qr_size_mm * mm
    
    # Logo dimensions
    logo_w_mm = 16
    logo_h_mm = 6
    logo_w = logo_w_mm * mm
    logo_h = logo_h_mm * mm if logo_img else 0
    
    # Gap between QR and logo
    gap_mm = 0.5
    gap = gap_mm * mm if logo_img else 0
    
    # Total height needed for QR + logo
    center_block_h = qr_h + logo_h + gap
    
    # Scale down if needed to fit
    if center_block_h > center_zone_h:
        scale = center_zone_h / center_block_h
        qr_w *= scale
        qr_h *= scale
        logo_w *= scale
        logo_h *= scale
        center_block_h = qr_h + logo_h + gap
    
    # Center the block vertically
    block_bottom = center_zone_bottom + (center_zone_h - center_block_h) / 2
    
    # Draw QR code
    qr_x = x + (label_w - qr_w) / 2
    qr_y = block_bottom + (logo_h + gap if logo_img else 0)
    
    try:
        if item.qr_path and Path(item.qr_path).exists():
            c.drawImage(
                str(item.qr_path),
                qr_x,
                qr_y,
                width=qr_w,
                height=qr_h,
                preserveAspectRatio=True,
                mask="auto",
            )
        else:
            logger.warning(f"QR code not found for {item.equipement}")
    except Exception as e:
        logger.error(f"Failed to draw QR code for {item.equipement}: {e}")
    
    # Draw logo below QR code
    if logo_img and Path(logo_img).exists():
        logo_x = x + (label_w - logo_w) / 2
        logo_y = block_bottom
        try:
            c.drawImage(
                str(logo_img),
                logo_x,
                logo_y,
                width=logo_w,
                height=logo_h,
                preserveAspectRatio=True,
                mask="auto",
            )
        except Exception as e:
            logger.error(f"Failed to draw logo: {e}")


def draw_page_frame(
    c: canvas.Canvas,
    zone: str,
    chambre: str,
    localtech: str,
    page_num: int = 1,
    page_count: int = 1
) -> None:
    """
    Draw the title band and footer for a page.
    
    Args:
        c: ReportLab canvas
        zone: Zone name
        chambre: Chamber name
        localtech: Technical room name
        page_num: Current page number
        page_count: Total page count
    """
    # --- TITLE BAND ---
    title_x = config.title_left_mm * mm
    title_y = (config.page_height_mm - config.title_top_mm - config.title_height_mm) * mm
    title_w = (config.page_width_mm - config.title_left_mm - config.title_right_mm) * mm
    title_h = config.title_height_mm * mm
    
    # Draw title band rectangle
    c.setLineWidth(3 / 2.835)  # Convert from points to mm (1 point = 1/72 inch)
    c.rect(title_x, title_y, title_w, title_h, stroke=1, fill=0)
    
    # --- US OPEN LOGO (right side of title) ---
    text_start_x = title_x + 4 * mm
    
    if check_file_exists(config.logo_path, "US Open logo"):
        logo_max_h_mm = config.title_height_mm - 6
        logo_max_h = logo_max_h_mm * mm
        logo_max_w = logo_max_h * 3  # Maintain aspect ratio
        
        logo_x = title_x + title_w - logo_max_w - 2 * mm
        logo_y = title_y + (title_h - logo_max_h) / 2
        
        try:
            c.drawImage(
                str(config.logo_path),
                logo_x,
                logo_y,
                width=logo_max_w,
                height=logo_max_h,
                preserveAspectRatio=True,
                mask="auto",
            )
            # Adjust text start to avoid overlapping with logo
            text_start_x = title_x + 4 * mm
        except Exception as e:
            logger.error(f"Failed to draw US Open logo: {e}")
    
    # --- TITLE TEXT ---
    # Zone
    c.setFont(config.font_bold, config.title_font_size_zone)
    c.setFillColorRGB(*config.title_zone_color)
    c.drawString(text_start_x, title_y + title_h - 8 * mm, zone)
    
    # Chamber
    c.setFont(config.font_bold, config.title_font_size_chamber)
    c.setFillColorRGB(*config.title_chamber_color)
    c.drawString(text_start_x, title_y + title_h - 15 * mm, f"Pulling chamber: {chambre}")
    
    # Technical room
    c.setFont(config.font_bold, config.title_font_size_techroom)
    c.setFillColorRGB(*config.title_techroom_color)
    c.drawString(text_start_x, title_y + title_h - 22 * mm, f"Technical room: {localtech}")
    
    # Reset color
    c.setFillColorRGB(0, 0, 0)
    
    # --- FOOTER ---
    footer_x = config.footer_left_mm * mm
    footer_y = config.footer_bottom_mm * mm
    footer_w = (config.page_width_mm - config.footer_left_mm - config.footer_right_mm) * mm
    footer_h = config.footer_height_mm * mm
    
    # Draw footer rectangle
    c.setLineWidth(3 / 2.835)
    c.rect(footer_x, footer_y, footer_w, footer_h, stroke=1, fill=0)
    
    # --- FOOTER CONTENT ---
    footer_center_y = footer_y + footer_h / 2 - 3
    
    # Left: Generation date/time
    c.setFont(config.font_medium, config.footer_font_size)
    gen_text = format_datetime()
    c.drawString(footer_x + 4 * mm, footer_center_y, gen_text)
    
    # Center: Synoptic logo
    if check_file_exists(config.synoptic_logo_path, "Synoptic logo"):
        syn_max_h = (config.footer_height_mm - 4) * mm
        syn_max_w = syn_max_h * 3  # Maintain aspect ratio
        syn_x = footer_x + footer_w / 2 - syn_max_w / 2
        syn_y = footer_y + (footer_h - syn_max_h) / 2
        
        try:
            c.drawImage(
                str(config.synoptic_logo_path),
                syn_x,
                syn_y,
                width=syn_max_w,
                height=syn_max_h,
                preserveAspectRatio=True,
                mask="auto",
            )
        except Exception as e:
            logger.error(f"Failed to draw Synoptic logo: {e}")
    
    # Right: Page numbers
    c.setFont(config.font_medium, config.footer_font_size)
    page_text = f"Page {page_num} / {page_count}"
    text_width = c.stringWidth(page_text, config.font_medium, config.footer_font_size)
    right_margin = footer_x + footer_w - 4 * mm
    c.drawString(right_margin - text_width, footer_center_y, page_text)


def generate_labels_pdf_for_group(
    key: Tuple[str, str, str],
    items: List[EquipmentItem]
) -> Optional[Path]:
    """
    Generate PDF with labels for a specific group.
    
    Args:
        key: Tuple of (zone, chambre, localtech)
        items: List of equipment items in this group
    
    Returns:
        Path to generated PDF, or None if generation failed
    """
    zone, chambre, localtech = key
    
    # Create PDF filename
    slug_title = slugify(f"{zone}_{chambre}_{localtech}")
    pdf_path = config.pdf_dir / f"etiquettes_{slug_title}.pdf"
    
    logger.info(f"Generating PDF for group: {zone} ({len(items)} items)")
    
    try:
        # Create canvas
        c = canvas.Canvas(str(pdf_path), pagesize=A4)
        
        # Calculate label area boundaries
        label_area_top_mm = (
            config.page_height_mm
            - config.title_top_mm
            - config.title_height_mm
            - config.label_area_margin_top_mm
        )
        
        # Load logo if available
        logo_img = config.logo_path if config.logo_path.exists() else None
        
        # Page layout
        col = 0
        row = 0
        page_num = 1
        per_page = config.cols * config.rows
        page_count = max(1, (len(items) + per_page - 1) // per_page)
        
        # Draw first page frame
        draw_page_frame(c, zone, chambre, localtech, page_num, page_count)
        
        # Draw labels
        for idx, item in enumerate(items):
            # Check if we need a new page
            if row >= config.rows:
                c.showPage()
                page_num += 1
                draw_page_frame(c, zone, chambre, localtech, page_num, page_count)
                col = 0
                row = 0
            
            # Calculate label position
            x_mm = config.title_left_mm + col * (config.label_width_mm + config.label_gap_mm)
            y_mm = (
                label_area_top_mm
                - (row + 1) * config.label_height_mm
                - row * config.label_gap_mm
            )
            
            # Draw the label
            draw_label(c, x_mm, y_mm, item, logo_img)
            
            # Move to next position
            col += 1
            if col >= config.cols:
                col = 0
                row += 1
        
        # Save the PDF
        c.showPage()
        c.save()
        
        logger.info(f"✅ PDF generated: {pdf_path}")
        return pdf_path
        
    except Exception as e:
        logger.error(f"Failed to generate PDF for group {zone}: {e}", exc_info=True)
        return None


def generate_all_pdfs(groups: dict) -> List[Path]:
    """
    Generate PDFs for all groups.
    
    Args:
        groups: Dictionary of groups from data_loader.group_items()
    
    Returns:
        List of generated PDF paths
    """
    generated_pdfs = []
    
    for key, group_items in groups.items():
        pdf_path = generate_labels_pdf_for_group(key, group_items)
        if pdf_path:
            generated_pdfs.append(pdf_path)
    
    logger.info(f"Generated {len(generated_pdfs)} PDFs in total")
    return generated_pdfs


def generate_pdf_preview(
    items: List[EquipmentItem],
    output_path: Optional[Path] = None
) -> Optional[Path]:
    """
    Generate a single PDF with all items as a preview.
    Useful for testing without grouping.
    
    Args:
        items: List of equipment items
        output_path: Custom output path (optional)
    
    Returns:
        Path to generated PDF, or None if generation failed
    """
    if output_path is None:
        output_path = config.pdf_dir / "preview_labels.pdf"
    
    logger.info(f"Generating preview PDF: {output_path}")
    
    try:
        # Group temporarily with dummy key
        dummy_key = ("Preview", "All", "Items")
        return generate_labels_pdf_for_group(dummy_key, items)
    except Exception as e:
        logger.error(f"Failed to generate preview PDF: {e}")
        return None