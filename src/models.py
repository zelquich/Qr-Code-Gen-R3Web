from __future__ import annotations
import json
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class EquipmentItem:
    name: str
    Id: int
    parent: Optional[Lieu] = None
    lieu_path: str = ""
    id_path: str = ""
    qr_file_path: str = ""

    BASE_URL = "https://fiber-main.synoptic-broadcast.com/R3WEB_USOPEN/R3Web_EN.dll/RqPDFDirect"

    @property
    def pdf_url(self) -> str:
        """Generate the PDF request URL for this equipment item."""
        query = {
            "infosession": {"envlog": "R3WEB_USOPEN"},
            "param": {"categ": "E", "numero": self.Id}
        }
        json_query = json.dumps(query, separators=(',', ':'))  # compact
        return f"{self.BASE_URL}?Requete={json_query}"
    
@dataclass
class Lieu:
    name: str
    Id: int
    categorie: str          # "R" for ensemble, "G" for sous‑ensemble
    type_name: str
    parent: Optional[Lieu] = None
    dir_path: str = ""
    lieu_path: str = ""
    id_path: str = ""

    # Children collections
    children_lieux: List[Lieu] = field(default_factory=list)
    equipment_items: List[EquipmentItem] = field(default_factory=list)

    BASE_URL = "https://fiber-main.synoptic-broadcast.com/R3WEB_USOPEN/R3Web_EN.dll/RqPDFDirectRG"
    VALID_CATEGORIES_FOR_PDF = {"R", "G"}  # Only these categories have PDF reports

    @property
    def pdf_url(self) -> str:
        """Return the PDF request URL if this lieu has one. 
        Raises ValueError if the category is not valid for PDF generation.
        """
        if self.categorie.upper() not in self.VALID_CATEGORIES_FOR_PDF:
            raise ValueError(f"No PDF for categorie '{self.categorie}'")

        query = {
            "infosession": {"envlog": "R3WEB_USOPEN"},
            "param": {"numerolieu": self.Id}
        }
        json_query = json.dumps(query, separators=(",", ":"))
        return f"{self.BASE_URL}?Requete={json_query}"