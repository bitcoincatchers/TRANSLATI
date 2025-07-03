"""
Helper functions for the Telegram Translation Bot
"""
import logging
import re
from typing import List, Optional
from langdetect import detect
from langdetect.lang_detect_exception import LangDetectException

def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('bot.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def detect_language(text: str) -> Optional[str]:
    """
    Detect the language of the given text

    Args:
        text (str): Text to analyze

    Returns:
        str: Language code (e.g., 'en', 'es', 'fr') or None if detection fails
    """
    try:
        # Clean text for better detection
        clean_text = re.sub(r'[^\w\s]', '', text)
        if len(clean_text.strip()) < 3:
            return None

        detected_lang = detect(clean_text)
        return detected_lang
    except LangDetectException:
        return None
    except Exception as e:
        logging.error(f"Language detection error: {e}")
        return None

def split_long_message(text: str, max_length: int = 4000) -> List[str]:
    """
    Split long messages into chunks that fit Telegram's message limit

    Args:
        text (str): Text to split
        max_length (int): Maximum length per chunk

    Returns:
        List[str]: List of text chunks
    """
    if len(text) <= max_length:
        return [text]

    chunks = []
    current_chunk = ""

    # Split by sentences first
    sentences = re.split(r'(?<=[.!?])\s+', text)

    for sentence in sentences:
        if len(current_chunk + sentence) <= max_length:
            current_chunk += sentence + " "
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = sentence + " "
            else:
                # If single sentence is too long, split by words
                words = sentence.split()
                temp_chunk = ""
                for word in words:
                    if len(temp_chunk + word) <= max_length:
                        temp_chunk += word + " "
                    else:
                        if temp_chunk:
                            chunks.append(temp_chunk.strip())
                            temp_chunk = word + " "
                        else:
                            # If single word is too long, force split
                            chunks.append(word[:max_length])
                            temp_chunk = word[max_length:] + " "
                current_chunk = temp_chunk

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks

def clean_text(text: str) -> str:
    """
    Clean text for better translation

    Args:
        text (str): Text to clean

    Returns:
        str: Cleaned text
    """
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)

    # Remove special characters that might interfere with translation
    text = re.sub(r'[^\w\s.,!?;:()\-'"]', '', text)

    return text.strip()

def format_translation_response(original_text: str, translated_text: str, 
                              source_lang: str, target_lang: str) -> str:
    """
    Format the translation response message

    Args:
        original_text (str): Original text
        translated_text (str): Translated text
        source_lang (str): Source language code
        target_lang (str): Target language code

    Returns:
        str: Formatted response message
    """
    lang_names = {
        'en': 'English',
        'es': 'Spanish',
        'fr': 'French',
        'de': 'German',
        'it': 'Italian',
        'pt': 'Portuguese',
        'ru': 'Russian',
        'ja': 'Japanese',
        'ko': 'Korean',
        'zh': 'Chinese',
        'ar': 'Arabic',
        'hi': 'Hindi'
    }

    source_name = lang_names.get(source_lang, source_lang.upper())
    target_name = lang_names.get(target_lang, target_lang.upper())

    response = f"🌐 **Translation**\n"
    response += f"📝 **{source_name} → {target_name}**\n\n"
    response += f"**Original:** {original_text}\n\n"
    response += f"**Translation:** {translated_text}"

    return response

def is_valid_language_code(lang_code: str) -> bool:
    """
    Check if language code is valid

    Args:
        lang_code (str): Language code to validate

    Returns:
        bool: True if valid, False otherwise
    """
    valid_codes = {
        'en', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'ja', 'ko', 
        'zh', 'ar', 'hi', 'nl', 'sv', 'da', 'no', 'fi', 'pl',
        'tr', 'he', 'th', 'vi', 'id', 'ms', 'tl', 'sw', 'yo'
    }
    return lang_code.lower() in valid_codes
