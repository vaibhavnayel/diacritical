/**
 * Diacritical Translator
 * JavaScript module for the translator functionality
 */

// Main module for translator
const TranslatorModule = (function() {
    // Translate text function
    function translateText() {
        const inputText = document.getElementById('inputText').value;
        if (!inputText.trim()) {
            alert('Please enter some text to translate');
            return;
        }

        fetch('/translate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ text: inputText })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            if (data.error) {
                alert(data.error);
            } else {
                document.getElementById('outputText').value = data.result;
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred while translating');
        });
    }

    // Copy to clipboard function
    function copyToClipboard() {
        const outputText = document.getElementById('outputText');
        outputText.select();
        try {
            document.execCommand('copy');
            alert('Text copied to clipboard!');
        } catch (err) {
            console.error('Failed to copy text:', err);
            // Fallback to modern clipboard API
            navigator.clipboard.writeText(outputText.value)
                .then(() => alert('Text copied to clipboard!'))
                .catch(err => {
                    console.error('Failed to copy text:', err);
                    alert('Failed to copy text');
                });
        }
    }

    // Public methods
    return {
        init: function() {
            // Set up event listeners
            document.getElementById('translateBtn').addEventListener('click', translateText);
            document.getElementById('copyBtn').addEventListener('click', copyToClipboard);
        },
        translate: translateText,
        copyToClipboard: copyToClipboard
    };
})();

// Initialize when document is ready
$(document).ready(function() {
    TranslatorModule.init();
}); 