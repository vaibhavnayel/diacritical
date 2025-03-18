"""
Database operations module for the Diacritical application.
Handles CRUD operations for diacritic mappings.
"""

import logging
from database import db, DiacriticMapping, Feedback

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
BATCH_SIZE = 1000

# Mapping operations
def load_mappings_from_db() -> dict[str, str]:
    """Load mappings from the database"""
    mappings = {}
    try:
        db_mappings = DiacriticMapping.query.all()
        for mapping in db_mappings:
            mappings[mapping.plain_text] = mapping.diacritic_text
        logger.info(f"Loaded {len(mappings)} mappings from database")
    except Exception as e:
        logger.error(f"Error loading mappings from database: {e}")
    return mappings

def save_mapping_to_db(plain_text: str, diacritic_text: str) -> DiacriticMapping:
    """Save a new mapping to the database"""
    try:
        mapping = DiacriticMapping(
            plain_text=plain_text.lower(), 
            diacritic_text=diacritic_text.lower()
        )
        db.session.add(mapping)
        db.session.commit()
        logger.info(f"Saved mapping: {plain_text.lower()} -> {diacritic_text.lower()}")
        return mapping
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error saving mapping to database: {e}")
        raise

def update_mapping_in_db(mapping_id: int, plain_text: str, diacritic_text: str) -> DiacriticMapping:
    """Update an existing mapping in the database"""
    try:
        mapping = DiacriticMapping.query.get(mapping_id)
        if mapping:
            mapping.plain_text = plain_text.lower()
            mapping.diacritic_text = diacritic_text.lower()
            db.session.commit()
            logger.info(f"Updated mapping {mapping_id}: {plain_text.lower()} -> {diacritic_text.lower()}")
        return mapping
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating mapping in database: {e}")
        raise

def delete_mapping_from_db(mapping_id: int) -> bool:
    """Delete a mapping from the database"""
    try:
        mapping = DiacriticMapping.query.get(mapping_id)
        if mapping:
            db.session.delete(mapping)
            db.session.commit()
            logger.info(f"Deleted mapping {mapping_id}")
            return True
        return False
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting mapping from database: {e}")
        raise

def batch_delete_mappings_from_db(ids: list[int]) -> int:
    """Delete multiple mappings from the database
    
    Args:
        ids: List of mapping IDs to delete
        
    Returns:
        Number of mappings deleted
    """
    try:
        mappings = DiacriticMapping.query.filter(DiacriticMapping.id.in_(ids)).all()
        deleted_count = len(mappings)
        
        for mapping in mappings:
            db.session.delete(mapping)
        
        db.session.commit()
        logger.info(f"Batch deleted {deleted_count} mappings")
        return deleted_count
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error batch deleting mappings: {e}")
        raise

# File processing operations
def process_uploaded_mappings_file(file_path: str, mode: str = 'update') -> dict[str, int]:
    """Process an uploaded mappings file
    
    Args:
        file_path: Path to the uploaded file
        mode: 'update' to add/update mappings, 'overwrite' to replace all mappings
        
    Returns:
        Dictionary with statistics about the operation
    """
    from diacritics import load_mappings_from_file
    
    try:
        uploaded_mappings = load_mappings_from_file(file_path)
        logger.info(f"Loaded {len(uploaded_mappings)} mappings from uploaded file")
        
        stats = {
            'total': len(uploaded_mappings),
            'added': 0,
            'updated': 0,
            'unchanged': 0
        }
        
        if mode == 'overwrite':
            stats = _process_overwrite_mode(uploaded_mappings)
        else:
            stats = _process_update_mode(uploaded_mappings)
        
        return stats
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error processing uploaded mappings file: {e}")
        raise

def _process_overwrite_mode(uploaded_mappings: dict[str, str]) -> dict[str, int]:
    """Process uploaded mappings in overwrite mode"""
    try:
        # Delete all existing mappings
        DiacriticMapping.query.delete()
        db.session.commit()
        logger.info("Deleted all existing mappings for overwrite mode")
        
        # Add all mappings from the uploaded file
        mappings_to_add = []
        for plain_text, diacritic_text in uploaded_mappings.items():
            mappings_to_add.append({
                'plain_text': plain_text.lower(),
                'diacritic_text': diacritic_text.lower()
            })
        
        # Use bulk insert for better performance
        for i in range(0, len(mappings_to_add), BATCH_SIZE):
            batch = mappings_to_add[i:i+BATCH_SIZE]
            db.session.bulk_insert_mappings(DiacriticMapping, batch)
            db.session.commit()
        
        return {
            'total': len(uploaded_mappings),
            'added': len(uploaded_mappings),
            'updated': 0,
            'unchanged': 0
        }
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in overwrite mode: {e}")
        raise

def _process_update_mode(uploaded_mappings: dict[str, str]) -> dict[str, int]:
    """Process uploaded mappings in update mode"""
    try:
        stats = {
            'total': len(uploaded_mappings),
            'added': 0,
            'updated': 0,
            'unchanged': 0
        }
        
        # Get existing mappings
        existing_mappings = {}
        for mapping in DiacriticMapping.query.all():
            existing_mappings[mapping.plain_text] = {
                'id': mapping.id,
                'diacritic_text': mapping.diacritic_text
            }
        
        # Process each mapping from the uploaded file
        for plain_text, diacritic_text in uploaded_mappings.items():
            plain_text = plain_text.lower()
            diacritic_text = diacritic_text.lower()
            
            if plain_text in existing_mappings:
                if existing_mappings[plain_text]['diacritic_text'] != diacritic_text:
                    # Update the existing mapping
                    mapping = DiacriticMapping.query.get(existing_mappings[plain_text]['id'])
                    mapping.diacritic_text = diacritic_text
                    stats['updated'] += 1
                else:
                    stats['unchanged'] += 1
            else:
                # Add new mapping
                mapping = DiacriticMapping(plain_text=plain_text, diacritic_text=diacritic_text)
                db.session.add(mapping)
                stats['added'] += 1
        
        db.session.commit()
        logger.info(f"Update mode: Added {stats['added']}, updated {stats['updated']}, unchanged {stats['unchanged']}")
        return stats
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in update mode: {e}")
        raise

def migrate_mappings_from_file_to_db(file_path: str) -> int:
    """Migrate mappings from a text file to the database using bulk insert for better performance"""
    from diacritics import load_mappings_from_file
    
    try:
        # Load mappings from the file
        mappings = load_mappings_from_file(file_path)
        logger.info(f"Loaded {len(mappings)} mappings from file, preparing for migration")
        
        # Get existing mappings to avoid duplicates
        existing_mappings = {
            mapping[0] for mapping in 
            DiacriticMapping.query.with_entities(DiacriticMapping.plain_text).all()
        }
        
        # Prepare mappings for bulk insert
        mappings_to_add = []
        count = 0
        
        for plain_text, diacritic_text in mappings.items():
            if plain_text not in existing_mappings:
                mappings_to_add.append({
                    'plain_text': plain_text,
                    'diacritic_text': diacritic_text
                })
                count += 1
        
        # Use bulk insert if there are mappings to add
        if mappings_to_add:
            # Process in batches for better performance
            for i in range(0, len(mappings_to_add), BATCH_SIZE):
                batch = mappings_to_add[i:i+BATCH_SIZE]
                db.session.bulk_insert_mappings(DiacriticMapping, batch)
                db.session.commit()
                logger.info(f"Inserted batch of {len(batch)} mappings")
        
        logger.info(f"Migrated {count} mappings from file {file_path} to database")
        return count
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error migrating mappings from file to database: {e}")
        raise

# Feedback operations
def save_feedback_to_db(message: str, email: str = None) -> Feedback:
    """Save a new feedback entry to the database"""
    try:
        feedback = Feedback(message=message, email=email)
        db.session.add(feedback)
        db.session.commit()
        logger.info(f"Saved feedback: {message[:30]}...")
        return feedback
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error saving feedback to database: {e}")
        raise

def get_all_feedback() -> list[Feedback]:
    """Get all feedback entries from the database, ordered by most recent first"""
    try:
        feedback_entries = Feedback.query.order_by(Feedback.created_at.desc()).all()
        logger.info(f"Retrieved {len(feedback_entries)} feedback entries")
        return feedback_entries
    except Exception as e:
        logger.error(f"Error retrieving feedback from database: {e}")
        return []

def delete_feedback_from_db(feedback_id: int) -> bool:
    """Delete a feedback entry from the database"""
    try:
        feedback = Feedback.query.get(feedback_id)
        if feedback:
            db.session.delete(feedback)
            db.session.commit()
            logger.info(f"Deleted feedback {feedback_id}")
            return True
        return False
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting feedback from database: {e}")
        return False 