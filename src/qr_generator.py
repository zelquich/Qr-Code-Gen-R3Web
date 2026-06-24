import os
from typing import List
from io import BytesIO
from concurrent.futures import ProcessPoolExecutor, as_completed
import segno
from PIL import Image, ImageDraw, ImageFont
from models import EquipmentItem, Lieu
from config import config
from utils import slugify, ensure_dirs, logger

# region Font caching
_FONT_CACHE = None

def _get_font(size: int) -> ImageFont.FreeTypeFont:
    """Get or create a cached font at the given size."""
    global _FONT_CACHE
    if _FONT_CACHE is None or _FONT_CACHE.size != size:
        try:
            _FONT_CACHE = ImageFont.truetype("Arial.ttf", size)
        except IOError:
            _FONT_CACHE = ImageFont.load_default()
    assert _FONT_CACHE is ImageFont.FreeTypeFont, "Font cache could not be created properly."
    return _FONT_CACHE
# endregion

# region Public function: add_center_text
def add_center_text(img: Image.Image, text: str | None = None, color: tuple | None = None) -> Image.Image:
    """Add centered text overlay on an image with a white background box."""
    if text is None:
        text = config.qr_center_text
    if color is None:
        color = config.qr_center_color

    draw = ImageDraw.Draw(img)
    w, h = img.size

    font_size = int(min(w, h) * 0.12)
    # Use cached font instead of loading from disk each time
    font = _get_font(font_size)

    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    cx, cy = w / 2, h / 2
    x = cx - text_w / 2 - bbox[0]
    y = cy - text_h / 2 - bbox[1]

    margin = 2
    rect = [x + bbox[0] - margin, y + bbox[1] - margin,
            x + bbox[2] + margin, y + bbox[3] + margin]
    draw.rectangle(rect, fill="white")
    draw.text((x, y), text, fill=color, font=font)
    return img
# endregion

# region Internal helpers
def _make_qr_image(url: str, size_px: int | None = None) -> Image.Image:
    """Create a QR code image from a URL, resized and with center text."""
    if size_px is None:
        size_px = config.qr_size_px
    
    # Use segno for faster QR code generation
    qr = segno.make(url, error='m')
    
    # Get the number of modules to calculate proper scaling
    modules = qr.symbol_size()[0]
    scale = max(1, size_px // modules)
    
    # Save QR code to a BytesIO buffer and load it as PIL Image
    buffer = BytesIO()
    qr.save(buffer, kind='png', scale=scale, border=0, dark='black', light='white')
    buffer.seek(0)
    img = Image.open(buffer)
    
    # If the image isn't exactly the target size, resize it
    if img.size != (size_px, size_px):
        img = img.resize((size_px, size_px), Image.Resampling.LANCZOS)
    
    img = img.convert("RGB")
    return add_center_text(img)

def _create_lieu_directories(lieu_items: List[Lieu], lieu_paths: dict) -> None:
    """Create all directories for the given lieux and set their dir_path."""
    if not lieu_items or not lieu_paths:
        return

    for lieu in lieu_items:
        lieu_dir = lieu_paths.get(lieu.Id)
        if lieu_dir:
            os.makedirs(lieu_dir, exist_ok=True)
            lieu.dir_path = lieu_dir
            logger.debug(f"Created directory for lieu {lieu.name}: {lieu_dir}")

# region Worker functions for parallel processing
def _generate_one_equipment_qr(item: EquipmentItem, lieu_paths: dict, size_px: int) -> EquipmentItem:
    """Generate a single equipment QR code (worker function for parallel processing)."""
    filename = slugify(item.name) + ".png"

    if item.parent and item.parent.Id in lieu_paths:
        subdir = lieu_paths[item.parent.Id]
    elif item.lieu_path:
        lieu_parts = [slugify(part.strip()) for part in item.lieu_path.split(">")]
        subdir = os.path.join(config.qrcode_dir, *lieu_parts) if lieu_parts else config.qrcode_dir
    else:
        subdir = config.qrcode_dir

    os.makedirs(subdir, exist_ok=True)
    out_path = os.path.join(subdir, filename)

    img = _make_qr_image(item.pdf_url, size_px)
    img.save(out_path, format="PNG", optimize=True)

    item.qr_file_path = out_path
    return item

def _generate_one_lieu_qr(lieu: Lieu, lieu_paths: dict, size_px: int) -> tuple:
    """Generate a single lieu QR code (worker function for parallel processing).
    Returns (lieu_id, success) tuple."""
    lieu_full_path = lieu_paths.get(lieu.Id)
    if not lieu_full_path:
        return (lieu.Id, False)

    parent_dir = os.path.dirname(lieu_full_path) or config.qrcode_dir
    os.makedirs(parent_dir, exist_ok=True)

    filename = slugify(lieu.name) + ".png"
    out_path = os.path.join(parent_dir, filename)

    img = _make_qr_image(lieu.pdf_url, size_px)
    img.save(out_path, format="PNG", optimize=True)
    return (lieu.Id, True)
# endregion

def _generate_equipment_qr_codes(
    equipment_items: List[EquipmentItem], lieu_paths: dict
) -> None:
    """Generate and save a QR code for each piece of equipment using parallel processing."""
    if not equipment_items:
        return

    max_workers = min(os.cpu_count() or 4, len(equipment_items))
    logger.debug(f"Generating equipment QR codes using {max_workers} workers")

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_generate_one_equipment_qr, item, lieu_paths, config.qr_size_px): idx
            for idx, item in enumerate(equipment_items)
        }
        for future in as_completed(futures):
            idx = futures[future]
            try:
                equipment_items[idx] = future.result()
                logger.debug(f"Generated QR code for equipment {equipment_items[idx].name} (ID: {equipment_items[idx].Id})")
            except Exception as e:
                logger.error(f"Failed to generate QR code for equipment item at index {idx}: {e}")

def _generate_lieu_qr_codes(lieu_items: List[Lieu], lieu_paths: dict) -> int:
    """Generate QR codes for 'R' and 'G' lieux using parallel processing. Returns number of QR codes created."""
    count = 0
    if not lieu_items or not lieu_paths:
        return count

    # Filter lieux that need QR codes
    valid_lieux = [lieu for lieu in lieu_items if lieu.categorie in lieu.VALID_CATEGORIES_FOR_PDF]
    if not valid_lieux:
        return 0

    max_workers = min(os.cpu_count() or 4, len(valid_lieux))
    logger.debug(f"Generating lieu QR codes using {max_workers} workers")

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_generate_one_lieu_qr, lieu, lieu_paths, config.qr_size_px): lieu.Id
            for lieu in valid_lieux
        }
        for future in as_completed(futures):
            lieu_id = futures[future]
            try:
                result_id, success = future.result()
                if success:
                    count += 1
                    logger.debug(f"Generated QR code for lieu (ID: {result_id})")
                else:
                    logger.debug(f"Could not determine path for lieu (ID: {result_id})")
            except Exception as e:
                logger.error(f"Failed to generate QR code for lieu (ID: {lieu_id}): {e}")

    return count
# endregion

# region Main entry point (generate_qr_codes)
def generate_qr_codes(
    equipment_items: List[EquipmentItem],
    lieu_items: List[Lieu] | None = None,
    lieu_paths: dict | None = None,
) -> None:
    """
    Generate QR codes and directories for equipment and lieux.

    - Creates directories for all lieux based on their hierarchy
    - Creates QR codes for lieux that are "R" (ensemble) or "G" (sous ensemble)
    - Creates QR codes for all equipment items
    - Uses parallel processing for faster generation
    """
    logger.info("Starting QR code generation...")
    ensure_dirs(config.qrcode_dir, config.pdf_dir)

    if lieu_paths is None:
        lieu_paths = {}
    
    assert lieu_items is not None, "lieu_items must be provided to create directories"

    # 1. Create all lieu directories (must be done in main process before parallel generation)
    _create_lieu_directories(lieu_items, lieu_paths)

    # 2. Equipment QR codes (each in its parent lieu directory) - parallelized
    _generate_equipment_qr_codes(equipment_items, lieu_paths)

    # 3. Lieu QR codes (only for R / G categories) in parent directory - parallelized
    lieu_qr_count = _generate_lieu_qr_codes(lieu_items, lieu_paths)

    logger.info(f"Generated {len(equipment_items)} equipment QR codes and {lieu_qr_count} lieu QR codes")
# endregion