"""
Diacritical text processing module.
Handles the core functionality of processing text with diacritics.
"""

import docx
import re
import unicodedata
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ESCAPE_SEQUENCE = "*/*"

def read_docx(path: str) -> str:
    """Read text from a DOCX file"""
    doc = docx.Document(path)
    return "\n".join(paragraph.text for paragraph in doc.paragraphs)

def generate_tokens(text: str) -> list[str]:
    """Split text into tokens"""
    tokens = re.split(r'([^\w\u0300-\u036f\s]|\s+)', text)
    return [t for t in tokens if t]

def join_tokens(tokens: list[str]) -> str:
    """Join tokens back into text"""
    return ''.join(tokens)

def remove_diacritics(word: str) -> str:
    """Remove diacritics from a word"""
    normalized = unicodedata.normalize('NFKD', word)
    return ''.join(c for c in normalized if not unicodedata.combining(c))

def match_case(word: str, mapping: str) -> str:
    """Match the case of a mapping to a word"""
    if word.isupper():
        return mapping.upper()
    elif word.islower():
        return mapping.lower()
    elif word[0].isupper():
        return mapping[0].upper() + mapping[1:]
    else:
        raise ValueError(f"Cannot add diacritics to word: {word} with mapping: {mapping}")

def process_one_to_many_mapping(word: str, mapping: str) -> str:
    """Process a one-to-many mapping with escape sequences"""
    words_with_diacritics = mapping.replace(ESCAPE_SEQUENCE, "").replace(" ", "").split(",")
    words_with_diacritics = [match_case(word, w) for w in words_with_diacritics]
    return f"{ESCAPE_SEQUENCE}{','.join(words_with_diacritics)}{ESCAPE_SEQUENCE}"

def add_diacritics(word: str, mappings: dict[str, str]) -> str:
    """Add diacritics to a word based on mappings"""
    mapping = mappings.get(word.lower(), word)
    
    if ESCAPE_SEQUENCE in mapping:
        return process_one_to_many_mapping(word, mapping)
    else:
        return match_case(word, mapping)
    
def make_mappings(tokens: list[str]) -> dict[str, str]:
    """Create mappings from tokens with diacritics"""
    mappings = {}
    for token in tokens:
        token_without_diacritics = remove_diacritics(token)
        if (token != token_without_diacritics) and not token.isspace():
            mappings[token_without_diacritics.lower()] = token.lower()
    return mappings

def reconstruct_tokens(tokens: list[str], mappings: dict[str, str]) -> list[str]:
    """Reconstruct tokens with diacritics based on mappings"""
    reconstructed_tokens = []
    for token in tokens:
        token_without_diacritics = remove_diacritics(token)
        if token_without_diacritics.lower() not in mappings:
            reconstructed_tokens.append(token_without_diacritics)
        else:
            reconstructed_tokens.append(add_diacritics(token_without_diacritics, mappings))
    return reconstructed_tokens

def verify(text: str, reconstructed_text: str, tokens: list[str], reconstructed_tokens: list[str]) -> bool:
    """Verify that the reconstructed text matches the original"""
    if text != reconstructed_text:
        if len(tokens) != len(reconstructed_tokens):
            logger.warning(f"tokens: {len(tokens)}, reconstructed_tokens: {len(reconstructed_tokens)}")

        if len(text) != len(reconstructed_text):
            logger.warning(f"text: {len(text)}, reconstructed_text: {len(reconstructed_text)}")

        for orig, recon in zip(tokens, reconstructed_tokens):
            if orig != recon:
                logger.warning(f"original: {orig}, reconstructed: {recon}")
        return False
    return True

def test_txt_file(path: str) -> bool:
    """Test the diacritics processing on a text file"""
    with open(path, "r") as f:
        text = f.read()
    
    tokens = generate_tokens(text)
    mappings = make_mappings(tokens)
    reconstructed_tokens = reconstruct_tokens(tokens, mappings)
    reconstructed_text = join_tokens(reconstructed_tokens)
    return verify(text, reconstructed_text, tokens, reconstructed_tokens)

def load_mappings_from_file(path: str) -> dict[str, str]:
    """Load mappings from a text file"""
    mappings = {}
    try:
        with open(path, "r") as f:
            for line in f:
                if ',' in line:
                    k, v = line.strip().split(",", 1)  # Split on first comma only
                    mappings[k.lower()] = v.lower()  # Convert key and value to lowercase
        logger.info(f"Loaded {len(mappings)} mappings from file {path}")
    except Exception as e:
        logger.error(f"Error loading mappings from file {path}: {e}")
    return mappings

def translate_text(text: str, mappings: dict[str, str]) -> str:
    """Translate text by adding diacritics based on provided mappings"""
    tokens = generate_tokens(text)
    translated_tokens = reconstruct_tokens(tokens, mappings)
    return join_tokens(translated_tokens)