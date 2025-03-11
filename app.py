"""
Main application module for the Diacritical application.
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_bootstrap import Bootstrap
from functools import wraps
import os
import threading
import time
import tempfile
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Import modules
from database import init_db, DiacriticMapping
from diacritics import translate_text, load_mappings_from_file
from db_operations import (
    load_mappings_from_db, save_mapping_to_db, update_mapping_in_db,
    delete_mapping_from_db, batch_delete_mappings_from_db,
    process_uploaded_mappings_file, migrate_mappings_from_file_to_db
)

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
bootstrap = Bootstrap(app)

# Database configuration
database_url = os.environ.get('DATABASE_URL')
# Fix for Render's postgres:// vs postgresql:// issue
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
init_db(app)

# Get configuration from environment variables
app.secret_key = os.environ.get('FLASK_SECRET_KEY')
USERNAME = os.environ.get('APP_USERNAME')
PASSWORD = os.environ.get('APP_PASSWORD')

# Migration status tracking
migration_status = {
    'status': 'idle',
    'message': '',
    'count': 0,
    'total': 0,
    'start_time': None
}

# Add CLI commands
@app.cli.command("lowercase-migration")
def lowercase_migration_command():
    """Convert all mappings in the database to lowercase."""
    from lowercase_migration import run_migration
    print("Starting lowercase migration...")
    run_migration()
    print("Migration completed.")

# Login decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/', methods=['GET'])
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['username'] == USERNAME and request.form['password'] == PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('translator'))
        else:
            flash('Invalid credentials')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/translator', methods=['GET'])
@login_required
def translator():
    return render_template('translator.html')

@app.route('/translate', methods=['POST'])
@login_required
def translate():
    text = request.json.get('text', '')
    if not text:
        return jsonify({'error': 'No text provided'}), 400
    
    try:
        # Get mappings from database
        mappings = load_mappings_from_db()
        # Translate text
        translated = translate_text(text, mappings)
        return jsonify({'result': translated})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/mappings', methods=['GET'])
@login_required
def mappings_page():
    return render_template('mappings.html')

# API endpoints for mappings
@app.route('/api/mappings', methods=['GET'])
@login_required
def get_mappings():
    mappings = DiacriticMapping.query.all()
    return jsonify([mapping.to_dict() for mapping in mappings])

@app.route('/api/mappings', methods=['POST'])
@login_required
def add_mapping():
    data = request.json
    plain_text = data.get('plain_text', '').strip().lower()
    diacritic_text = data.get('diacritic_text', '').strip().lower()
    
    if not plain_text or not diacritic_text:
        return jsonify({'error': 'Both plain text and diacritic text are required'}), 400
    
    # Check if mapping already exists
    existing = DiacriticMapping.query.filter_by(plain_text=plain_text).first()
    if existing:
        return jsonify({'error': f'Mapping for "{plain_text}" already exists'}), 400
    
    try:
        mapping = save_mapping_to_db(plain_text, diacritic_text)
        return jsonify(mapping.to_dict()), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/mappings/<int:mapping_id>', methods=['PUT'])
@login_required
def update_mapping(mapping_id):
    data = request.json
    plain_text = data.get('plain_text', '').strip().lower()
    diacritic_text = data.get('diacritic_text', '').strip().lower()
    
    if not plain_text or not diacritic_text:
        return jsonify({'error': 'Both plain text and diacritic text are required'}), 400
    
    # Check if the new plain_text already exists for another mapping
    existing = DiacriticMapping.query.filter_by(plain_text=plain_text).first()
    if existing and existing.id != mapping_id:
        return jsonify({'error': f'Mapping for "{plain_text}" already exists'}), 400
    
    try:
        mapping = update_mapping_in_db(mapping_id, plain_text, diacritic_text)
        if mapping:
            return jsonify(mapping.to_dict())
        return jsonify({'error': 'Mapping not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/mappings/<int:mapping_id>', methods=['DELETE'])
@login_required
def delete_mapping(mapping_id):
    try:
        success = delete_mapping_from_db(mapping_id)
        if success:
            return jsonify({'success': True})
        return jsonify({'error': 'Mapping not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/mappings/batch-delete', methods=['POST'])
@login_required
def batch_delete_mappings():
    data = request.json
    ids = data.get('ids', [])
    
    if not ids:
        return jsonify({'error': 'No IDs provided'}), 400
    
    try:
        deleted_count = batch_delete_mappings_from_db(ids)
        return jsonify({'success': True, 'deleted_count': deleted_count})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/mappings/upload', methods=['POST'])
@login_required
def upload_mappings():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if not file.filename.endswith('.txt'):
        return jsonify({'error': 'Only .txt files are allowed'}), 400
    
    mode = request.form.get('mode', 'update')
    if mode not in ['update', 'overwrite']:
        return jsonify({'error': 'Invalid mode. Must be "update" or "overwrite"'}), 400
    
    try:
        # Save the uploaded file to a temporary location
        temp_dir = tempfile.gettempdir()
        filename = secure_filename(file.filename)
        file_path = os.path.join(temp_dir, filename)
        file.save(file_path)
        
        # Process the file
        stats = process_uploaded_mappings_file(file_path, mode)
        
        # Clean up the temporary file
        os.remove(file_path)
        
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Migration endpoints
def perform_migration(file_path):
    """Background task to perform migration"""
    global migration_status
    
    try:
        migration_status['status'] = 'in_progress'
        migration_status['message'] = 'Loading mappings from file...'
        migration_status['start_time'] = time.time()
        
        # Migrate mappings
        count = migrate_mappings_from_file_to_db(file_path)
        
        elapsed_time = time.time() - migration_status['start_time']
        migration_status['message'] = f'Migration completed in {elapsed_time:.2f} seconds'
        migration_status['status'] = 'completed'
        migration_status['count'] = count
        
    except Exception as e:
        migration_status['status'] = 'error'
        migration_status['message'] = f'Error: {str(e)}'

@app.route('/api/migrate', methods=['POST'])
@login_required
def migrate_mappings():
    global migration_status
    
    # Check if migration is already in progress
    if migration_status['status'] == 'in_progress':
        return jsonify({'error': 'Migration already in progress'}), 400
    
    try:
        # Reset migration status
        migration_status = {
            'status': 'starting',
            'message': 'Starting migration...',
            'count': 0,
            'total': 0,
            'start_time': time.time()
        }
        
        # Start migration in a background thread
        thread = threading.Thread(target=perform_migration, args=('mappings.txt',))
        thread.daemon = True
        thread.start()
        
        return jsonify({'success': True, 'message': 'Migration started'})
    except Exception as e:
        migration_status['status'] = 'error'
        migration_status['message'] = str(e)
        return jsonify({'error': str(e)}), 500

@app.route('/api/migrate/status', methods=['GET'])
@login_required
def get_migration_status():
    return jsonify({
        'status': migration_status['status'],
        'message': migration_status['message'],
        'count': migration_status['count'],
        'total': migration_status['total'],
        'elapsed': time.time() - migration_status['start_time'] if migration_status['start_time'] else 0
    })

@app.route('/api/mappings/download', methods=['GET'])
@login_required
def download_mappings():
    try:
        # Get all mappings from the database
        mappings = DiacriticMapping.query.order_by(DiacriticMapping.plain_text).all()
        
        # Create a string with all mappings in the format plain_text,diacritic_text
        mappings_text = ""
        for mapping in mappings:
            mappings_text += f"{mapping.plain_text},{mapping.diacritic_text}\n"
        
        # Create a response with the mappings text
        response = app.response_class(
            response=mappings_text,
            status=200,
            mimetype='text/plain'
        )
        
        # Set the Content-Disposition header to make the browser download the file
        response.headers["Content-Disposition"] = "attachment; filename=mappings.txt"
        
        return response
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Run the application
if __name__ == '__main__':
    app.run(debug=True)
