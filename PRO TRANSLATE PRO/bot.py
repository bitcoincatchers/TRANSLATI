#!/usr/bin/env python3
"""
Telegram Translation Bot - Standalone Version
Detects English messages, translates to Spanish, and posts to Twitter/Telegram
"""

import asyncio
import logging
import os
import sys
import re
from datetime import datetime
from typing import Optional, List

import openai
import tweepy
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode
from dotenv import load_dotenv
from langdetect import detect
from langdetect.lang_detect_exception import LangDetectException

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

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
        
        # Bot Configuration
        self.ENABLE_TWITTER_SHARING = os.getenv('ENABLE_TWITTER_SHARING', 'true').lower() == 'true'
        
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

def detect_language(text: str) -> Optional[str]:
    """Detect the language of the given text"""
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
        logger.warning(f"Language detection failed: {e}")
        return None

def split_long_message(text: str, max_length: int = 4000) -> List[str]:
    """Split long messages into chunks that fit Telegram's limits"""
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
                            # Force split if single word is too long
                            chunks.append(word[:max_length])
                            temp_chunk = word[max_length:] + " "
                current_chunk = temp_chunk
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks

def clean_text(text: str) -> str:
    """Clean text for better translation"""
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove special characters that might interfere
    text = re.sub(r'[^\w\s.,!?;:()\-\'"]', '', text)
    return text.strip()

class TranslationBot:
    """Main Translation Bot Class"""

    def __init__(self):
        """Initialize the bot with all configurations"""
        self.settings = Settings()
        self.setup_apis()

    def setup_apis(self):
        """Setup OpenAI and Twitter APIs"""
        try:
            # Setup OpenAI
            openai.api_key = self.settings.OPENAI_API_KEY
            self.openai_client = openai.OpenAI(api_key=self.settings.OPENAI_API_KEY)
            logger.info("✅ OpenAI API initialized")

            # Setup Twitter API v2
            if self.settings.ENABLE_TWITTER_SHARING:
                self.twitter_client = tweepy.Client(
                    consumer_key=self.settings.TWITTER_API_KEY,
                    consumer_secret=self.settings.TWITTER_API_SECRET,
                    wait_on_rate_limit=True
                )
                logger.info("✅ Twitter API v2 initialized")
            else:
                self.twitter_client = None
                logger.info("ℹ️ Twitter sharing disabled")

        except Exception as e:
            logger.error(f"❌ API setup error: {e}")
            raise

    async def translate_text(self, text: str, target_lang: str = "es") -> Optional[str]:
        """Translate text using OpenAI GPT-4"""
        try:
            clean_input = clean_text(text)

            prompt = f"""Translate the following English text to Spanish. 
            Make it engaging and natural, not just literal translation.
            Add some personality while keeping the original meaning.

            Text to translate: {clean_input}"""

            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert translator who creates engaging, culturally-aware Spanish translations."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.7
            )

            translation = response.choices[0].message.content.strip()
            logger.info(f"✅ Translation completed: {len(text)} chars -> {len(translation)} chars")
            return translation

        except Exception as e:
            logger.error(f"❌ Translation error: {e}")
            return None

    async def post_to_twitter(self, text: str) -> bool:
        """Post translated text to Twitter using v2 API"""
        if not self.twitter_client or not self.settings.ENABLE_TWITTER_SHARING:
            return False

        try:
            timestamp = datetime.now().strftime("%H:%M")
            tweet_text = f"🌐 Auto-Translation ({timestamp})\n\n{text}"

            if len(tweet_text) > 280:
                tweet_text = tweet_text[:275] + "..."

            response = self.twitter_client.create_tweet(text=tweet_text)
            logger.info(f"✅ Posted to Twitter: {response.data['id']}")
            return True

        except Exception as e:
            logger.error(f"❌ Twitter posting error: {e}")
            return False

    async def post_to_telegram(self, bot: Bot, text: str, original_text: str = None) -> bool:
        """Post translation to Telegram group"""
        try:
            if original_text:
                message = f"🌐 **Auto-Translation**\n\n"
                message += f"**Original (EN):** {original_text[:100]}{'...' if len(original_text) > 100 else ''}\n\n"
                message += f"**Spanish:** {text}"
            else:
                message = f"🌐 **Translation**\n\n{text}"

            message_chunks = split_long_message(message, 4000)

            for chunk in message_chunks:
                await bot.send_message(
                    chat_id=self.settings.TELEGRAM_GROUP_ID,
                    text=chunk,
                    parse_mode=ParseMode.MARKDOWN
                )

            logger.info(f"✅ Posted to Telegram group: {len(message_chunks)} messages")
            return True

        except Exception as e:
            logger.error(f"❌ Telegram posting error: {e}")
            return False

    async def process_message(self, text: str, bot: Bot) -> dict:
        """Process a message: detect language, translate, and post"""
        results = {
            'detected_language': None,
            'translation': None,
            'twitter_posted': False,
            'telegram_posted': False,
            'error': None
        }

        try:
            # Detect language
            detected_lang = detect_language(text)
            results['detected_language'] = detected_lang

            # Only process English messages
            if detected_lang != 'en':
                results['error'] = f"Not English (detected: {detected_lang})"
                return results

            logger.info(f"🔍 Processing English message: {text[:50]}...")

            # Translate to Spanish
            translation = await self.translate_text(text, 'es')
            if not translation:
                results['error'] = "Translation failed"
                return results

            results['translation'] = translation

            # Post to Twitter
            if self.settings.ENABLE_TWITTER_SHARING:
                twitter_success = await self.post_to_twitter(translation)
                results['twitter_posted'] = twitter_success

            # Post to Telegram group
            telegram_success = await self.post_to_telegram(bot, translation, text)
            results['telegram_posted'] = telegram_success

            logger.info(f"✅ Message processed successfully")
            return results

        except Exception as e:
            logger.error(f"❌ Message processing error: {e}")
            results['error'] = str(e)
            return results

# Bot Command Handlers
translation_bot = TranslationBot()

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    welcome_message = """
🤖 **Welcome to Translation Bot!**

I automatically detect English messages and translate them to Spanish.

**Commands:**
• `/start` - Show this welcome message
• `/help` - Get help and usage info
• `/translate <text>` - Translate text to Spanish
• `/detect <text>` - Detect language of text
• `/status` - Check bot status

**Auto-Translation:**
• I monitor messages for English text
• Automatically translate to Spanish
• Post to Twitter and Telegram group

Ready to translate! 🌐
    """

    await update.message.reply_text(welcome_message, parse_mode=ParseMode.MARKDOWN)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_message = """
🆘 **Translation Bot Help**

**How it works:**
1. Send any English text
2. Bot detects the language
3. Translates to Spanish using GPT-4
4. Posts to Twitter and Telegram group

**Manual Commands:**
• `/translate <text>` - Force translate text
• `/detect <text>` - Check language detection
• `/status` - Bot health check

**Features:**
• ✅ Auto language detection
• ✅ GPT-4 powered translation
• ✅ Twitter integration
• ✅ Smart message splitting
• ✅ Error handling

Ready to translate! 🚀
    """

    await update.message.reply_text(help_message, parse_mode=ParseMode.MARKDOWN)

async def translate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /translate command"""
    if not context.args:
        await update.message.reply_text("❌ Please provide text to translate.\nUsage: `/translate Hello world`", parse_mode=ParseMode.MARKDOWN)
        return

    text = ' '.join(context.args)
    processing_msg = await update.message.reply_text("🔄 Translating...")

    try:
        translation = await translation_bot.translate_text(text, 'es')

        if translation:
            response = f"🌐 **Translation**\n\n**Original (EN):** {text}\n\n**Spanish:** {translation}"
            await processing_msg.edit_text(response, parse_mode=ParseMode.MARKDOWN)
        else:
            await processing_msg.edit_text("❌ Translation failed. Please try again.")

    except Exception as e:
        logger.error(f"Translation command error: {e}")
        await processing_msg.edit_text("❌ An error occurred during translation.")

async def detect_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /detect command"""
    if not context.args:
        await update.message.reply_text("❌ Please provide text to detect.\nUsage: `/detect Hello world`", parse_mode=ParseMode.MARKDOWN)
        return

    text = ' '.join(context.args)
    detected_lang = detect_language(text)

    if detected_lang:
        lang_names = {
            'en': 'English', 'es': 'Spanish', 'fr': 'French', 
            'de': 'German', 'it': 'Italian', 'pt': 'Portuguese'
        }
        lang_name = lang_names.get(detected_lang, detected_lang.upper())

        response = f"🔍 **Language Detection**\n\n**Text:** {text}\n**Detected:** {lang_name} ({detected_lang})"
    else:
        response = f"❌ Could not detect language for: {text}"

    await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command"""
    status_message = f"""
🤖 **Bot Status**

**APIs:**
• OpenAI: {'✅ Connected' if translation_bot.openai_client else '❌ Error'}
• Twitter: {'✅ Connected' if translation_bot.twitter_client else '❌ Disabled'}

**Settings:**
• Auto-detect: ✅ Enabled
• Target Language: Spanish (es)
• Twitter Sharing: {'✅ Enabled' if translation_bot.settings.ENABLE_TWITTER_SHARING else '❌ Disabled'}

**Stats:**
• Uptime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
• Status: 🟢 Online

Ready to translate! 🌐
    """

    await update.message.reply_text(status_message, parse_mode=ParseMode.MARKDOWN)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages for auto-translation"""
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()

    # Skip commands and short messages
    if text.startswith('/') or len(text) < 10:
        return

    try:
        results = await translation_bot.process_message(text, context.bot)

        if results['error']:
            if 'Not English' in results['error']:
                return  # Silent skip
            else:
                await update.message.reply_text(f"❌ {results['error']}")
        elif results['translation']:
            feedback = "✅ **Translation completed!**\n\n"
            if results['twitter_posted']:
                feedback += "🐦 Posted to Twitter\n"
            if results['telegram_posted']:
                feedback += "📱 Posted to Telegram group\n"

            await update.message.reply_text(feedback, parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        logger.error(f"Message handling error: {e}")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(f"Update {update} caused error {context.error}")

def main():
    """Main function to run the bot"""
    try:
        application = Application.builder().token(translation_bot.settings.TELEGRAM_BOT_TOKEN).build()

        # Add handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("translate", translate_command))
        application.add_handler(CommandHandler("detect", detect_command))
        application.add_handler(CommandHandler("status", status_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        application.add_error_handler(error_handler)

        # Start bot
        logger.info("🚀 Starting Telegram Translation Bot...")
        logger.info(f"🔑 Bot Token: {translation_bot.settings.TELEGRAM_BOT_TOKEN[:10]}...")
        logger.info(f"📱 Group ID: {translation_bot.settings.TELEGRAM_GROUP_ID}")
        logger.info(f"🌐 Target Language: Spanish")
        logger.info(f"🐦 Twitter: {'Enabled' if translation_bot.settings.ENABLE_TWITTER_SHARING else 'Disabled'}")

        application.run_polling(drop_pending_updates=True)

    except Exception as e:
        logger.error(f"❌ Bot startup error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
