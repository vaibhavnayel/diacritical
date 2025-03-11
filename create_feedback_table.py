"""
Script to create the feedback table in the database.
"""

from app import app
from database import db, Feedback

def create_feedback_table():
    """Create the feedback table in the database."""
    with app.app_context():
        # Create the feedback table
        db.create_all()
        print("Feedback table created successfully.")

if __name__ == "__main__":
    create_feedback_table() 