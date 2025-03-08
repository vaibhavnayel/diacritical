import docx
import re
import unicodedata
from models import DiacriticMapping, db
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def read_docx(path: str) -> str:
    doc = docx.Document(path)
    text = ""
    for paragraph in doc.paragraphs:
        text += paragraph.text + "\n"
    return text

def generate_tokens(text: str) -> list[str]:
    tokens = re.split(r'([^\w\u0300-\u036f\s]|\s+)', text)
    tokens = [t for t in tokens if t]
    return tokens

def join_tokens(tokens: list[str]) -> str:
    return ''.join(tokens)

def remove_diacritics(word: str) -> str:
    normalized = unicodedata.normalize('NFKD', word)
    return ''.join(c for c in normalized if not unicodedata.combining(c))

def add_diacritics(word: str, mappings: dict[str, str]) -> str:
    word_with_diacritics = mappings.get(word.lower(), word)

    if word.isupper():
        return word_with_diacritics.upper()
    elif word.islower():
        return word_with_diacritics.lower()
    elif word[0].isupper():
        return word_with_diacritics[0].upper() + word_with_diacritics[1:]
    else:
        raise ValueError(f"Cannot add diacritics to word: {word} with mapping: {word_with_diacritics}")
    
def make_mappings(tokens: list[str]) -> dict[str, str]:
    mappings = {}
    for token in tokens:
        token_without_diacritics = remove_diacritics(token)
        if (token != token_without_diacritics) and not token.isspace():
            mappings[token_without_diacritics.lower()] = token.lower()
    return mappings

def reconstruct_tokens(tokens: list[str], mappings: dict[str, str]) -> list[str]:
    reconstructed_tokens = []
    for token in tokens:
        token_without_diacritics = remove_diacritics(token)
        if token_without_diacritics.lower() not in mappings:
            reconstructed_tokens.append(token_without_diacritics)
        else:
            reconstructed_tokens.append(add_diacritics(token_without_diacritics, mappings))
    return reconstructed_tokens

def verify(text: str, reconstructed_text: str, tokens: list[str], reconstructed_tokens: list[str]) -> bool:
    if text != reconstructed_text:
        if len(tokens) != len(reconstructed_tokens):
            print(f"tokens: {len(tokens)}, reconstructed_tokens: {len(reconstructed_tokens)}")

        if len(text) != len(reconstructed_text):
            print(f"text: {len(text)}, reconstructed_text: {len(reconstructed_text)}")

        for orig, recon in zip(tokens, reconstructed_tokens):
            if orig != recon:
                print(f"original: {orig}, reconstructed: {recon}")
        return False
    else:
        return True

def test_txt_file(path: str) -> bool:
    text = open(path, "r").read()
    tokens = generate_tokens(text)
    mappings = make_mappings(tokens)
    reconstructed_tokens = reconstruct_tokens(tokens, mappings)
    reconstructed_text = join_tokens(reconstructed_tokens)
    return verify(text, reconstructed_text, tokens, reconstructed_tokens)

def load_mappings_from_file(path: str) -> dict[str, str]:
    """Legacy function to load mappings from a text file"""
    mappings = {}
    try:
        with open(path, "r") as f:
            for line in f:
                if ',' in line:
                    k, v = line.strip().split(",", 1)  # Split on first comma only
                    mappings[k] = v
        logger.info(f"Loaded {len(mappings)} mappings from file {path}")
    except Exception as e:
        logger.error(f"Error loading mappings from file {path}: {e}")
    return mappings

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
        mapping = DiacriticMapping(plain_text=plain_text, diacritic_text=diacritic_text)
        db.session.add(mapping)
        db.session.commit()
        logger.info(f"Saved mapping: {plain_text} -> {diacritic_text}")
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
            mapping.plain_text = plain_text
            mapping.diacritic_text = diacritic_text
            db.session.commit()
            logger.info(f"Updated mapping {mapping_id}: {plain_text} -> {diacritic_text}")
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
        # Get the mappings to delete
        mappings = DiacriticMapping.query.filter(DiacriticMapping.id.in_(ids)).all()
        deleted_count = len(mappings)
        
        # Delete the mappings
        for mapping in mappings:
            db.session.delete(mapping)
        
        db.session.commit()
        logger.info(f"Batch deleted {deleted_count} mappings with IDs: {ids}")
        return deleted_count
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error batch deleting mappings: {e}")
        raise

def migrate_mappings_from_file_to_db(file_path: str):
    """Migrate mappings from a text file to the database using bulk insert for better performance"""
    try:
        mappings = load_mappings_from_file(file_path)
        logger.info(f"Loaded {len(mappings)} mappings from file, preparing for migration")
        
        # Get existing mappings to avoid duplicates
        existing_mappings = set()
        for mapping in DiacriticMapping.query.with_entities(DiacriticMapping.plain_text).all():
            existing_mappings.add(mapping[0])
        
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
            # Process in batches of 1000 for better performance
            batch_size = 1000
            for i in range(0, len(mappings_to_add), batch_size):
                batch = mappings_to_add[i:i+batch_size]
                db.session.bulk_insert_mappings(DiacriticMapping, batch)
                db.session.commit()
                logger.info(f"Inserted batch of {len(batch)} mappings")
        
        logger.info(f"Migrated {count} mappings from file {file_path} to database")
        return count
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error migrating mappings from file to database: {e}")
        raise

# For backward compatibility
def load_mappings(path: str = None) -> dict[str, str]:
    """Load mappings from the database or file if specified"""
    if path:
        return load_mappings_from_file(path)
    else:
        return load_mappings_from_db()

def process_uploaded_mappings_file(file_path: str, mode: str = 'update') -> dict:
    """Process an uploaded mappings file
    
    Args:
        file_path: Path to the uploaded file
        mode: 'update' to add/update mappings, 'overwrite' to replace all mappings
        
    Returns:
        Dictionary with statistics about the operation
    """
    try:
        # Load mappings from the uploaded file
        uploaded_mappings = load_mappings_from_file(file_path)
        logger.info(f"Loaded {len(uploaded_mappings)} mappings from uploaded file")
        
        stats = {
            'total': len(uploaded_mappings),
            'added': 0,
            'updated': 0,
            'unchanged': 0
        }
        
        # If overwrite mode, delete all existing mappings
        if mode == 'overwrite':
            try:
                # Delete all existing mappings
                DiacriticMapping.query.delete()
                db.session.commit()
                logger.info("Deleted all existing mappings for overwrite mode")
                
                # Add all mappings from the uploaded file
                mappings_to_add = []
                for plain_text, diacritic_text in uploaded_mappings.items():
                    mappings_to_add.append({
                        'plain_text': plain_text,
                        'diacritic_text': diacritic_text
                    })
                
                # Use bulk insert for better performance
                batch_size = 1000
                for i in range(0, len(mappings_to_add), batch_size):
                    batch = mappings_to_add[i:i+batch_size]
                    db.session.bulk_insert_mappings(DiacriticMapping, batch)
                    db.session.commit()
                
                stats['added'] = len(uploaded_mappings)
                logger.info(f"Added {stats['added']} mappings in overwrite mode")
                
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error in overwrite mode: {e}")
                raise
                
        # Update mode - add new mappings and update existing ones
        else:
            # Get existing mappings
            existing_mappings = {}
            for mapping in DiacriticMapping.query.all():
                existing_mappings[mapping.plain_text] = {
                    'id': mapping.id,
                    'diacritic_text': mapping.diacritic_text
                }
            
            # Process each mapping from the uploaded file
            for plain_text, diacritic_text in uploaded_mappings.items():
                if plain_text in existing_mappings:
                    # Check if the mapping has changed
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
        logger.error(f"Error processing uploaded mappings file: {e}")
        raise