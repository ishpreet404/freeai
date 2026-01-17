# Discord AI Bot (No n8n Required!)

A standalone Discord bot powered by g4f (gpt4free) for free AI chat and image generation.

## Features

- 💬 **AI Chat**: Natural conversations with GPT-4
- 🎨 **Image Generation**: Create images with `/imagine` command
- 📝 **Conversation Memory**: Maintains context for each user
- ⚡ **Commands**: Built-in utility commands

## Quick Setup

### 1. Create Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" → Name it
3. Go to "Bot" section:
   - Click "Add Bot"
   - Copy the **Bot Token** ⚠️ Keep this secret!
   - Enable these Privileged Gateway Intents:
     - ✅ Message Content Intent
     - ✅ Server Members Intent
4. Go to "OAuth2" → "URL Generator":
   - **Scopes**: Select `bot`
   - **Bot Permissions**: 
     - Send Messages
     - Read Messages/View Channels
     - Embed Links
     - Attach Files
   - Copy the URL and invite bot to your server

### 2. Deploy to Render

1. Go to [render.com](https://render.com) and sign up
2. Click "New +" → "Web Service"
3. Connect your GitHub repository
4. Configure:
   - **Name**: `discord-ai-bot`
   - **Environment**: `Docker`
   - **Dockerfile Path**: `Dockerfile.bot`
   - **Instance Type**: `Free`
5. Add Environment Variable:
   - **Key**: `DISCORD_BOT_TOKEN`
   - **Value**: Your bot token from step 1
6. Click "Create Web Service"
7. Wait 5-10 minutes for deployment

### Alternative: Deploy to Railway

1. Go to [railway.app](https://railway.app)
2. Click "New Project" → "Deploy from GitHub"
3. Select your repository
4. Add environment variable:
   - `DISCORD_BOT_TOKEN` = your bot token
5. In Settings → Change Dockerfile to `Dockerfile.bot`
6. Deploy!

## How to Use

### Chat with AI
Just type any message in a channel where the bot has access:

```
You: What's the weather like on Mars?
Bot: Mars has a cold, thin atmosphere...
```

The bot remembers your last 10 messages for context!

### Generate Images
Use the `/imagine` command:

```
/imagine a cyberpunk city at night
```

The bot will generate and send the image as an embed.

### Commands

- `!help` - Show all available commands
- `!clear` - Clear your conversation history
- `!ping` - Check bot latency

## Project Files

- `discord_bot.py` - Main bot code
- `Dockerfile.bot` - Docker config for bot
- `requirements.txt` - Python dependencies
- `app.py` - Optional Flask API (if you want both)

## Technical Details

### How it Works

1. Bot listens to Discord messages
2. Regular messages → Sends to g4f for AI response
3. `/imagine` messages → Generates image via g4f
4. Responses sent back to Discord

### Conversation Memory

- Each user gets their own conversation history
- Stores last 10 messages per user
- Resets when bot restarts (or use `!clear`)
- For persistent memory, add a database (Redis/PostgreSQL)

## Troubleshooting

### Bot is offline
- Check Render/Railway logs for errors
- Verify `DISCORD_BOT_TOKEN` is set correctly
- Make sure bot is invited to your server

### Bot doesn't respond
- Verify Message Content Intent is enabled
- Check bot has permission to read/send messages
- Look at deployment logs for errors

### Image generation fails
- g4f image providers can be unstable
- Try different prompts
- Some providers have rate limits

### Bot is slow
- Free hosting can have cold starts (30s delay)
- g4f depends on free providers which vary in speed
- Consider paid hosting for faster response

## Upgrading to Persistent Memory

To add persistent conversation history, you can:

1. Add PostgreSQL database (Render/Railway offer free tier)
2. Use Redis for caching (Upstash has free tier)
3. Store history in JSON files (mount a volume)

## Costs

- **Discord Bot**: Free
- **g4f**: Free (reverse-engineered APIs)
- **Hosting**:
  - Render: Free tier (sleeps after 15min inactivity)
  - Railway: $5/month free credit
  - Fly.io: Free tier available

## Security Notes

- Never commit your bot token to GitHub
- Use environment variables for secrets
- Enable only necessary bot permissions
- Consider rate limiting for production

## Advanced Features

Want to add more? You can:
- Add moderation commands
- Integrate with databases for persistence
- Add custom slash commands
- Create AI-powered games
- Add voice channel support

## Support

If issues persist:
1. Check bot logs in hosting dashboard
2. Test bot token is valid
3. Verify Discord permissions
4. Check g4f GitHub for provider updates

## Development

To run locally (for testing):

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variable
$env:DISCORD_BOT_TOKEN="your_token_here"

# Run bot
python discord_bot.py
```

---

**Note**: g4f uses reverse-engineered APIs which can be unstable. For production apps, consider using official API keys (OpenAI, Anthropic, etc.)
