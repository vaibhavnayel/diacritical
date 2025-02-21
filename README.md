# Diacritical Translator Web App

A web application that adds diacritical marks to text based on predefined mappings.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set environment variables (in production):
```bash
export FLASK_SECRET_KEY='your-secret-key'
export APP_USERNAME='your-username'
export APP_PASSWORD='your-password'
```

3. Run the application:
```bash
python app.py
```

## Deployment on Render

1. Create a new Web Service on Render
2. Connect your GitHub repository
3. Configure the following:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`
   - Python Version: 3.9 or later

4. Add the following environment variables in Render:
   - `FLASK_SECRET_KEY`
   - `APP_USERNAME`
   - `APP_PASSWORD`

## Usage

1. Access the application through your browser
2. Log in with your credentials
3. Paste text in the input box
4. Click "Add Diacritics" to process the text
5. Use the copy button to copy the processed text

## Security Notes

- Change the default username and password
- Use a strong secret key
- Keep your mappings file secure 