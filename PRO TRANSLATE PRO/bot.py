#!/usr/bin/env python3
"""
Telegram Translation Bot - FINAL VERSION
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

# Import your settings
from settings import settings

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(settings.LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def detect_language(text: str) -> Optional[str]:
    """Detect the language of the given text"""
    try:
        # Clean text for better detection
        clean_text = re.sub(r'[^\w\s]', '', text)
        if len(clean_text.strip()) < 3:
            return None
        
        detected_lang = detect(clean_text)
        logger.info(f"Language detected: {detected_lang} for text: {text[:30]}...")
        return detected_lang
    except LangDetectException as e:
        logger.warning(f"Language detection failed (LangDetectException): {e}")
        return None
    except Exception as e:
        logger.warning(f"Language detection failed: {e}")
        return None

def split_long_message(text: str, max_length: int = None) -> List[str]:
    """Split long messages into chunks that fit Telegram's limits"""
    if max_length is None:
        max_length = settings.MAX_MESSAGE_LENGTH
    
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
        self.settings = settings
        self.setup_apis()

    def setup_apis(self):
        """Setup OpenAI and Twitter APIs"""
        try:
            # Setup OpenAI
            openai.api_key = self.settings.OPENAI_API_KEY
            self.openai_client = openai.OpenAI(api_key=self.settings.OPENAI_API_KEY)
            logger.info("✅ OpenAI API initialized")

            # Setup Twitter API using OAuth 1.0a
            if self.settings.is_twitter_enabled():
                try:
                    twitter_creds = self.settings.get_twitter_credentials()
                    
                    # Use OAuth 1.0a with all credentials
                    self.twitter_client = tweepy.Client(
                        consumer_key=twitter_creds['api_key'],
                        consumer_secret=twitter_creds['api_secret'],
                        access_token=twitter_creds['access_token'],
                        access_token_secret=twitter_creds['access_token_secret'],
                        wait_on_rate_limit=True
                    )
                    
                    logger.info("✅ Twitter API v2 with OAuth 1.0a initialized")
                    logger.info("🎯 FREE plan - 500 writes per month available")
                    
                    # Test Twitter connection
                    try:
                        me = self.twitter_client.get_me()
                        if me.data:
                            logger.info(f"✅ Twitter connection verified - User: @{me.data.username}")
                        else:
                            logger.info("✅ Twitter connection initialized (user data not accessible with FREE plan)")
                    except Exception as e:
                        logger.warning(f"⚠️ Twitter connection test failed (normal for FREE plan): {e}")
                        logger.info("✅ Twitter configured - ready for posting")
                        
                except Exception as e:
                    logger.error(f"❌ Twitter API setup failed: {e}")
                    self.twitter_client = None
            else:
                self.twitter_client = None
                logger.info("ℹ️ Twitter sharing disabled (missing credentials or disabled)")

        except Exception as e:
            logger.error(f"❌ API setup error: {e}")
            raise

    async def translate_text(self, text: str, target_lang: str = None) -> Optional[str]:
        """Translate text using OpenAI GPT-4 with subtle emoji enhancement"""
        if target_lang is None:
            target_lang = self.settings.DEFAULT_TARGET_LANGUAGE
            
        try:
            clean_input = clean_text(text)
            logger.info(f"🔄 Starting translation for: {clean_input[:50]}...")

            # Get target language name
            supported_langs = self.settings.get_supported_languages()
            target_lang_name = supported_langs.get(target_lang, 'Spanish')

            prompt = f"""Translate the following English text to {target_lang_name}. 
            Make it engaging and natural, not just literal translation.
            Add some personality while keeping the original meaning.
            Add subtle emojis ONLY where they make sense and enhance the message.
            Don't add extra words or change the core message.
            Keep it professional but with a touch of flair.

            Text to translate: {clean_input}"""

            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": f"You are an expert translator who creates engaging, culturally-aware {target_lang_name} translations with subtle emoji enhancements."},
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
        """Post to Twitter using OAuth 1.0a (FREE plan compatible)"""
        result = {"success": False, "tweets": 0, "thread": False, "error": None}
        
        logger.info(f"🐦 Attempting to post to Twitter: {text[:50]}...")
        
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
                # Single tweet
                logger.info("📤 Posting single tweet...")
                response = self.twitter_client.create_tweet(text=text)
                result["success"] = True
                result["tweets"] = 1
                result["thread"] = False
                logger.info(f"✅ Posted single tweet successfully: {response.data['id']}")
                logger.info("🔥 FREE PLAN SUCCESS!")
            else:
                # Twitter thread
                logger.info("📤 Posting Twitter thread...")
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
                logger.info("🔥 FREE PLAN THREAD SUCCESS!")
            
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
            message_chunks = split_long_message(text)
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
🔥 **¡Bienvenido al Bot de Traducción FINAL!**

Detecto automáticamente mensajes en inglés y los traduzco al español.

**🎯 CARACTERÍSTICAS:**
• 🔄 Auto-traducción EN→ES
• 🐦 Posts en Twitter (500 writes/mes)
• 📱 Posts en grupo Telegram
• 🎯 División inteligente de hilos
• 🔘 Botones de confirmación

**¿Cómo funciona?**
• ¡Envía cualquier texto en inglés!
• Lo traduciré automáticamente
• Te preguntaré si quieres compartirlo
• Click "✅ SÍ" para postear en Twitter y Telegram

**Comandos:**
• `/start` - Este mensaje
• `/help` - Ayuda detallada
• `/status` - Estado del bot
• `/getid` - ID del chat actual

¡Listo para traducir! ¡Envíame texto en inglés! 🌐
    """

    await update.message.reply_text(welcome_message, parse_mode=ParseMode.MARKDOWN)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_message = """
🆘 **Ayuda del Bot de Traducción FINAL**

**¿Cómo funciona?**
1. Envía CUALQUIER texto en inglés
2. El bot detecta el idioma automáticamente
3. Muestra la traducción con botones
4. Click "✅ SÍ" → Postea en Twitter y Telegram
5. Click "❌ NO" → Cancela

**🔥 CARACTERÍSTICAS PLAN GRATUITO:**
• ✅ Detección automática de idioma
• ✅ Traducción con GPT-4
• ✅ Posts en Twitter (500 writes/mes)
• ✅ Hilos de Twitter para textos largos
• ✅ Soporte para mensajes reenviados
• ✅ Soporte para imágenes con subtítulos
• ✅ Botones inline para confirmación

**Comandos de debug:**
• `/getid` - Obtener ID del chat
• `/status` - Verificar estado de sistemas

**¡Solo envía texto en inglés y yo me encargo del resto!** 🚀
    """

    await update.message.reply_text(help_message, parse_mode=ParseMode.MARKDOWN)

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command"""
    twitter_status = "✅ Conectado (OAuth 1.0a)" if translation_bot.twitter_client else "❌ Deshabilitado/Error"
    
    status_message = f"""
🔥 **Estado del Bot - VERSIÓN FINAL**

**APIs:**
• OpenAI: {'✅ Conectado' if translation_bot.openai_client else '❌ Error'}
• Twitter: {twitter_status}

**Configuración:**
• Auto-detección: ✅ Habilitada
• Idioma objetivo: {settings.get_supported_languages().get(settings.DEFAULT_TARGET_LANGUAGE, 'Español')}
• Compartir Twitter: {'✅ Habilitado (Plan GRATUITO)' if settings.ENABLE_TWITTER_SHARING else '❌ Deshabilitado'}
• Grupo Telegram: {settings.TELEGRAM_GROUP_ID}

**Configuración Twitter:**
• Credenciales: {'✅ Configuradas' if settings.is_twitter_enabled() else '❌ Faltantes'}
• Plan: GRATUITO (500 writes/mes)
• Modo: OAuth 1.0a

**Estadísticas:**
• Tiempo activo: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
• Estado: 🟢 En línea
• Versión: FINAL con Config Completa

¡Listo para traducir! 🌐
    """

    await update.message.reply_text(status_message, parse_mode=ParseMode.MARKDOWN)

async def getid_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get chat ID for debugging"""
    chat_id = update.effective_chat.id
    chat_type = update.effective_chat.type
    chat_title = getattr(update.effective_chat, 'title', 'Sin título')
    user_name = update.effective_user.first_name
    
    info = f"""
🔍 **Info del Chat - VERSIÓN FINAL**

**Detalles del Chat:**
• **ID:** `{chat_id}`
• **Tipo:** {chat_type}
• **Título:** {chat_title}

**Detalles del Usuario:**
• **Nombre:** {user_name}
• **ID Usuario:** {update.effective_user.id}

**Instrucciones:**
Si este es un GRUPO y quieres que el bot postee aquí:
1. Copia el Chat ID: `{chat_id}`
2. Ve a Heroku → Settings → Config Vars
3. Actualiza TELEGRAM_GROUP_ID con este valor: `{chat_id}`
4. ¡El bot posteará traducciones en este chat!

**Nota:** Los IDs de grupo suelen ser números negativos.
**Objetivo actual:** {settings.TELEGRAM_GROUP_ID}
    """
    await update.message.reply_text(info, parse_mode=ParseMode.MARKDOWN)

async def handle_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button clicks for confirmation"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    logger.info(f"🔘 Usuario {user_id} hizo click en botón: {query.data}")
    
    # Answer the callback query to remove loading state
    await query.answer()
    
    if query.data == "confirm_share":
        # User confirmed sharing
        translation = context.user_data.get('pending_translation')
        
        if not translation:
            logger.warning(f"⚠️ No hay traducción pendiente para usuario {user_id}")
            await query.edit_message_text("❌ No hay traducción pendiente.")
            return
        
        logger.info(f"📤 Usuario {user_id} confirmó compartir. Iniciando distribución...")
        await query.edit_message_text("📤 Compartiendo en Twitter y Telegram...")
        
        # Post to both platforms
        logger.info("🚀 Iniciando posteo paralelo en Twitter (OAuth 1.0a) y Telegram...")
        twitter_result = await translation_bot.post_to_twitter(translation)
        telegram_result = await translation_bot.post_to_telegram(context.bot, translation)
        
        # Create detailed confirmation message
        confirmation_parts = []
        
        if twitter_result["success"]:
            if twitter_result["thread"]:
                confirmation_parts.append(f"🐦 **Twitter:** 🔥 ¡ÉXITO! Hilo publicado ({twitter_result['tweets']} tweets)")
                logger.info(f"✅ Hilo de Twitter posteado exitosamente ({twitter_result['tweets']} tweets)")
            else:
                confirmation_parts.append(f"🐦 **Twitter:** 🔥 ¡ÉXITO! Tweet publicado")
                logger.info("✅ Tweet único posteado exitosamente")
        else:
            confirmation_parts.append(f"🐦 **Twitter:** ❌ Error - {twitter_result.get('error', 'Desconocido')}")
            logger.error(f"❌ Fallo en posteo de Twitter: {twitter_result.get('error', 'Desconocido')}")
        
        if telegram_result["success"]:
            if telegram_result["messages"] > 1:
                confirmation_parts.append(f"📱 **Telegram:** ✅ Enviado en {telegram_result['messages']} mensajes")
                logger.info(f"✅ Mensajes de Telegram posteados exitosamente ({telegram_result['messages']} mensajes)")
            else:
                confirmation_parts.append(f"📱 **Telegram:** ✅ Mensaje enviado correctamente")
                logger.info("✅ Mensaje único de Telegram posteado exitosamente")
        else:
            confirmation_parts.append(f"📱 **Telegram:** ❌ Error - {telegram_result.get('error', 'Desconocido')}")
            logger.error(f"❌ Fallo en posteo de Telegram: {telegram_result.get('error', 'Desconocido')}")
        
        final_message = "🔥 **Resultados FINALES:**\n\n" + "\n".join(confirmation_parts)
        
        await query.edit_message_text(final_message, parse_mode=ParseMode.MARKDOWN)
        logger.info(f"✅ Proceso de compartir completado para usuario {user_id}")
        
        # Clear stored data
        context.user_data.clear()
        
    elif query.data == "deny_share":
        # User denied sharing
        logger.info(f"❌ Usuario {user_id} canceló compartir")
        await query.edit_message_text("❌ Compartición cancelada.")
        context.user_data.clear()

async def handle_auto_translation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle automatic translation of English messages (including forwarded with images)"""
    if not update.message:
        return

    user_id = update.effective_user.id
    logger.info(f"📨 Mensaje recibido de usuario {user_id}")

    # Extract text from different message types
    text = None
    
    # Check if it's a forwarded message
    if update.message.forward_from or update.message.forward_from_chat:
        logger.info("📨 Mensaje reenviado detectado")
    
    # Get text from various sources
    if update.message.text:
        text = update.message.text.strip()
        logger.info(f"📝 Mensaje de texto: {text[:50]}...")
    elif update.message.caption:
        # Message with image/video + caption
        text = update.message.caption.strip()
        logger.info(f"📸 Media con subtítulo: {text[:50]}...")
    
    # If no text found, skip
    if not text:
        logger.info("⏭️ No se encontró contenido de texto en el mensaje - saltando")
        return

    # Skip commands and very short messages
    if text.startswith('/'):
        logger.info("⏭️ Comando detectado - saltando auto-traducción")
        return
        
    if len(text) < 5:
        logger.info("⏭️ Mensaje muy corto - saltando auto-traducción")
        return

    try:
        # Detect language
        logger.info("🔍 Iniciando detección de idioma...")
        detected_lang = detect_language(text)
        
        # Only process English messages
        if detected_lang != 'en':
            logger.info(f"⏭️ Mensaje no inglés detectado ({detected_lang}) - saltando traducción")
            return  # Silent skip for non-English
        
        logger.info("🇺🇸 Mensaje en inglés confirmado - iniciando proceso de traducción")
        
        # Show processing message
        processing_msg = await update.message.reply_text("🔄 Traduciendo automáticamente...")
        
        # Translate to Spanish
        translation = await translation_bot.translate_text(text)
        
        if translation:
            # Store for later use
            context.user_data['pending_translation'] = translation
            context.user_data['original_text'] = text
            logger.info(f"💾 Traducción guardada para usuario {user_id}")
            
            # Create inline keyboard with buttons
            keyboard = [
                [
                    InlineKeyboardButton("✅ SÍ, Compartir", callback_data="confirm_share"),
                    InlineKeyboardButton("❌ NO, Cancelar", callback_data="deny_share")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Show ONLY the translation + buttons
            response = f"📝 **Traducción:**\n\n{translation}\n\n🔥 ¿Compartir en Twitter y Telegram?"
            
            await processing_msg.edit_text(response, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
            logger.info(f"✅ Traducción presentada a usuario {user_id} con botones")
        else:
            logger.error("❌ Traducción falló")
            await processing_msg.edit_text("❌ Error en la traducción.")

    except Exception as e:
        logger.error(f"❌ Error de auto-traducción: {e}")
        logger.error(f"❌ Tipo de error: {type(e).__name__}")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(f"❌ Update {update} causó error {context.error}")

def main():
    """Main function to run the bot"""
    try:
        logger.info("🔥 Inicializando Bot de Traducción VERSIÓN FINAL...")
        
        application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()

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
        logger.info("🔥 Iniciando Bot de Traducción VERSIÓN FINAL...")
        logger.info(f"🔑 Bot Token: {settings.TELEGRAM_BOT_TOKEN[:10]}...")
        logger.info(f"📱 Group ID: {settings.TELEGRAM_GROUP_ID}")
        logger.info(f"🌐 Auto-traducción: Inglés → {settings.get_supported_languages().get(settings.DEFAULT_TARGET_LANGUAGE, 'Español')}")
        logger.info(f"🐦 Twitter: {'✅ OAuth 1.0a HABILITADO' if settings.ENABLE_TWITTER_SHARING else '❌ Deshabilitado'}")
        logger.info("🔥 Versión: FINAL con settings.py - 500 writes/mes")
        logger.info("✅ ¡Bot listo para procesar mensajes!")

        application.run_polling(drop_pending_updates=True)

    except Exception as e:
        logger.error(f"❌ Error de inicio del bot: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
