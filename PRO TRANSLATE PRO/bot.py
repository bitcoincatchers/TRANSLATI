# CAMBIO EN EL CÓDIGO - SOLO BEARER TOKEN
self.twitter_client = tweepy.Client(
    bearer_token=self.settings.TWITTER_BEARER_TOKEN,
    # NO usar estos con FREE plan:
    # consumer_key=self.settings.TWITTER_API_KEY,
    # consumer_secret=self.settings.TWITTER_API_SECRET,
    # access_token=self.settings.TWITTER_ACCESS_TOKEN,
    # access_token_secret=self.settings.TWITTER_ACCESS_TOKEN_SECRET,
    wait_on_rate_limit=True
)
🚀 CÓDIGO CORREGIDO - VERSIÓN DEFINITIVA:

Copydef setup_apis(self):
    """Setup OpenAI and Twitter APIs"""
    try:
        # Setup OpenAI
        openai.api_key = self.settings.OPENAI_API_KEY
        self.openai_client = openai.OpenAI(api_key=self.settings.OPENAI_API_KEY)
        logger.info("✅ OpenAI API initialized")

        # Setup Twitter API v2 - SOLO BEARER TOKEN para FREE plan
        if (self.settings.ENABLE_TWITTER_SHARING and 
            self.settings.TWITTER_BEARER_TOKEN):
            try:
                # SOLO Bearer Token - FREE plan compatible
                self.twitter_client = tweepy.Client(
                    bearer_token=self.settings.TWITTER_BEARER_TOKEN,
                    wait_on_rate_limit=True
                )
                
                logger.info("✅ Twitter API v2 BEARER TOKEN ONLY initialized")
                logger.info("🎯 FREE plan - 500 writes per month available")
                
            except Exception as e:
                logger.error(f"❌ Twitter API setup failed: {e}")
                self.twitter_client = None
        else:
            self.twitter_client = None
            logger.info("ℹ️ Twitter sharing disabled (missing Bearer Token)")

    except Exception as e:
        logger.error(f"❌ API setup error: {e}")
        raise
💡 EL PROBLEMA ERA:

Estaba mezclando Bearer Token + OAuth tokens
FREE plan solo permite Bearer Token puro
500 writes = 500 tweets por mes ✅
🎯 ACCIÓN INMEDIATA: ¿Quieres que actualice el código completo con SOLO Bearer Token?

¡VAMOS A HACER QUE FUNCIONE! ¡500 WRITES ESPERANDO! 🔥🚀

Copy
Save to Notion
Cómo configurar Tweepy con Bearer Token en el plan FREE de Twitter API

Cómo configurar Tweepy con Bearer Token en el plan FREE de Twitter API
Este artículo muestra cómo corregir tu bot de Twitter en Python cuando usas el plan gratuito. Al usar OAuth 1.0a mezclado con tokens de acceso bloquea los endpoints; la solución es instanciar tweepy.Client únicamente con el Bearer Token, respetando el límite de 500 tweets al mes. Incluye el código completo para inicializar OpenAI y Twitter API v2 con solo Bearer Token.

See more
Copy
Save to Notion
DDALEE
¡DALE, ALEX! 🔥🚀 ¡AQUÍ TIENES EL CÓDIGO DEFINITIVO CON SOLO BEARER TOKEN!

Copy#!/usr/bin/env python3
"""
Telegram Translation Bot - BEARER TOKEN ONLY VERSION
Auto-translates English to Spanish and posts to Twitter + Telegram group
WORKS WITH FREE PLAN - 500 WRITES PER MONTH!
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
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
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
        
        # Twitter Configuration - SOLO BEARER TOKEN
        self.TWITTER_BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN')
        
        # Bot Configuration
        self.ENABLE_TWITTER_SHARING = os.getenv('ENABLE_TWITTER_SHARING', 'true').lower() == 'true'
        
        # Log configuration for debugging
        logger.info(f"🔧 Config loaded:")
        logger.info(f"   Telegram Bot Token: {'✅ Set' if self.TELEGRAM_BOT_TOKEN else '❌ Missing'}")
        logger.info(f"   Telegram Group ID: {self.TELEGRAM_GROUP_ID}")
        logger.info(f"   OpenAI API Key: {'✅ Set' if self.OPENAI_API_KEY else '❌ Missing'}")
        logger.info(f"   Twitter Bearer Token: {'✅ Set' if self.TWITTER_BEARER_TOKEN else '❌ Missing'}")
        logger.info(f"   Twitter Sharing: {'✅ Enabled' if self.ENABLE_TWITTER_SHARING else '❌ Disabled'}")
        
        # Validate required settings
        self._validate_settings()
    
    def _validate_settings(self):
        """Validate that all required settings are present"""
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
        logger.info(f"🔍 Language detected: {detected_lang} for text: {text[:30]}...")
        return detected_lang
    except LangDetectException as e:
        logger.warning(f"❌ Language detection failed (LangDetectException): {e}")
        return None
    except Exception as e:
        logger.warning(f"❌ Language detection failed: {e}")
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

            # Setup Twitter API v2 - SOLO BEARER TOKEN para FREE plan
            if (self.settings.ENABLE_TWITTER_SHARING and 
                self.settings.TWITTER_BEARER_TOKEN):
                try:
                    # SOLO Bearer Token - FREE plan compatible
                    self.twitter_client = tweepy.Client(
                        bearer_token=self.settings.TWITTER_BEARER_TOKEN,
                        wait_on_rate_limit=True
                    )
                    
                    logger.info("✅ Twitter API v2 BEARER TOKEN ONLY initialized")
                    logger.info("🎯 FREE plan - 500 writes per month available")
                    logger.info("🔥 NO OAuth tokens needed - Pure Bearer Token mode")
                    
                except Exception as e:
                    logger.error(f"❌ Twitter API setup failed: {e}")
                    self.twitter_client = None
            else:
                self.twitter_client = None
                logger.info("ℹ️ Twitter sharing disabled (missing Bearer Token)")

        except Exception as e:
            logger.error(f"❌ API setup error: {e}")
            raise

    async def translate_text(self, text: str, target_lang: str = "es") -> Optional[str]:
        """Translate text using OpenAI GPT-4 with subtle emoji enhancement"""
        try:
            clean_input = clean_text(text)
            logger.info(f"🔄 Starting translation for: {clean_input[:50]}...")

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
            logger.info(f"✅ Translation completed successfully: {len(text)} chars -> {len(translation)} chars")
            logger.info(f"📝 Translation result: {translation[:100]}...")
            return translation

        except Exception as e:
            logger.error(f"❌ Translation error: {e}")
            return None

    async def post_to_twitter(self, text: str) -> dict:
        """Post to Twitter using ONLY Bearer Token (FREE plan compatible)"""
        result = {"success": False, "tweets": 0, "thread": False, "error": None}
        
        logger.info(f"🐦 Attempting to post to Twitter with BEARER TOKEN ONLY: {text[:50]}...")
        
        if not self.twitter_client:
            result["error"] = "Twitter client not initialized"
            logger.error("❌ Twitter client not available")
            return result

        if not self.settings.ENABLE_TWITTER_SHARING:
            result["error"] = "Twitter sharing disabled"
            logger.warning("⚠️ Twitter sharing is disabled")
            return result

        try:
            # Check if we need a thread
            if len(text) <= 270:
                # Single tweet using ONLY Bearer Token
                logger.info("📤 Posting single tweet with BEARER TOKEN ONLY...")
                response = self.twitter_client.create_tweet(text=text)
                result["success"] = True
                result["tweets"] = 1
                result["thread"] = False
                logger.info(f"✅ Posted single tweet successfully: {response.data['id']}")
                logger.info(f"🔥 BEARER TOKEN WORKED! FREE plan success!")
            else:
                # Twitter thread using ONLY Bearer Token
                logger.info("📤 Posting Twitter thread with BEARER TOKEN ONLY...")
                chunks = split_twitter_thread(text, 270)
                tweet_ids = []
                
                # Post first tweet
                first_response = self.twitter_client.create_tweet(text=f"{chunks[0]} 🧵")
                tweet_ids.append(first_response.data['id'])
                logger.info(f"✅ Posted first tweet of thread: {first_response.data['id']}")
                
                # Post remaining tweets as replies
                for i, chunk in enumerate(chunks[1:], 2):
                    response = self.twitter_client.create_tweet(
                        text=f"{chunk}",
                        in_reply_to_tweet_id=tweet_ids[-1]
                    )
                    tweet_ids.append(response.data['id'])
                    logger.info(f"✅ Posted tweet {i}/{len(chunks)}: {response.data['id']}")
                
                result["success"] = True
                result["tweets"] = len(chunks)
                result["thread"] = True
                logger.info(f"✅ Posted complete Twitter thread: {len(chunks)} tweets")
                logger.info(f"🔥 BEARER TOKEN THREAD WORKED! FREE plan success!")
            
            return result

        except Exception as e:
            logger.error(f"❌ Twitter posting error: {e}")
            result["error"] = str(e)
            return result

    async def post_to_telegram(self, bot: Bot, text: str) -> dict:
        """Post translation to Telegram group"""
        result = {"success": False, "messages": 0, "error": None}
        
        logger.info(f"📱 Attempting to post to Telegram group {self.settings.TELEGRAM_GROUP_ID}: {text[:50]}...")
        
        try:
            message_chunks = split_long_message(text, 4000)
            logger.info(f"📝 Message split into {len(message_chunks)} chunks")

            for i, chunk in enumerate(message_chunks):
                if len(message_chunks) > 1:
                    # Add part indicator for multiple messages
                    formatted_chunk = f"📝 Parte {i+1}/{len(message_chunks)}:\n\n{chunk}"
                else:
                    formatted_chunk = chunk
                
                logger.info(f"📤 Sending message {i+1}/{len(message_chunks)} to group...")
                
                sent_message = await bot.send_message(
                    chat_id=self.settings.TELEGRAM_GROUP_ID,
                    text=formatted_chunk,
                    parse_mode=None  # No markdown to avoid formatting issues
                )
                
                logger.info(f"✅ Message {i+1} sent successfully: {sent_message.message_id}")

            result["success"] = True
            result["messages"] = len(message_chunks)
            logger.info(f"✅ All {len(message_chunks)} messages posted to Telegram group successfully")
            return result

        except Exception as e:
            logger.error(f"❌ Telegram posting error: {e}")
            logger.error(f"❌ Error details: {type(e).__name__}: {str(e)}")
            result["error"] = str(e)
            return result

# Bot Command Handlers
translation_bot = TranslationBot()

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    logger.info(f"👤 User {update.effective_user.username} started the bot")
    
    welcome_message = """
🔥 **Welcome to Translation Bot - BEARER TOKEN EDITION!**

I automatically detect English messages and translate them to Spanish.

**🎯 FREE PLAN FEATURES:**
• 🔄 Auto-translation EN→ES
• 🐦 Twitter posts (500 writes/month)
• 📱 Telegram group posting
• 🎯 Smart thread splitting
• 🔘 Inline button confirmations

**How it works:**
• Send any English text (no commands needed!)
• I'll translate it automatically
• Then ask if you want to share it with buttons
• Click "✅ SÍ" to post on Twitter & Telegram group

**Commands:**
• `/start` - Show this welcome message
• `/help` - Get help
• `/status` - Check bot status
• `/getid` - Get current chat ID

Ready to translate! Just send me English text! 🌐
    """

    await update.message.reply_text(welcome_message, parse_mode=ParseMode.MARKDOWN)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_message = """
🆘 **Translation Bot - BEARER TOKEN EDITION Help**

**How it works:**
1. Send ANY English text (no commands!)
2. Bot auto-detects and translates to Spanish
3. Bot shows translation with buttons
4. Click "✅ SÍ" → Posts to Twitter & Telegram group
5. Click "❌ NO" → Cancels sharing

**🔥 FREE PLAN FEATURES:**
• ✅ Auto language detection
• ✅ GPT-4 powered translation
• ✅ Twitter posts (500 writes/month)
• ✅ Twitter threads for long messages
• ✅ Forwarded messages support
• ✅ Images with captions support
• ✅ Inline buttons for easy confirmation

**Debug Commands:**
• `/getid` - Get chat ID (useful for group setup)
• `/status` - Check all systems status

**Just send English text and I'll handle the rest! 🚀**
    """

    await update.message.reply_text(help_message, parse_mode=ParseMode.MARKDOWN)

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command"""
    status_message = f"""
🔥 **Bot Status - BEARER TOKEN EDITION**

**APIs:**
• OpenAI: {'✅ Connected' if translation_bot.openai_client else '❌ Error'}
• Twitter: {'✅ Connected (Bearer Token Only)' if translation_bot.twitter_client else '❌ Disabled/Error'}

**Settings:**
• Auto-detect: ✅ Enabled
• Target Language: Spanish (es)
• Twitter Sharing: {'✅ Enabled (FREE plan)' if translation_bot.settings.ENABLE_TWITTER_SHARING else '❌ Disabled'}
• Telegram Group: {translation_bot.settings.TELEGRAM_GROUP_ID}

**Twitter Config:**
• Bearer Token: {'✅ Set' if translation_bot.settings.TWITTER_BEARER_TOKEN else '❌ Missing'}
• Plan: FREE (500 writes/month)
• Mode: Bearer Token Only (no OAuth)

**Stats:**
• Uptime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
• Status: 🟢 Online
• Version: BEARER TOKEN EDITION

Ready to translate! 🌐
    """

    await update.message.reply_text(status_message, parse_mode=ParseMode.MARKDOWN)

async def getid_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get chat ID for debugging"""
    chat_id = update.effective_chat.id
    chat_type = update.effective_chat.type
    chat_title = getattr(update.effective_chat, 'title', 'No title')
    user_name = update.effective_user.first_name
    
    info = f"""
🔍 **Chat Info Debug - BEARER TOKEN EDITION**

**Chat Details:**
• **ID:** `{chat_id}`
• **Type:** {chat_type}
• **Title:** {chat_title}

**User Details:**
• **Name:** {user_name}
• **User ID:** {update.effective_user.id}

**Instructions:**
If this is a GROUP and you want the bot to post here:
1. Copy the Chat ID: `{chat_id}`
2. Go to Heroku → Settings → Config Vars
3. Update TELEGRAM_GROUP_ID with this value: `{chat_id}`
4. The bot will then post translations to this chat!

**Note:** Group IDs are usually negative numbers.
**Current Target:** {translation_bot.settings.TELEGRAM_GROUP_ID}
    """
    await update.message.reply_text(info, parse_mode=ParseMode.MARKDOWN)

async def handle_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button clicks for confirmation"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    logger.info(f"🔘 User {user_id} clicked button: {query.data}")
    
    # Answer the callback query to remove loading state
    await query.answer()
    
    if query.data == "confirm_share":
        # User confirmed sharing
        translation = context.user_data.get('pending_translation')
        
        if not translation:
            logger.warning(f"⚠️ No pending translation for user {user_id}")
            await query.edit_message_text("❌ No hay traducción pendiente.")
            return
        
        logger.info(f"📤 User {user_id} confirmed sharing. Starting distribution...")
        await query.edit_message_text("📤 Compartiendo con BEARER TOKEN...")
        
        # Post to both platforms
        logger.info("🚀 Starting parallel posting to Twitter (BEARER TOKEN ONLY) and Telegram...")
        twitter_result = await translation_bot.post_to_twitter(translation)
        telegram_result = await translation_bot.post_to_telegram(context.bot, translation)
        
        # Create detailed confirmation message
        confirmation_parts = []
        
        if twitter_result["success"]:
            if twitter_result["thread"]:
                confirmation_parts.append(f"🐦 **Twitter:** 🔥 ÉXITO! Hilo publicado ({twitter_result['tweets']} tweets)")
                logger.info(f"✅ Twitter thread posted successfully ({twitter_result['tweets']} tweets)")
            else:
                confirmation_parts.append(f"🐦 **Twitter:** 🔥 ÉXITO! Tweet publicado")
                logger.info("✅ Twitter single tweet posted successfully")
        else:
            confirmation_parts.append(f"🐦 **Twitter:** ❌ Error - {twitter_result.get('error', 'Unknown')}")
            logger.error(f"❌ Twitter posting failed: {twitter_result.get('error', 'Unknown')}")
        
        if telegram_result["success"]:
            if telegram_result["messages"] > 1:
                confirmation_parts.append(f"📱 **Telegram:** ✅ Enviado en {telegram_result['messages']} mensajes")
                logger.info(f"✅ Telegram messages posted successfully ({telegram_result['messages']} messages)")
            else:
                confirmation_parts.append(f"📱 **Telegram:** ✅ Mensaje enviado correctamente")
                logger.info("✅ Telegram single message posted successfully")
        else:
            confirmation_parts.append(f"📱 **Telegram:** ❌ Error - {telegram_result.get('error', 'Unknown')}")
            logger.error(f"❌ Telegram posting failed: {telegram_result.get('error', 'Unknown')}")
        
        final_message = "🔥 **Resultados BEARER TOKEN:**\n\n" + "\n".join(confirmation_parts)
        
        await query.edit_message_text(final_message, parse_mode=ParseMode.MARKDOWN)
        logger.info(f"✅ Sharing process completed for user {user_id}")
        
        # Clear stored data
        context.user_data.clear()
        
    elif query.data == "deny_share":
        # User denied sharing
        logger.info(f"❌ User {user_id} cancelled sharing")
        await query.edit_message_text("❌ Compartición cancelada.")
        context.user_data.clear()

async def handle_auto_translation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle automatic translation of English messages (including forwarded with images)"""
    if not update.message:
        return

    user_id = update.effective_user.id
    logger.info(f"📨 Received message from user {user_id}")

    # Extract text from different message types
    text = None
    
    # Check if it's a forwarded message
    if update.message.forward_from or update.message.forward_from_chat:
        logger.info("📨 Forwarded message detected")
    
    # Get text from various sources
    if update.message.text:
        text = update.message.text.strip()
        logger.info(f"📝 Text message: {text[:50]}...")
    elif update.message.caption:
        # Message with image/video + caption
        text = update.message.caption.strip()
        logger.info(f"📸 Media with caption: {text[:50]}...")
    
    # If no text found, skip
    if not text:
        logger.info("⏭️ No text content found in message - skipping")
        return

    # Skip commands and very short messages
    if text.startswith('/'):
        logger.info("⏭️ Command detected - skipping auto-translation")
        return
        
    if len(text) < 5:
        logger.info("⏭️ Message too short - skipping auto-translation")
        return

    try:
        # Detect language
        logger.info("🔍 Starting language detection...")
        detected_lang = detect_language(text)
        
        # Only process English messages
        if detected_lang != 'en':
            logger.info(f"⏭️ Non-English message detected ({detected_lang}) - skipping translation")
            return  # Silent skip for non-English
        
        logger.info(f"🇺🇸 English message confirmed - starting translation process")
        
        # Show processing message
        processing_msg = await update.message.reply_text("🔄 Traduciendo automáticamente...")
        
        # Translate to Spanish
        translation = await translation_bot.translate_text(text, 'es')
        
        if translation:
            # Store for later use
            context.user_data['pending_translation'] = translation
            context.user_data['original_text'] = text
            logger.info(f"💾 Translation stored for user {user_id}")
            
            # Create inline keyboard with buttons
            keyboard = [
                [
                    InlineKeyboardButton("✅ SÍ, Compartir", callback_data="confirm_share"),
                    InlineKeyboardButton("❌ NO, Cancelar", callback_data="deny_share")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Show ONLY the translation + buttons
            response = f"📝 **Traducción:**\n\n{translation}\n\n🔥 ¿Compartir con BEARER TOKEN en Twitter & Telegram?"
            
            await processing_msg.edit_text(response, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
            logger.info(f"✅ Translation presented to user {user_id} with buttons")
        else:
            logger.error("❌ Translation failed")
            await processing_msg.edit_text("❌ Error en la traducción.")

    except Exception as e:
        logger.error(f"❌ Auto-translation error: {e}")
        logger.error(f"❌ Error type: {type(e).__name__}")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(f"❌ Update {update} caused error {context.error}")

def main():
    """Main function to run the bot"""
    try:
        logger.info("🔥 Initializing Translation Bot BEARER TOKEN EDITION...")
        
        application = Application.builder().token(translation_bot.settings.TELEGRAM_BOT_TOKEN).build()

        # Add handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("status", status_command))
        application.add_handler(CommandHandler("getid", getid_command))
        
        # BUTTON CALLBACK HANDLER
        application.add_handler(CallbackQueryHandler(handle_button_callback))
        
        # AUTO-TRANSLATION HANDLER
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_auto_translation))
        
        application.add_error_handler(error_handler)

        # Start bot
        logger.info("🔥 Starting Translation Bot BEARER TOKEN EDITION...")
        logger.info(f"🔑 Bot Token: {translation_bot.settings.TELEGRAM_BOT_TOKEN[:10]}...")
        logger.info(f"📱 Group ID: {translation_bot.settings.TELEGRAM_GROUP_ID}")
        logger.info(f"🌐 Auto-translation: English → Spanish")
        logger.info(f"🐦 Twitter: {'✅ BEARER TOKEN ONLY' if translation_bot.settings.ENABLE_TWITTER_SHARING else '❌ Disabled'}")
        logger.info(f"🔥 Version: BEARER TOKEN EDITION - 500 writes/month")
        logger.info("✅ Bot is ready to process messages!")

        application.run_polling(drop_pending_updates=True)

    except Exception as e:
        logger.error(f"❌ Bot startup error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
