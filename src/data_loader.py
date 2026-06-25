import os
import pandas as pd
from typing import List, Dict, Optional, Callable, TypeVar
from pathlib import Path
from models import EquipmentItem, Lieu
from config import config
from utils import logger, check_file_exists, slugify

T = TypeVar("T")


def _read_csv(
    file_path: Path,
    description: str,
    builder: Callable[[pd.Series], Optional[T]],
) -> List[T]:
    """Generic CSV reader that validates, parses, and returns a list of items."""
    if not check_file_exists(file_path, description):
        logger.error(f"Cannot read {description}: {file_path}")
        return []

    logger.info(f"Reading {description}: {file_path}")
    try:
        df = pd.read_csv(file_path, delimiter=";")
        df.columns = [c.strip() for c in df.columns]
    except Exception as e:
        logger.error(f"Failed to read {description}: {e}")
        return []

    items: List[T] = []
    for _, row in df.iterrows():
        try:
            item = builder(row)
            if item is not None:
                items.append(item)
        except Exception as e:
            logger.debug(f"Skipping invalid row in {description}: {e}")

    logger.info(f"Loaded {len(items)} items from {description}")
    return items


def read_equipment_csv(file_path: Optional[Path] = None) -> List[EquipmentItem]:
    """Read equipment CSV, returning a list of EquipmentItem (no parent set yet)."""
    if file_path is None:
        file_path = config.equipement_path_csv_path

    def builder(row) -> Optional[EquipmentItem]:
        name = str(row.get("Equipment Name", "")).strip()
        if not name:
            return None
        equipment_id = int(row.get("Equipment ID", -1))
        id_path = str(row.get("ID Path", "")).strip()
        lieu_path = str(row.get("Lieu Path", "")).strip()
        return EquipmentItem(
            name=name,
            Id=equipment_id,
            lieu_path=lieu_path,
            id_path=id_path,
        )

    return _read_csv(file_path, "Equipment CSV file", builder)


def read_lieu_csv(file_path: Optional[Path] = None) -> List[Lieu]:
    """Read Lieu CSV, returning a list of Lieu (no parent nor children set yet)."""
    if file_path is None:
        file_path = config.Lieu_csv_path

    def builder(row) -> Optional[Lieu]:
        name = str(row.get("Nom", "")).strip()
        if not name:
            return None
        lieu_id = int(row.get("Id_lieu", -1))
        categorie = str(row.get("Categorie", "")).strip()
        type_name = str(row.get("Nom_Type", "")).strip()
        return Lieu(
            name=name,
            Id=lieu_id,
            categorie=categorie,
            type_name=type_name,
        )

    return _read_csv(file_path, "Lieu CSV file", builder)


def build_hierarchy(
    equipment_items: List[EquipmentItem],
    lieu_items: List[Lieu],
) -> Dict[int, str]:
    """
    Process the equipment list once to:
    - Set each equipment's parent Lieu
    - Build parent/child relationships between Lieux (children_lieux, parent)
    - Populate each Lieu's equipment_items list
    - Determine human‑readable paths (lieu_path, id_path) for every Lieu
    - Return a mapping of lieu_id → slugified directory path for QR codes

    Returns:
        Mapping of lieu_id to directory path (e.g. "qrcodes/US_Open/Intl_Compound")
    """
    lieu_by_id = {l.Id: l for l in lieu_items}
    lieu_paths: Dict[int, str] = {}          # slugified directory paths
    lieu_raw: Dict[int, tuple] = {}          # (human_lieu_path, human_id_path)

    for equip in equipment_items:
        # --- Parse id_path and find parent Lieu ---
        if not equip.id_path:
            continue

        id_parts_str = [p.strip() for p in equip.id_path.split(">")]
        try:
            id_parts = [int(p) for p in id_parts_str]
        except ValueError:
            logger.debug(f"Invalid ID path for equipment {equip.name}")
            continue

        if not id_parts:
            continue

        # The last ID in the path is the direct parent Lieu of this equipment
        parent_lieu_id = id_parts[-1]
        parent_lieu = lieu_by_id.get(parent_lieu_id)
        if parent_lieu:
            equip.parent = parent_lieu
            if equip not in parent_lieu.equipment_items:
                parent_lieu.equipment_items.append(equip)

        # --- Build Lieu hierarchy (parent/child) from consecutive IDs ---
        for i in range(len(id_parts) - 1):
            p_id = id_parts[i]
            c_id = id_parts[i + 1]
            parent = lieu_by_id.get(p_id)
            child = lieu_by_id.get(c_id)
            if parent and child:
                if child.parent is None:
                    child.parent = parent
                if child not in parent.children_lieux:
                    parent.children_lieux.append(child)

        # --- Extract directory and human paths using lieu_path ---
        if not equip.lieu_path:
            continue

        lieu_parts = [p.strip() for p in equip.lieu_path.split(">")]
        if len(lieu_parts) != len(id_parts_str):
            continue

        for i, (lieu_name, lid) in enumerate(zip(lieu_parts, id_parts)):
            if lid in lieu_paths:
                continue  # already computed
            # Slugified directory path
            dir_comp = [slugify(p) for p in lieu_parts[: i + 1]]
            full_dir = os.path.join(config.qrcode_dir, *dir_comp)
            lieu_paths[lid] = full_dir
            # Human‑readable strings
            raw_lieu = " > ".join(lieu_parts[: i + 1])
            raw_id = " > ".join(id_parts_str[: i + 1])
            lieu_raw[lid] = (raw_lieu, raw_id)

    # --- Assign paths to Lieu objects ---
    for lieu in lieu_items:
        if lieu.Id in lieu_raw:
            lieu.lieu_path, lieu.id_path = lieu_raw[lieu.Id]
            logger.debug(
                f"Set paths for Lieu {lieu.name} (ID {lieu.Id}): "
                f"'{lieu.lieu_path}' / '{lieu.id_path}'"
            )
        else:
            logger.debug(f"No hierarchy path found for Lieu {lieu.name} (ID {lieu.Id})")

    logger.info(f"Hierarchy built: \n"
                f"among {len(lieu_items)} Lieux, \n"
                f"{sum(1 for l in lieu_items if l.children_lieux)} have children Lieux, \n"
                f"{sum(1 for l in lieu_items if l.equipment_items)} have children equipment, \n"
                f"{sum(1 for l in lieu_items if l.categorie in {"R", "G"})} are ensemble or sous-ensemble, Lieux (R/G)), \n"
                f"{len(lieu_paths)} have a path.")
    return lieu_paths