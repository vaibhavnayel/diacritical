#!/usr/bin/env python
"""
Script to run the lowercase migration from the Flask application.
This is a convenience wrapper around lowercase_migration.py.

Usage:
    python run_lowercase_migration.py
"""

import os
import sys
import logging
from flask import Flask
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def main():
    """Run the lowercase migration"""
    try:
        # Import the migration module
        from lowercase_migration import run_migration
        
        # Run the migration
        logger.info("Starting lowercase migration...")
        run_migration()
        logger.info("Migration completed.")
        
    except ImportError:
        logger.error("Could not import lowercase_migration module. Make sure lowercase_migration.py is in the current directory.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 