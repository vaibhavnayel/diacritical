from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class DiacriticMapping(db.Model):
    __tablename__ = 'diacritic_mappings'
    
    id = db.Column(db.Integer, primary_key=True)
    plain_text = db.Column(db.String(255), unique=True, nullable=False)
    diacritic_text = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<DiacriticMapping {self.plain_text} -> {self.diacritic_text}>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'plain_text': self.plain_text,
            'diacritic_text': self.diacritic_text,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        } 