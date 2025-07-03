#!/usr/bin/env python3
"""
Telegram Translation Bot - Auto Translation with Twitter Threads
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

def split_twitter_thread(text: str, max_length: int = 270) -> List[str]:
    """Split text into Twitter thread chunks with smart breaks"""
    if len(text) <= max_length:
        return [text]
    
    chunks = []
    current_chunk = ""
    
    # Split by sentences for better readability
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    for sentence in sentences:
        # Check if adding this sentence would exceed limit
        if len(current_chunk + " " + sentence) > max_length:
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = sentence
            else:
                # Single sentence too long, split by meaningful breaks
                words = sentence.split()
                temp_chunk = ""
                for word in words:
                    if len(temp_chunk + " " + word) <= max_length:
                        temp_chunk += " " + word if temp_chunk else word
                    else:
                        if temp_chunk:
                            chunks.append(temp_chunk.strip())
                            temp_chunk = word
                        else:
                            # Force split word if too long
                            chunks.append(word[:max_length])
                            temp_chunk = word[max_length:]
                current_chunk = temp_chunk
        else:
            current_chunk += " " + sentence if current_chunk else sentence
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks

def clean_text(text: str) -> str:
    """Clean text for better translation"""
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
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
        """Translate text using OpenAI GPT-4 with subtle emoji enhancement"""
        try:
            clean_input = clean_text(text)

            prompt = f"""Translate the following English text to Spanish. 
            Make it engaging and natural, not just literal translation.
            Add some personality while keeping the original meaning.
            Add subtle emojis ONLY where they make sense and enhance the message.
            Don't add extra words or change the core message.
            Keep it professional but with a touch of flair.

            Text to translate: {clean_input}"""

            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert translator who creates engaging, culturally-aware Spanish translations with subtle emoji enhancements."},
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

    async def post_to_twitter(self, text: str) -> dict:
        """Post to Twitter as single tweet or thread"""
        result = {"success": False, "tweets": 0, "thread": False, "error": None}
        
        if not self.twitter_client or not self.settings.ENABLE_TWITTER_SHARING:
            result["error"] = "Twitter disabled"
            return result

        try:
            # Check if we need a thread
            if len(text) <= 270:
                # Single tweet
                response = self.twitter_client.create_tweet(text=text)
                result["success"] = True
                result["tweets"] = 1
                result["thread"] = False
                logger.info(f"✅ Posted single tweet: {response.data['id']}")
            else:
                # Twitter thread
                chunks = split_twitter_thread(text, 270)
                tweet_ids = []
                
                # Post first tweet
                first_response = self.twitter_client.create_tweet(text=f"{chunks[0]} 🧵")
                tweet_ids.append(first_response.data['id'])
                
                # Post remaining tweets as replies
                for i, chunk in enumerate(chunks[1:], 2):
                    response = self.twitter_client.create_tweet(
                        text=f"{chunk}",
                        in_reply_to_tweet_id=tweet_ids[-1]
                    )
                    tweet_ids.append(response.data['id'])
                
                result["success"] = True
                result["tweets"] = len(chunks)
                result["thread"] = True
                logger.info(f"✅ Posted Twitter thread: {len(chunks)} tweets")
            
            return result

        except Exception as e:
            logger.error(f"❌ Twitter posting error: {e}")
            result["error"] = str(e)
            return result

    async def post_to_telegram(self, bot: Bot, text: str) -> dict:
        """Post translation to Telegram group"""
        result = {"success": False, "messages": 0, "error": None}
        
        try:
            message_chunks = split_long_message(text, 4000)

            for i, chunk in enumerate(message_chunks):
                if len(message_chunks) > 1:
                    # Add part indicator for multiple messages
                    formatted_chunk = f"📝 Parte {i+1}/{len(message_chunks)}:\n\n{chunk}"
                else:
                    formatted_chunk = chunk
                
                await bot.send_message(
                    chat_id=self.settings.TELEGRAM_GROUP_ID,
                    text=formatted_chunk,
                    parse_mode=None  # No markdown to avoid formatting issues
                )

            result["success"] = True
            result["messages"] = len(message_chunks)
            logger.info(f"✅ Posted to Telegram group: {len(message_chunks)} messages")
            return result

        except Exception as e:
            logger.error(f"❌ Telegram posting error: {e}")
            result["error"] = str(e)
            return result

# Bot Command Handlers
translation_bot = TranslationBot()

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    welcome_message = """
🤖 **Welcome to Auto Translation Bot!**

I automatically detect English messages and translate them to Spanish.

**How it works:**
• Send any English text (no commands needed!)
• I'll translate it automatically
• Then ask if you want to share it
• Respond "SÍ" to post on Twitter & Telegram group

**Commands:**
• `/start` - Show this welcome message
• `/help` - Get help
• `/status` - Check bot status

Ready to translate! Just send me English text! 🌐
    """

    await update.message.reply_text(welcome_message, parse_mode=ParseMode.MARKDOWN)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_message = """
🆘 **Auto Translation Bot Help**

**How it works:**
1. Send ANY English text (no commands!)
2. Bot auto-detects and translates to Spanish
3. Bot asks: "¿Compartir?"
4. Reply "SÍ" → Posts to Twitter & Telegram group
5. Reply "NO" → Cancels sharing

**Features:**
• ✅ Auto language detection
• ✅ GPT-4 powered translation
• ✅ Twitter threads for long messages
• ✅ Confirmation before sharing
• ✅ Detailed posting confirmations

**Just send English text and I'll handle the rest! 🚀**
    """

    await update.message.reply_text(help_message, parse_mode=ParseMode.MARKDOWN)

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

async def handle_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle YES/NO confirmation for sharing"""
    text = update.message.text.strip().upper()
    
    if text in ['SÍ', 'SI', 'YES', 'Y']:
        # Obtener traducción guardada
        translation = context.user_data.get('pending_translation')
        
        if not translation:
            await update.message.reply_text("❌ No hay traducción pendiente.")
            return
        
        processing_msg = await update.message.reply_text("📤 Compartiendo...")
        
        # Postear en ambas plataformas
        twitter_result = await translation_bot.post_to_twitter(translation)
        telegram_result = await translation_bot.post_to_telegram(context.bot, translation)
        
        # Crear mensaje de confirmación detallado
        confirmation_parts = []
        
        if twitter_result["success"]:
            if twitter_result["thread"]:
                confirmation_parts.append(f"🐦 **Twitter:** Publicado como hilo ({twitter_result['tweets']} tweets)")
            else:
                confirmation_parts.append(f"🐦 **Twitter:** Publicado como tweet único")
        else:
            confirmation_parts.append(f"❌ **Twitter:** Error - {twitter_result.get('error', 'Unknown')}")
        
        if telegram_result["success"]:
            if telegram_result["messages"] > 1:
                confirmation_parts.append(f"📱 **Telegram:** Enviado en {telegram_result['messages']} mensajes")
            else:
                confirmation_parts.append(f"📱 **Telegram:** Mensaje enviado correctamente")
        else:
            confirmation_parts.append(f"❌ **Telegram:** Error - {telegram_result.get('error', 'Unknown')}")
        
        final_message = "✅ **Resultados:**\n\n" + "\n".join(confirmation_parts)
        
        await processing_msg.edit_text(final_message, parse_mode=ParseMode.MARKDOWN)
        
        # Limpiar datos guardados
        context.user_data.clear()
        
    elif text in ['NO', 'N']:
        await update.message.reply_text("❌ Compartición cancelada.")
        context.user_data.clear()

async def handle_auto_translation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle automatic translation of English messages"""
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()

    # Skip commands and very short messages
    if text.startswith('/') or len(text) < 10:
        return

    # Skip if user is responding to confirmation
    if text.upper() in ['SÍ', 'SI', 'YES', 'Y', 'NO', 'N']:
        await handle_confirmation(update, context)
        return

    try:
        # Detect language
        detected_lang = detect_language(text)
        
        # Only process English messages
        if detected_lang != 'en':
            return  # Silent skip for non-English
        
        logger.info(f"🔍 Auto-translating English message: {text[:50]}...")
        
        # Show processing message
        processing_msg = await update.message.reply_text("🔄 Traduciendo automáticamente...")
        
        # Translate to Spanish
        translation = await translation_bot.translate_text(text, 'es')
        
        if translation:
            # Store for later use
            context.user_data['pending_translation'] = translation
            
            # Show ONLY the translation + confirmation question
            response = f"{translation}\n\n¿Estás listo para compartir? Responde **SÍ** o **NO**"
            
            await processing_msg.edit_text(response, parse_mode=ParseMode.MARKDOWN)
        else:
            await processing_msg.edit_text("❌ Error en la traducción.")

    except Exception as e:
        logger.error(f"Auto-translation error: {e}")

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
        application.add_handler(CommandHandler("status", status_command))
        
        # AUTO-TRANSLATION HANDLER (no commands needed!)
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_auto_translation))
        
        application.add_error_handler(error_handler)

        # Start bot
        logger.info("🚀 Starting Auto Translation Bot...")
        logger.info(f"🔑 Bot Token: {translation_bot.settings.TELEGRAM_BOT_TOKEN[:10]}...")
        logger.info(f"📱 Group ID: {translation_bot.settings.TELEGRAM_GROUP_ID}")
        logger.info(f"🌐 Auto-translation: English → Spanish")
        logger.info(f"🐦 Twitter: {'Enabled' if translation_bot.settings.ENABLE_TWITTER_SHARING else 'Disabled'}")

        application.run_polling(drop_pending_updates=True)

    except Exception as e:
        logger.error(f"❌ Bot startup error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
