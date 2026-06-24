import os
import pandas as pd
from typing import List, Dict
from pathlib import Path
from models import EquipmentItem, Lieu
from config import config
from utils import logger, check_file_exists, slugify


def read_equipment_csv(file_path: Path | None = None) -> tuple[List[EquipmentItem], Dict[int, int]]:
    """
    Read equipment data from CSV file.
    
    Returns:
        Tuple of (equipment items, equipment_id -> parent_lieu_id mapping)
    """
    if file_path is None:
        file_path = config.equipement_path_csv_path
    
    if not check_file_exists(file_path, "Equipment CSV file"):
        logger.error(f"Cannot read Equipment CSV file: {file_path}")
        return [], {}
    
    logger.info(f"Reading Equipment CSV file: {file_path}")
    
    try:
        df = pd.read_csv(file_path, delimiter=';')
        # Clean column names
        df.columns = [c.strip() for c in df.columns]
    except Exception as e:
        logger.error(f"Failed to read Equipment CSV file: {e}")
        return [], {}
    
    items: List[EquipmentItem] = []
    equipment_to_parent_lieu: Dict[int, int] = {}
    
    for _, row in df.iterrows():
        try:
            name = str(row.get("Equipment Name", "")).strip()
            equipment_id = int(row.get("Equipment ID", -1))
            id_path = str(row.get("ID Path", "")).strip()
            lieu_path = str(row.get("Lieu Path", "")).strip()
            
            if not name:
                logger.debug("Skipping row with empty equipment name")
                continue
            
            # Extract parent lieu ID from ID Path (last ID in the path)
            parent_lieu_id = None
            if id_path:
                try:
                    parent_lieu_id = int(id_path.split(">")[-1])
                    equipment_to_parent_lieu[equipment_id] = parent_lieu_id
                except (ValueError, IndexError):
                    logger.debug(f"Could not parse ID Path for equipment {equipment_id}: {id_path}")
            
            item = EquipmentItem(
                name=name,
                Id=equipment_id,
                parent=None,  # Will be set later when linking to lieux
                lieu_path=lieu_path,
                id_path=id_path
            )
            items.append(item)
            
        except (ValueError, TypeError, KeyError) as e:
            logger.debug(f"Skipping invalid equipment row: {e}")
            continue
    
    logger.info(f"Loaded {len(items)} equipment items from CSV")
    return items, equipment_to_parent_lieu


def read_lieu_csv(file_path: Path | None = None) -> tuple[List[Lieu], Dict[int, int]]:
    """
    Read lieu data from CSV file.
    
    Returns:
        Tuple of (lieu items, lieu_id -> parent_lieu_id mapping)
    """
    if file_path is None:
        file_path = config.Lieu_csv_path
    
    if not check_file_exists(file_path, "Lieu CSV file"):
        logger.error(f"Cannot read Lieu CSV file: {file_path}")
        return [], {}
    
    logger.info(f"Reading Lieu CSV file: {file_path}")
    
    try:
        df = pd.read_csv(file_path, delimiter=';')
        # Clean column names
        df.columns = [c.strip() for c in df.columns]
    except Exception as e:
        logger.error(f"Failed to read Lieu CSV file: {e}")
        return [], {}
    
    items: List[Lieu] = []
    lieu_hierarchy: Dict[int, int] = {}
    
    for _, row in df.iterrows():
        try:
            name = str(row.get("Nom", "")).strip()
            lieu_id = int(row.get("Id_lieu", -1))
            categorie = str(row.get("Categorie", "")).strip()
            type_name = str(row.get("Nom_Type", "")).strip()
            
            if not name:
                logger.debug("Skipping row with empty lieu name")
                continue
            
            item = Lieu(
                name=name,
                Id=lieu_id,
                categorie=categorie,
                type_name=type_name,
                parent=None  # Will be set later when determining hierarchy
            )
            items.append(item)
            
        except (ValueError, TypeError, KeyError) as e:
            logger.debug(f"Skipping invalid lieu row: {e}")
            continue
    
    logger.info(f"Loaded {len(items)} lieu items from CSV")
    return items, lieu_hierarchy


def link_equipment_to_lieux(
    equipment_items: List[EquipmentItem],
    lieu_items: List[Lieu],
    equipment_to_parent_lieu: Dict[int, int]
) -> List[EquipmentItem]:
    """
    Link equipment items to their parent lieu items.
    
    Args:
        equipment_items: List of equipment items
        lieu_items: List of lieu items
        equipment_to_parent_lieu: Mapping of equipment_id to parent_lieu_id
    
    Returns:
        Updated equipment items with parent references set
    """
    # Create a mapping of lieu IDs to lieu objects
    lieu_map: Dict[int, Lieu] = {lieu.Id: lieu for lieu in lieu_items}
    
    # Link equipment to their parent lieux
    for equip in equipment_items:
        parent_lieu_id = equipment_to_parent_lieu.get(equip.Id)
        if parent_lieu_id and parent_lieu_id in lieu_map:
            equip.parent = lieu_map[parent_lieu_id]
            logger.debug(f"Linked equipment {equip.name} (ID: {equip.Id}) to lieu {equip.parent.name} (ID: {equip.parent.Id})")
        else:
            logger.debug(f"No parent lieu found for equipment {equip.name} (ID: {equip.Id})")
    
    return equipment_items


def build_lieu_hierarchy_paths(equipment_items: List[EquipmentItem]) -> Dict[int, str]:
    """
    Build directory paths for all lieux based on equipment hierarchy.
    
    Uses both lieu_path and id_path to map lieu IDs to their full directory paths.
    
    Returns:
        Mapping of lieu_id -> directory_path (e.g., "qrcodes/US Open/Int'l Compound")
    """
    lieu_paths: Dict[int, str] = {}
    
    # Extract hierarchy paths from all equipment
    for equip in equipment_items:
        if equip.lieu_path and equip.id_path:
            lieu_parts = [part.strip() for part in equip.lieu_path.split(">")]
            id_parts_str = equip.id_path.split(">")
            
            try:
                id_parts = [int(id_str.strip()) for id_str in id_parts_str]
                
                # Map each lieu ID to its full path
                if len(lieu_parts) == len(id_parts):
                    for i, (lieu_name, lieu_id) in enumerate(zip(lieu_parts, id_parts)):
                        # Build the path up to and including this lieu, slugifying each part
                        path_components = [slugify(p) for p in lieu_parts[:i+1]]
                        full_path = os.path.join(config.qrcode_dir, *path_components)
                        lieu_paths[lieu_id] = full_path
                        logger.debug(f"Mapped lieu ID {lieu_id} ({lieu_name}) to path: {full_path}")
            except (ValueError, IndexError) as e:
                logger.debug(f"Could not parse ID path for equipment {equip.name}: {e}")
    
    logger.info(f"Built directory paths for {len(lieu_paths)} lieux")
    return lieu_paths