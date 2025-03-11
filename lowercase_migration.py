"""
Database migration script to convert all mappings to lowercase.
This script will:
1. Find all mappings with uppercase characters
2. Convert them to lowercase
3. Handle potential duplicates by merging them
4. Update the database with the lowercase mappings

Usage:
    python lowercase_migration.py

Note: This script should be run with the application's virtual environment activated.
"""

import os
import sys
import logging
from datetime import datetime
from flask import Flask
from sqlalchemy import text, bindparam, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
import time

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('lowercase_migration.log')
    ]
)
logger = logging.getLogger(__name__)

# Create a minimal Flask app for database context
app = Flask(__name__)

# Database configuration from environment
database_url = os.environ.get('DATABASE_URL')
# Fix for Render's postgres:// vs postgresql:// issue
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Import database models
from database import init_db, db, DiacriticMapping

def run_migration():
    """Run the migration to convert all mappings to lowercase"""
    start_time = datetime.now()
    logger.info(f"Starting lowercase migration at {start_time}")
    
    # Initialize database
    init_db(app)
    
    with app.app_context():
        # Step 1: Find all mappings with uppercase characters using SQL for better performance
        logger.info("Finding mappings with uppercase characters...")
        
        # Use raw SQL for better performance on large datasets
        uppercase_query = text("""
            SELECT id, plain_text, diacritic_text, updated_at
            FROM diacritic_mappings
            WHERE plain_text <> LOWER(plain_text) OR diacritic_text <> LOWER(diacritic_text)
        """)
        
        result = db.session.execute(uppercase_query)
        uppercase_mappings = [
            {
                'id': row[0],
                'plain_text': row[1],
                'diacritic_text': row[2],
                'updated_at': row[3],
                'plain_lower': row[1].lower(),
                'diacritic_lower': row[2].lower()
            }
            for row in result
        ]
        
        uppercase_count = len(uppercase_mappings)
        logger.info(f"Found {uppercase_count} mappings with uppercase characters")
        
        if uppercase_count == 0:
            logger.info("No uppercase mappings found. Migration not needed.")
            return
        
        # Step 2: Get all existing lowercase mappings that might conflict
        lowercase_plain_texts = list(set(m['plain_lower'] for m in uppercase_mappings))
        
        # Use batching for large datasets
        batch_size = 1000
        existing_lowercase = {}
        
        for i in range(0, len(lowercase_plain_texts), batch_size):
            batch = lowercase_plain_texts[i:i+batch_size]
            query = text("""
                SELECT id, plain_text, diacritic_text, updated_at
                FROM diacritic_mappings
                WHERE plain_text = ANY(:plain_texts)
            """)
            result = db.session.execute(query, {'plain_texts': batch})
            
            for row in result:
                existing_lowercase[row[1]] = {
                    'id': row[0],
                    'diacritic_text': row[2],
                    'updated_at': row[3]
                }
        
        logger.info(f"Found {len(existing_lowercase)} existing lowercase mappings that might conflict")
        
        # Step 3: Group uppercase mappings by their lowercase version to handle duplicates
        lowercase_groups = {}
        
        for mapping in uppercase_mappings:
            plain_lower = mapping['plain_lower']
            
            if plain_lower not in lowercase_groups:
                lowercase_groups[plain_lower] = []
                
            lowercase_groups[plain_lower].append(mapping)
        
        # Step 4: Process each group to determine what to keep and what to delete
        to_update = []  # Mappings to update to lowercase
        to_delete = []  # Mappings to delete (duplicates)
        
        for plain_lower, group in lowercase_groups.items():
            # Sort by updated_at descending to keep the most recent
            group.sort(key=lambda x: x['updated_at'], reverse=True)
            
            if plain_lower in existing_lowercase:
                # Case 1: There's already a lowercase version
                existing = existing_lowercase[plain_lower]
                
                # If the newest uppercase mapping is newer than the existing lowercase
                if group[0]['updated_at'] > existing['updated_at']:
                    # Update the existing lowercase with the newer diacritic text
                    to_update.append({
                        'id': existing['id'],
                        'diacritic_text': group[0]['diacritic_lower']
                    })
                
                # Delete all uppercase versions
                for mapping in group:
                    to_delete.append(mapping['id'])
            else:
                # Case 2: No existing lowercase version
                # Keep the most recent uppercase and convert it to lowercase
                to_update.append({
                    'id': group[0]['id'],
                    'plain_text': plain_lower,
                    'diacritic_text': group[0]['diacritic_lower']
                })
                
                # Delete the rest
                for mapping in group[1:]:
                    to_delete.append(mapping['id'])
        
        # Step 5: Execute the updates and deletes in batches
        updated_count = 0
        deleted_count = 0
        error_count = 0
        
        try:
            # Process updates in batches
            logger.info(f"Updating {len(to_update)} mappings to lowercase...")
            
            for i in range(0, len(to_update), batch_size):
                batch = to_update[i:i+batch_size]
                
                for item in batch:
                    try:
                        if 'plain_text' in item:
                            # Full update (plain_text and diacritic_text)
                            update_query = text("""
                                UPDATE diacritic_mappings
                                SET plain_text = :plain_text, diacritic_text = :diacritic_text, updated_at = NOW()
                                WHERE id = :id
                            """)
                            db.session.execute(update_query, item)
                        else:
                            # Just update diacritic_text
                            update_query = text("""
                                UPDATE diacritic_mappings
                                SET diacritic_text = :diacritic_text, updated_at = NOW()
                                WHERE id = :id
                            """)
                            db.session.execute(update_query, item)
                        
                        updated_count += 1
                    except Exception as e:
                        logger.error(f"Error updating mapping {item['id']}: {str(e)}")
                        error_count += 1
                
                db.session.commit()
                logger.info(f"Updated batch of {len(batch)} mappings")
            
            # Process deletes in batches
            logger.info(f"Deleting {len(to_delete)} duplicate mappings...")
            
            for i in range(0, len(to_delete), batch_size):
                batch = to_delete[i:i+batch_size]
                
                delete_query = text("""
                    DELETE FROM diacritic_mappings
                    WHERE id = ANY(:ids)
                """)
                
                try:
                    db.session.execute(delete_query, {'ids': batch})
                    deleted_count += len(batch)
                    db.session.commit()
                    logger.info(f"Deleted batch of {len(batch)} mappings")
                except Exception as e:
                    db.session.rollback()
                    logger.error(f"Error deleting batch: {str(e)}")
                    
                    # Try one by one if batch delete fails
                    for id in batch:
                        try:
                            mapping = DiacriticMapping.query.get(id)
                            if mapping:
                                db.session.delete(mapping)
                                db.session.commit()
                                deleted_count += 1
                        except Exception as inner_e:
                            db.session.rollback()
                            logger.error(f"Error deleting mapping {id}: {str(inner_e)}")
                            error_count += 1
            
            # Final step: Check for any remaining uppercase mappings and convert them
            logger.info("Checking for any remaining uppercase mappings...")
            
            remaining_query = text("""
                SELECT id, plain_text, diacritic_text
                FROM diacritic_mappings
                WHERE plain_text <> LOWER(plain_text) OR diacritic_text <> LOWER(diacritic_text)
            """)
            
            result = db.session.execute(remaining_query)
            remaining = [{'id': row[0], 'plain_text': row[1], 'diacritic_text': row[2]} for row in result]
            
            if remaining:
                logger.info(f"Found {len(remaining)} remaining uppercase mappings, converting them...")
                
                for mapping in remaining:
                    try:
                        update_query = text("""
                            UPDATE diacritic_mappings
                            SET plain_text = LOWER(plain_text), diacritic_text = LOWER(diacritic_text), updated_at = NOW()
                            WHERE id = :id
                        """)
                        
                        db.session.execute(update_query, {'id': mapping['id']})
                        db.session.commit()
                        updated_count += 1
                    except Exception as e:
                        db.session.rollback()
                        logger.error(f"Error updating remaining mapping {mapping['id']}: {str(e)}")
                        error_count += 1
            
        except Exception as e:
            logger.error(f"Migration failed: {str(e)}")
            return
        
        # Log summary
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info(f"Migration completed in {duration:.2f} seconds")
        logger.info(f"Summary: {updated_count} mappings updated, {deleted_count} duplicates deleted, {error_count} errors")
        
        # Verify all mappings are now lowercase
        final_check_query = text("""
            SELECT COUNT(*)
            FROM diacritic_mappings
            WHERE plain_text <> LOWER(plain_text) OR diacritic_text <> LOWER(diacritic_text)
        """)
        
        result = db.session.execute(final_check_query)
        final_check = result.scalar()
        
        if final_check > 0:
            logger.warning(f"There are still {final_check} mappings with uppercase characters")
        else:
            logger.info("All mappings are now lowercase")

if __name__ == "__main__":
    run_migration() 