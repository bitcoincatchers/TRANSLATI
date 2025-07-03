"""
Configuration settings for Telegram Translation Bot
"""
import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings:
    """Bot configuration settings"""
    
    def __init__(self):
        """Initialize settings from environment variables"""
        
        # Telegram Configuration
        self.TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
        self.TELEGRAM_GROUP_ID = os.getenv('TELEGRAM_GROUP_ID')
        
        # OpenAI Configuration
        self.OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
        
        # Twitter Configuration
        self.TWITTER_API_KEY = os.getenv('TWITTER_API_KEY')
        self.TWITTER_API_SECRET = os.getenv('TWITTER_API_SECRET')
        self.TWITTER_ACCESS_TOKEN = os.getenv('TWITTER_ACCESS_TOKEN', '')
        self.TWITTER_ACCESS_TOKEN_SECRET = os.getenv('TWITTER_ACCESS_TOKEN_SECRET', '')
        
        # Bot Configuration
        self.DEFAULT_TARGET_LANGUAGE = os.getenv('DEFAULT_TARGET_LANGUAGE', 'es')
        self.MAX_MESSAGE_LENGTH = int(os.getenv('MAX_MESSAGE_LENGTH', '4000'))
        self.ENABLE_AUTO_DETECT = os.getenv('ENABLE_AUTO_DETECT', 'true').lower() == 'true'
        self.ENABLE_TWITTER_SHARING = os.getenv('ENABLE_TWITTER_SHARING', 'true').lower() == 'true'
        
        # Logging Configuration
        self.LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
        self.LOG_FILE = os.getenv('LOG_FILE', 'bot.log')
        
        # Rate Limiting
        self.MAX_REQUESTS_PER_MINUTE = int(os.getenv('MAX_REQUESTS_PER_MINUTE', '30'))
        self.MAX_REQUESTS_PER_HOUR = int(os.getenv('MAX_REQUESTS_PER_HOUR', '500'))
        
        # Database (for future features)
        self.DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///bot.db')
        
        # Validate required settings
        self._validate_settings()
    
    def _validate_settings(self):
        """Validate that required settings are present"""
        required_settings = [
            ('TELEGRAM_BOT_TOKEN', self.TELEGRAM_BOT_TOKEN),
            ('OPENAI_API_KEY', self.OPENAI_API_KEY),
            ('TELEGRAM_GROUP_ID', self.TELEGRAM_GROUP_ID)
        ]
        
        missing_settings = []
        for name, value in required_settings:
            if not value:
                missing_settings.append(name)
        
        if missing_settings:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_settings)}")
    
    def get_twitter_credentials(self) -> Optional[dict]:
        """Get Twitter credentials if available"""
        if not self.ENABLE_TWITTER_SHARING:
            return None
            
        if all([
            self.TWITTER_API_KEY,
            self.TWITTER_API_SECRET,
            self.TWITTER_ACCESS_TOKEN,
            self.TWITTER_ACCESS_TOKEN_SECRET
        ]):
            return {
                'api_key': self.TWITTER_API_KEY,
                'api_secret': self.TWITTER_API_SECRET,
                'access_token': self.TWITTER_ACCESS_TOKEN,
                'access_token_secret': self.TWITTER_ACCESS_TOKEN_SECRET
            }
        return None
    
    def is_twitter_enabled(self) -> bool:
        """Check if Twitter integration is properly configured"""
        return self.ENABLE_TWITTER_SHARING and self.get_twitter_credentials() is not None
    
    def get_supported_languages(self) -> dict:
        """Get supported language codes and names"""
        return {
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
            'hi': 'Hindi',
            'nl': 'Dutch',
            'sv': 'Swedish',
            'da': 'Danish',
            'no': 'Norwegian',
            'fi': 'Finnish',
            'pl': 'Polish',
            'tr': 'Turkish',
            'he': 'Hebrew',
            'th': 'Thai',
            'vi': 'Vietnamese',
            'id': 'Indonesian',
            'ms': 'Malay',
            'tl': 'Filipino',
            'sw': 'Swahili',
            'yo': 'Yoruba'
        }
    
    def __str__(self) -> str:
        """String representation of settings (without sensitive data)"""
        return f"""
Bot Settings:
- Target Language: {self.DEFAULT_TARGET_LANGUAGE}
- Max Message Length: {self.MAX_MESSAGE_LENGTH}
- Auto Detect: {self.ENABLE_AUTO_DETECT}
- Twitter Sharing: {self.ENABLE_TWITTER_SHARING}
- Log Level: {self.LOG_LEVEL}
- Rate Limits: {self.MAX_REQUESTS_PER_MINUTE}/min, {self.MAX_REQUESTS_PER_HOUR}/hour
        """.strip()

# Global settings instance
settings = Settings()
