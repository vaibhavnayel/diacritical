"""
Database module for the Diacritical application.
Handles database models and connections.
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize SQLAlchemy
db = SQLAlchemy()

class DiacriticMapping(db.Model):
    """
    Database model for diacritic mappings.
    Maps plain text to text with diacritics.
    """
    __tablename__ = 'diacritic_mappings'
    
    id = db.Column(db.Integer, primary_key=True)
    plain_text = db.Column(db.String(255), unique=True, nullable=False)
    diacritic_text = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<DiacriticMapping {self.plain_text} -> {self.diacritic_text}>"
    
    def to_dict(self):
        """Convert the model instance to a dictionary"""
        return {
            'id': self.id,
            'plain_text': self.plain_text,
            'diacritic_text': self.diacritic_text,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Feedback(db.Model):
    """
    Database model for user feedback.
    """
    __tablename__ = 'feedback'
    
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.Text, nullable=False)
    email = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Feedback {self.id}: {self.message[:30]}...>"
    
    def to_dict(self):
        """Convert the model instance to a dictionary"""
        return {
            'id': self.id,
            'message': self.message,
            'email': self.email,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

def init_db(app):
    """Initialize the database with the Flask app"""
    db.init_app(app)
    
    # Create tables if they don't exist
    with app.app_context():
        import sqlalchemy as sa
        inspector = sa.inspect(db.engine)
        if not inspector.has_table('diacritic_mappings') or not inspector.has_table('feedback'):
            db.create_all()
            logger.info("Created database tables")
        else:
            logger.info("Database tables already exist")
            
def get_db():
    """Get the database instance"""
    return db 