import os
import time
from dotenv import load_dotenv
from flask import Flask
from models import db, DiacriticMapping
from diacritics import load_mappings_from_file

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Database configuration
database_url = os.environ.get('DATABASE_URL')
# Fix for Render's postgres:// vs postgresql:// issue
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

def migrate_mappings():
    """Migrate mappings from the text file to the database using bulk insert for better performance"""
    with app.app_context():
        start_time = time.time()
        
        # Create tables if they don't exist
        db.create_all()
        print(f"Tables created or verified in {time.time() - start_time:.2f} seconds")
        
        # Load mappings from file
        load_start = time.time()
        mappings = load_mappings_from_file('mappings.txt')
        print(f"Loaded {len(mappings)} mappings from file in {time.time() - load_start:.2f} seconds")
        
        # Get existing mappings to avoid duplicates
        query_start = time.time()
        existing_mappings = set()
        for mapping in DiacriticMapping.query.with_entities(DiacriticMapping.plain_text).all():
            existing_mappings.add(mapping[0])
        print(f"Retrieved {len(existing_mappings)} existing mappings in {time.time() - query_start:.2f} seconds")
        
        # Prepare mappings for bulk insert
        prep_start = time.time()
        mappings_to_add = []
        count = 0
        
        for plain_text, diacritic_text in mappings.items():
            if plain_text not in existing_mappings:
                mappings_to_add.append({
                    'plain_text': plain_text,
                    'diacritic_text': diacritic_text
                })
                count += 1
        
        print(f"Prepared {count} new mappings in {time.time() - prep_start:.2f} seconds")
        
        # Use bulk insert if there are mappings to add
        if mappings_to_add:
            insert_start = time.time()
            # Process in batches of 1000 for better performance
            batch_size = 1000
            for i in range(0, len(mappings_to_add), batch_size):
                batch = mappings_to_add[i:i+batch_size]
                db.session.bulk_insert_mappings(DiacriticMapping, batch)
                db.session.commit()
                print(f"Inserted batch of {len(batch)} mappings")
            
            print(f"Inserted all mappings in {time.time() - insert_start:.2f} seconds")
        
        total_time = time.time() - start_time
        print(f"Migration completed: Added {count} new mappings in {total_time:.2f} seconds")

if __name__ == '__main__':
    migrate_mappings() 