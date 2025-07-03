#!/usr/bin/env python3
"""
Telegram Translation Bot - Main Application
Detects English messages, translates to Spanish, and posts to Twitter/Telegram
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from typing import Optional, List

import openai
import tweepy
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

# Import our utilities
from utils.helpers import (
    setup_logging, detect_language, split_long_message, 
    clean_text, format_translation_response, is_valid_language_code
)
from config.settings import Settings

# Initialize logging
logger = setup_logging()

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

            # Setup Twitter API v2 (NO USES IMGHDR)
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
        """
        Translate text using OpenAI GPT-4

        Args:
            text (str): Text to translate
            target_lang (str): Target language code

        Returns:
            str: Translated text or None if failed
        """
        try:
            # Clean the text
            clean_input = clean_text(text)

            # Create translation prompt
            lang_names = {
                'es': 'Spanish',
                'en': 'English',
                'fr': 'French',
                'de': 'German',
                'it': 'Italian',
                'pt': 'Portuguese'
            }

            target_lang_name = lang_names.get(target_lang, target_lang.upper())

            prompt = f"""Translate the following text to {target_lang_name}. 
            Make it engaging and natural, not just literal translation.
            Add some personality while keeping the original meaning.

            Text to translate: {clean_input}"""

            # Call OpenAI API
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": f"You are an expert translator who creates engaging, culturally-aware {target_lang_name} translations."},
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
        """
        Post translated text to Twitter using v2 API

        Args:
            text (str): Text to post

        Returns:
            bool: True if successful, False otherwise
        """
        if not self.twitter_client or not self.settings.ENABLE_TWITTER_SHARING:
            return False

        try:
            # Prepare tweet text
            timestamp = datetime.now().strftime("%H:%M")
            tweet_text = f"🌐 Auto-Translation ({timestamp})\n\n{text}"

            # Split if too long for Twitter
            if len(tweet_text) > 280:
                tweet_text = tweet_text[:275] + "..."

            # Post tweet using v2 API
            response = self.twitter_client.create_tweet(text=tweet_text)
            logger.info(f"✅ Posted to Twitter: {response.data['id']}")
            return True

        except Exception as e:
            logger.error(f"❌ Twitter posting error: {e}")
            return False

    async def post_to_telegram(self, bot: Bot, text: str, original_text: str = None) -> bool:
        """
        Post translation to Telegram group

        Args:
            bot (Bot): Telegram bot instance
            text (str): Translated text
            original_text (str): Original text for context

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Format message
            if original_text:
                message = f"🌐 **Auto-Translation**\n\n"
                message += f"**Original (EN):** {original_text[:100]}{'...' if len(original_text) > 100 else ''}\n\n"
                message += f"**Spanish:** {text}"
            else:
                message = f"🌐 **Translation**\n\n{text}"

            # Split long messages
            message_chunks = split_long_message(message, 4000)

            # Send to group
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
        """
        Process a message: detect language, translate, and post

        Args:
            text (str): Message text
            bot (Bot): Telegram bot instance

        Returns:
            dict: Processing results
        """
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

**Supported Languages:**
English → Spanish (primary)
Also supports: French, German, Italian, Portuguese

Need help? Just send a message! 🚀
    """

    await update.message.reply_text(help_message, parse_mode=ParseMode.MARKDOWN)

async def translate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /translate command"""
    if not context.args:
        await update.message.reply_text("❌ Please provide text to translate.\nUsage: `/translate Hello world`", parse_mode=ParseMode.MARKDOWN)
        return

    text = ' '.join(context.args)

    # Show processing message
    processing_msg = await update.message.reply_text("🔄 Translating...")

    try:
        # Translate
        translation = await translation_bot.translate_text(text, 'es')

        if translation:
            # Format response
            response = format_translation_response(text, translation, 'en', 'es')
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

        response = f"🔍 **Language Detection**\n\n"
        response += f"**Text:** {text}\n"
        response += f"**Detected:** {lang_name} ({detected_lang})"
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

    # Skip commands
    if text.startswith('/'):
        return

    # Skip short messages
    if len(text) < 10:
        return

    try:
        # Process message
        results = await translation_bot.process_message(text, context.bot)

        # Send feedback to user
        if results['error']:
            if 'Not English' in results['error']:
                # Silent skip for non-English messages
                return
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
        # Create application
        application = Application.builder().token(translation_bot.settings.TELEGRAM_BOT_TOKEN).build()

        # Add handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("translate", translate_command))
        application.add_handler(CommandHandler("detect", detect_command))
        application.add_handler(CommandHandler("status", status_command))

        # Add message handler for auto-translation
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        # Add error handler
        application.add_error_handler(error_handler)

        # Start bot
        logger.info("🚀 Starting Telegram Translation Bot...")
        logger.info(f"🔑 Bot Token: {translation_bot.settings.TELEGRAM_BOT_TOKEN[:10]}...")
        logger.info(f"📱 Group ID: {translation_bot.settings.TELEGRAM_GROUP_ID}")
        logger.info(f"🌐 Target Language: Spanish")
        logger.info(f"🐦 Twitter: {'Enabled' if translation_bot.settings.ENABLE_TWITTER_SHARING else 'Disabled'}")

        # Run the bot
        application.run_polling(drop_pending_updates=True)

    except Exception as e:
        logger.error(f"❌ Bot startup error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
