from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_bootstrap import Bootstrap4
from functools import wraps
import os
from diacritics import *

# Load mappings at startup
try:
    # First try to load from the mappings.txt file
    mappings = load_mappings("mappings.txt")
except Exception as e:
    print(f"Warning: Could not load from mappings.txt: {e}")
    try:
        # Try to load from all_mappings.txt as fallback
        mappings = load_mappings("all_mappings.txt")
    except Exception as e:
        print(f"Error loading mappings: {e}")
        mappings = {}

app = Flask(__name__)
bootstrap = Bootstrap4(app)

# Get configuration from environment variables
app.secret_key = os.environ.get('FLASK_SECRET_KEY', '696969696969')
USERNAME = os.environ.get('APP_USERNAME', 'chitrapur')
PASSWORD = os.environ.get('APP_PASSWORD', 'NCC1701')

# Login decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

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
        translated = main(text)
        return jsonify({'result': translated})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def main(text):
    tokens = generate_tokens(text)
    translated_tokens = reconstruct_tokens(tokens, mappings)
    translated_text = join_tokens(translated_tokens)
    return translated_text

if __name__ == '__main__':
    app.run(debug=True)
