import docx
import re
import unicodedata

def read_docx(path: str) -> str:
    doc = docx.Document(path)
    text = ""
    for paragraph in doc.paragraphs:
        text += paragraph.text + "\n"
    return text

def generate_tokens(text: str) -> list[str]:
    tokens = re.split(r'([^\w\u0300-\u036f\s]|\s+)', text)
    tokens = [t for t in tokens if t]
    return tokens

def join_tokens(tokens: list[str]) -> str:
    return ''.join(tokens)

def remove_diacritics(word: str) -> str:
    normalized = unicodedata.normalize('NFKD', word)
    return ''.join(c for c in normalized if not unicodedata.combining(c))

def add_diacritics(word: str, mappings: dict[str, str]) -> str:
    word_with_diacritics = mappings.get(word.lower(), word)

    if word.isupper():
        return word_with_diacritics.upper()
    elif word.islower():
        return word_with_diacritics.lower()
    elif word[0].isupper():
        return word_with_diacritics[0].upper() + word_with_diacritics[1:]
    else:
        raise ValueError(f"Cannot add diacritics to word: {word} with mapping: {word_with_diacritics}")
    
def make_mappings(tokens: list[str]) -> dict[str, str]:
    mappings = {}
    for token in tokens:
        token_without_diacritics = remove_diacritics(token)
        if (token != token_without_diacritics) and not token.isspace():
            mappings[token_without_diacritics.lower()] = token.lower()
    return mappings

def reconstruct_tokens(tokens: list[str], mappings: dict[str, str]) -> list[str]:
    reconstructed_tokens = []
    for token in tokens:
        token_without_diacritics = remove_diacritics(token)
        if token_without_diacritics.lower() not in mappings:
            reconstructed_tokens.append(token_without_diacritics)
        else:
            reconstructed_tokens.append(add_diacritics(token_without_diacritics, mappings))
    return reconstructed_tokens

def verify(text: str, reconstructed_text: str, tokens: list[str], reconstructed_tokens: list[str]) -> bool:
    if text != reconstructed_text:
        if len(tokens) != len(reconstructed_tokens):
            print(f"tokens: {len(tokens)}, reconstructed_tokens: {len(reconstructed_tokens)}")

        if len(text) != len(reconstructed_text):
            print(f"text: {len(text)}, reconstructed_text: {len(reconstructed_text)}")

        for orig, recon in zip(tokens, reconstructed_tokens):
            if orig != recon:
                print(f"original: {orig}, reconstructed: {recon}")
        return False
    else:
        return True

def test_txt_file(path: str) -> bool:
    text = open(path, "r").read()
    tokens = generate_tokens(text)
    mappings = make_mappings(tokens)
    reconstructed_tokens = reconstruct_tokens(tokens, mappings)
    reconstructed_text = join_tokens(reconstructed_tokens)
    return verify(text, reconstructed_text, tokens, reconstructed_tokens)

def load_mappings(path: str) -> dict[str, str]:
    mappings = {}
    with open(path, "r") as f:
        for line in f:
            k, v = line.strip().split(",")
            mappings[k] = v
    return mappings