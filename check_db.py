import os
from dotenv import load_dotenv
from flask import Flask
from models import db, DiacriticMapping
import sqlalchemy as sa

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

def check_database():
    """Check database connection and verify tables exist"""
    with app.app_context():
        try:
            # Check connection
            db.engine.connect()
            print("✅ Successfully connected to the database")
            
            # Check if tables exist
            inspector = sa.inspect(db.engine)
            if inspector.has_table('diacritic_mappings'):
                print("✅ Table 'diacritic_mappings' exists")
                
                # Count mappings
                count = DiacriticMapping.query.count()
                print(f"ℹ️ Database contains {count} mappings")
                
                # Show a few sample mappings
                if count > 0:
                    sample = DiacriticMapping.query.limit(5).all()
                    print("\nSample mappings:")
                    for mapping in sample:
                        print(f"  {mapping.plain_text} -> {mapping.diacritic_text}")
            else:
                print("❌ Table 'diacritic_mappings' does not exist")
                
        except Exception as e:
            print(f"❌ Database error: {e}")

if __name__ == '__main__':
    check_database() 