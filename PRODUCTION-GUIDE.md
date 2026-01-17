# 🚀 Production Deployment Guide

## ✅ Bot Features (Production Ready)

### 💬 AI Chat
- Prefix: `?` for conversational AI
- Command: `!ask <question>` for direct questions
- Model: GPT-4 (most reliable free option)

### 🖼️ Image Generation  
- Command: `!imagine <prompt>`
- 6 models available (flux, flux-pro, flux-realism, dalle, sdxl, playground-v2.5)
- Admin-configurable per server

### 📸 Image Analysis
- Upload images with optional text prompts
- Auto-detects and analyzes using GPT-4 Vision

## 🎯 All Available Commands

### User Commands
- `?<message>` - Chat with AI
- `!ask <question>` - Ask AI
- `!imagine <prompt>` - Generate image
- `!clear` - Clear chat history
- `!ping` - Check latency
- `!listimagemodels` - View image models
- `!bothelp` - Show help

### Admin Commands (Requires Manage Channels)
- `!setchannel` - Enable bot in channel
- `!removechannel` - Disable bot in channel
- `!listchannels` - List active channels
- `!clearallchannels` - Remove restrictions
- `!setimagemodel <model>` - Set image model

## 🐳 Docker Deployment

### Using Docker Compose (Recommended)
```yaml
version: '3.8'
services:
  discord-bot:
    build:
      context: .
      dockerfile: Dockerfile.bot
    environment:
      - DISCORD_BOT_TOKEN=${DISCORD_BOT_TOKEN}
      - PORT=5000
      - RENDER_EXTERNAL_URL=${RENDER_EXTERNAL_URL}
    restart: unless-stopped
```

### Manual Docker
```bash
# Build
docker build -f Dockerfile.bot -t discord-ai-bot .

# Run
docker run -d \
  -e DISCORD_BOT_TOKEN=your_token \
  -e PORT=5000 \
  --name discord-bot \
  discord-ai-bot
```

## ☁️ Cloud Deployment

### Render.com
1. Create new **Web Service**
2. Connect repository
3. Set:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python discord_bot.py`
4. Add Environment Variables:
   - `DISCORD_BOT_TOKEN` = your token
   - `PORT` = 5000
5. Deploy!

### Railway.app
1. Create new project
2. Add GitHub repo
3. Set environment variables
4. Railway auto-detects Python and deploys

### Heroku
```bash
# Login
heroku login

# Create app
heroku create your-bot-name

# Set config
heroku config:set DISCORD_BOT_TOKEN=your_token

# Deploy
git push heroku main
```

## 🔑 Getting Discord Bot Token

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create New Application
3. Go to "Bot" section
4. Click "Add Bot"
5. Copy the token
6. Enable these Intents:
   - Message Content Intent
   - Server Members Intent (optional)

## 📋 Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DISCORD_BOT_TOKEN` | Yes | Your Discord bot token |
| `PORT` | No | Port for health checks (default: 5000) |
| `RENDER_EXTERNAL_URL` | No | For keep-alive pings on Render |

## 🔒 Security Best Practices

1. **Never commit your bot token** - Use environment variables
2. **Restrict bot permissions** - Only give necessary Discord permissions
3. **Use .env file locally**:
   ```bash
   DISCORD_BOT_TOKEN=your_token_here
   ```
4. **Add to .gitignore**:
   ```
   .env
   __pycache__/
   *.pyc
   .venv/
   ```

## ⚡ Performance Tips

1. **Use lightweight hosting** - Bot is memory-efficient (~100MB)
2. **Enable keep-alive** - Set `RENDER_EXTERNAL_URL` for 24/7 uptime
3. **Monitor latency** - Use `!ping` to check response time
4. **Clear history regularly** - Conversation history is in-memory

## 🐛 Troubleshooting

### Bot offline
- Check if DISCORD_BOT_TOKEN is set correctly
- Verify bot is invited to server with proper permissions

### Commands not working
- Ensure bot has "Send Messages" and "Read Message History" permissions
- Check if channel restrictions are enabled (`!listchannels`)

### Image generation fails
- Try different model: `!setimagemodel flux`
- Free providers may have temporary outages

### Image analysis not working
- Ensure you're uploading images (jpg, png, gif, webp)
- Check bot has "Read Message History" permission

## 📊 Monitoring

### Health Check Endpoint
```
GET http://your-bot-url/health
```

Response:
```json
{
  "status": "healthy",
  "bot_ready": true
}
```

### Status Endpoint
```
GET http://your-bot-url/
```

Response:
```json
{
  "status": "online",
  "bot": "YourBotName",
  "guilds": 5,
  "latency": 45,
  "timestamp": "2026-01-17T12:00:00Z"
}
```

## 🔄 Updates & Maintenance

### Updating the Bot
```bash
# Pull latest changes
git pull origin main

# Restart (if using Docker)
docker-compose restart

# Or rebuild
docker-compose up -d --build
```

### Backing Up Data
⚠️ **Note**: Conversation history and settings are in-memory and will reset on restart. For persistence, consider adding a database in future versions.

## 📈 Scaling

For high-traffic servers:
1. Use managed hosting (Railway, Render Pro)
2. Monitor memory usage
3. Consider implementing database for conversation history
4. Add rate limiting if needed

## 🆘 Support

- Check existing issues in repository
- Review troubleshooting section
- Create new issue with:
  - Error messages
  - Steps to reproduce
  - Environment details

## 📝 Production Checklist

- [ ] Discord bot token configured
- [ ] Bot invited to server with proper permissions
- [ ] Environment variables set
- [ ] Health check endpoint working
- [ ] Test all commands (`!bothelp`)
- [ ] Test image generation (`!imagine`)
- [ ] Test image analysis (upload image)
- [ ] Test chat (`?hello`)
- [ ] Admin commands tested
- [ ] Monitoring setup (optional)
- [ ] Documentation updated

## 🎉 You're Ready!

Your Discord AI bot is now production-ready with:
- ✅ All commands using `!` prefix
- ✅ Image model selection menu
- ✅ Image analysis support
- ✅ Error handling
- ✅ Health monitoring
- ✅ Clean codebase

Invite your bot and start chatting! 🚀
