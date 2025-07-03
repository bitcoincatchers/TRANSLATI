# 🤖 Telegram Translation Bot

A powerful Telegram bot that automatically translates messages using OpenAI's GPT models with optional Twitter integration.

## ✨ Features

- 🌐 **Multi-language Translation**: Supports 25+ languages
- 🔍 **Auto Language Detection**: Automatically detects source language
- 📱 **Telegram Integration**: Works in groups and private chats
- 🐦 **Twitter Sharing**: Optional tweet sharing functionality
- 🚀 **Fast & Reliable**: Built with async/await for optimal performance
- 🔧 **Easy Deployment**: Docker and Heroku ready
- 📊 **Logging**: Comprehensive logging for monitoring

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone <your-repo-url>
cd telegram-translation-bot
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables
```bash
cp .env.example .env
```

Edit `.env` with your API credentials:
```env
TELEGRAM_BOT_TOKEN=7722508544:AAFZPj04nRjv9_1U_v1b1mv0jEYD7MdHGwM
TELEGRAM_GROUP_ID=7725774283
OPENAI_API_KEY=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
TWITTER_API_KEY=JDiaAOMiqL1eiPr3TRPu2qwJA
TWITTER_API_SECRET=FbQ3eQQr0dc75pIsPkpjFDfdTNPfX8I7BTxPMF3kOfqOi6KQZM
```

### 4. Run the Bot
```bash
python main.py
```

## 🐳 Docker Deployment

### Build and Run
```bash
docker-compose up -d
```

### View Logs
```bash
docker-compose logs -f telegram-bot
```

## 🚀 Heroku Deployment

1. **Create Heroku App**
```bash
heroku create your-bot-name
```

2. **Set Environment Variables**
```bash
heroku config:set TELEGRAM_BOT_TOKEN=your_token
heroku config:set OPENAI_API_KEY=your_key
heroku config:set TELEGRAM_GROUP_ID=your_group_id
```

3. **Deploy**
```bash
git push heroku main
```

## 📱 Bot Commands

- `/start` - Start the bot and get welcome message
- `/help` - Show available commands
- `/translate <text>` - Translate text to default language
- `/translate_to <lang> <text>` - Translate to specific language
- `/detect <text>` - Detect language of text
- `/languages` - Show supported languages
- `/settings` - Configure bot settings

## 🌍 Supported Languages

- English (en)
- Spanish (es)
- French (fr)
- German (de)
- Italian (it)
- Portuguese (pt)
- Russian (ru)
- Japanese (ja)
- Korean (ko)
- Chinese (zh)
- Arabic (ar)
- Hindi (hi)
- And many more...

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `TELEGRAM_BOT_TOKEN` | Telegram bot token from @BotFather | ✅ |
| `OPENAI_API_KEY` | OpenAI API key | ✅ |
| `TELEGRAM_GROUP_ID` | Telegram group ID for notifications | ✅ |
| `TWITTER_API_KEY` | Twitter API key (optional) | ❌ |
| `TWITTER_API_SECRET` | Twitter API secret (optional) | ❌ |
| `DEFAULT_TARGET_LANGUAGE` | Default translation language | ❌ |
| `MAX_MESSAGE_LENGTH` | Maximum message length | ❌ |

### Bot Settings

- **Default Language**: English (en)
- **Max Message Length**: 4000 characters
- **Auto-detect**: Enabled
- **Rate Limiting**: 30 requests/minute

## 📊 Monitoring

### Logs
The bot creates detailed logs in `bot.log`:
```bash
tail -f bot.log
```

### Health Check
```bash
curl http://localhost:8000/health
```

## 🛠️ Development

### Project Structure
```
telegram-translation-bot/
├── main.py                 # Main bot application
├── config/
│   ├── __init__.py
│   └── settings.py         # Configuration settings
├── utils/
│   ├── __init__.py
│   └── helpers.py          # Helper functions
├── requirements.txt        # Python dependencies
├── Dockerfile             # Docker configuration
├── docker-compose.yml     # Docker Compose setup
├── Procfile              # Heroku configuration
├── .env.example          # Environment variables template
└── README.md             # This file
```

### Adding New Features

1. **Create feature branch**
```bash
git checkout -b feature/new-feature
```

2. **Implement feature**
3. **Test thoroughly**
4. **Submit pull request**

## 🐛 Troubleshooting

### Common Issues

1. **Bot not responding**
   - Check bot token validity
   - Verify bot is added to group
   - Check internet connection

2. **Translation errors**
   - Verify OpenAI API key
   - Check API quota limits
   - Review error logs

3. **Docker issues**
   - Ensure Docker is running
   - Check environment variables
   - Review container logs

### Getting Help

- Check the logs: `tail -f bot.log`
- Review error messages
- Verify API credentials
- Test with simple commands first

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📞 Support

For support and questions:
- Create an issue on GitHub
- Check the documentation
- Review the troubleshooting section

---

**Made with ❤️ for the global community** 🌍
