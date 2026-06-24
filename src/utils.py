import os
import logging
from pathlib import Path
from typing import List, Optional
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.lib.units import mm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_file_exists(file_path: Path, description: str = "File") -> bool:
    """Check if a file exists and log warning if not."""
    if not file_path.exists():
        logger.warning(f"{description} not found: {file_path}")
        return False
    return True

def get_project_structure() -> dict:
    """Return the project directory structure for documentation."""
    from config import config
    return {
        "root": config.project_root,
        "src": config.src_dir,
        "data": config.data_dir,
        "assets": config.assets_dir,
        "fonts": config.fonts_dir,
        "images": config.images_dir,
        "output": config.output_dir,
    }

def slugify(text: str) -> str:
    """Convert text to a safe filename."""
    for ch in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']:
        text = text.replace(ch, '-')
    return text.replace(' ', '_')

def ensure_dirs(qrcode_dir: str | Path, pdf_dir: str | Path) -> None:
    """Create output directories if they don't exist."""
    os.makedirs(qrcode_dir, exist_ok=True)
    os.makedirs(pdf_dir, exist_ok=True)
    logger.info(f"Directories ensured: {qrcode_dir}, {pdf_dir}")

def wrap_text_lines(
    text: str, 
    max_width_mm: float, 
    font_name: str, 
    font_size: int, 
    max_lines: int = 2
) -> List[str]:
    """
    Wrap text to fit within a maximum width.
    Returns a list of lines, up to max_lines.
    """
    if not text:
        return []
    
    max_width = max_width_mm * mm
    words = text.split()
    lines = []
    current = ""
    
    for w in words:
        test = (current + " " + w).strip()
        if stringWidth(test, font_name, font_size) <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
                if len(lines) >= max_lines:
                    return lines
            current = w
    
    if current and len(lines) < max_lines:
        lines.append(current)
    
    return lines

def format_datetime() -> str:
    """Return formatted current datetime."""
    from datetime import datetime
    return datetime.now().strftime("Generated on %Y-%m-%d %H:%M")