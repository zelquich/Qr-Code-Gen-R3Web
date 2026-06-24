import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

@dataclass
class Config:
    # Project root (where this file is located)
    project_root: Path = Path(__file__).parent.parent
    
    # Directory structure
    src_dir: Path = Path(__file__).parent
    data_dir: Path = project_root / "data"
    assets_dir: Path = project_root / "assets"
    fonts_dir: Path = assets_dir / "fonts"
    images_dir: Path = assets_dir / "images"
    output_dir: Path = project_root / "output"
    
    # Input files (relative to data_dir)
    xlsx_file: str = "etiquette_US-open.xlsx"  # Will be resolved as data_dir / xlsx_file
    equipement_path_csv: str = "chemins equipements.csv"
    Lieu_csv: str = "infos Lieu.csv"
    
    # Asset files (relative to assets/images)
    logo_file: str = "Usopen-header-logo.png"
    synoptic_logo_file: str = "SYNOPTIC-LOGO.png"
    
    @property
    def xlsx_path(self) -> Path:
        return self.data_dir / self.xlsx_file
    
    @property
    def equipement_path_csv_path(self) -> Path:
        return self.data_dir / self.equipement_path_csv
    
    @property
    def Lieu_csv_path(self) -> Path:
        return self.data_dir / self.Lieu_csv
    
    @property
    def logo_path(self) -> Path:
        return self.images_dir / self.logo_file
    
    @property
    def synoptic_logo_path(self) -> Path:
        return self.images_dir / self.synoptic_logo_file
    
    @property
    def font_bold_path(self) -> Path:
        return self.fonts_dir / "SourceCodePro-Bold.ttf"
    
    @property
    def font_medium_path(self) -> Path:
        return self.fonts_dir / "SourceCodePro-Medium.ttf"
    
    @property
    def qrcode_dir(self) -> Path:
        return self.output_dir / "qrcodes"
    
    @property
    def pdf_dir(self) -> Path:
        return self.output_dir / "pdf"
    
    # QR code settings
    qr_size_px: int = 180
    qr_center_text: str = "FIBER"
    qr_center_color: tuple = (255, 0, 0)  # RGB
    
    # Page layout (mm)
    page_width_mm: float = 210
    page_height_mm: float = 297
    margin_left_mm: float = 10
    margin_right_mm: float = 10
    margin_top_mm: float = 10
    margin_bottom_mm: float = 10
    
    label_width_mm: float = 25
    label_height_mm: float = 50
    cols: int = 6
    rows: int = 4
    
    title_height_mm: float = 25
    title_left_mm: float = 10
    title_right_mm: float = 10
    title_top_mm: float = 10
    
    footer_height_mm: float = 10
    footer_left_mm: float = 10
    footer_right_mm: float = 10
    footer_bottom_mm: float = 10
    
    label_gap_mm: float = 4
    label_area_margin_top_mm: float = 5
    label_area_margin_bottom_mm: float = 5
    
    # Colors (RGB 0-1)
    title_zone_color: tuple = (0, 0, 0)
    title_chamber_color: tuple = (0, 0, 0)
    title_techroom_color: tuple = (0, 0, 0)
    piece_color: tuple = (0, 0.156, 0.549)  # #00288c
    
    # Fonts
    font_bold: str = "SourceCodePro-Bold"
    font_medium: str = "SourceCodePro-Medium"
    
    # Label text settings
    piece_font_size: int = 7
    equip_font_size: int = 7
    title_font_size_zone: int = 16
    title_font_size_chamber: int = 14
    title_font_size_techroom: int = 12
    footer_font_size: int = 9
    max_text_lines: int = 2

# Default configuration instance
config : Config = Config()