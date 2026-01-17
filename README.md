# 🤖 Free AI Discord Bot

A powerful Discord bot with AI chat, image generation, image analysis, voice features, and YouTube music player - all using free APIs!

## ✨ Features

- 💬 **AI Chat** - GPT-4 powered conversations
- 🖼️ **Image Generation** - 6 different AI models
- 📸 **Image Analysis** - Upload images for AI analysis
- 🎙️ **Text-to-Speech** - Indian female voice
- 📝 **Speech-to-Text** - Transcribe audio files
- 🎵 **YouTube Music Player** - Full-featured with queue system

## 🚀 Quick Start

### Requirements
- Python 3.9+
- Discord Bot Token
- FFmpeg (included in Docker)

### Installation

1. **Clone repository**
```bash
git clone <your-repo>
cd freeaidc
```

2. **Set environment variables**
```bash
# Windows PowerShell
$env:DISCORD_BOT_TOKEN="your_discord_bot_token"

# Linux/Mac
export DISCORD_BOT_TOKEN="your_discord_bot_token"
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Run bot**
```bash
python discord_bot.py
```

### Docker Deployment

```bash
# Build
docker build -f Dockerfile.bot -t discord-ai-bot .

# Run
docker run -e DISCORD_BOT_TOKEN=your_token discord-ai-bot
```

### Deploy to Render

1. Create Web Service on Render
2. Connect your repository
3. Set environment variable: `DISCORD_BOT_TOKEN`
4. Deploy automatically!

## 📋 All Commands

### 💬 Chat Commands

| Command | Description | Example |
|---------|-------------|---------|
| `?<message>` | Chat with AI (maintains context) | `?What is Python?` |
| `!ask <question>` | Ask AI a one-time question | `!ask Explain quantum physics` |
| `!clear` | Clear your conversation history | `!clear` |

### 🖼️ Image Commands

| Command | Description | Example |
|---------|-------------|---------|
| `!imagine <prompt>` | Generate an image | `!imagine a sunset over mountains` |
| `!listimagemodels` | Show available image models | `!listimagemodels` |
| `!setimagemodel <model>` | Set image model (Admin) | `!setimagemodel flux-pro` |
| Upload image + text | Analyze an image | Upload image + `What's in this?` |

**Available Image Models:**
- `flux` - Fast & Quality (Default)
- `flux-pro` - Higher Quality
- `flux-realism` - Photorealistic
- `dalle` - DALL-E
- `sdxl` - Stable Diffusion XL
- `playground-v2.5` - Playground v2.5

### 🎙️ Voice Commands

| Command | Description | Example |
|---------|-------------|---------|
| `!speak <text>` | Text-to-speech (Indian voice) | `!speak Hello everyone` |
| `!transcribe` | Transcribe audio attachment | Upload audio + `!transcribe` |
| `!join` | Join your voice channel | `!join` |
| `!leave` | Leave voice channel | `!leave` |

### 🎵 Music Commands

| Command | Description | Example |
|---------|-------------|---------|
| `!play <url/query>` | Play music from YouTube | `!play Imagine Dragons Believer` |
| `!search <query>` or `!ytsearch` | Search YouTube (shows top 5) | `!search Believer` |
| `!pause` | Pause current song | `!pause` |
| `!resume` | Resume paused song | `!resume` |
| `!skip` | Skip to next song | `!skip` |
| `!stop` | Stop and clear queue | `!stop` |
| `!queue` | Show music queue | `!queue` |
| `!nowplaying` or `!np` | Show current song | `!np` |
| `!disconnect` or `!dc` | Leave voice channel | `!dc` |

### 👑 Admin Commands (Requires Manage Channels)

| Command | Description | Example |
|---------|-------------|---------|
| `!setchannel` | Enable bot in current channel | `!setchannel` |
| `!removechannel` | Disable bot in current channel | `!removechannel` |
| `!listchannels` | List active channels | `!listchannels` |
| `!clearallchannels` | Remove all channel restrictions | `!clearallchannels` |
| `!setimagemodel <model>` | Set image generation model | `!setimagemodel flux-pro` |

### 🔧 Utility Commands

| Command | Description | Example |
|---------|-------------|---------|
| `!ping` | Check bot latency | `!ping` |
| `!bothelp` | Show help message | `!bothelp` |

## 🎯 Usage Examples

### Chat with AI
```
User: ?Tell me a joke
Bot: Why did the programmer quit his job? Because he didn't get arrays!

User: ?That's funny!
Bot: I'm glad you enjoyed it! Would you like to hear another one?
```

### Generate Images
```
User: !imagine a cat wearing a crown, digital art
Bot: 🎨 Generating image with Flux (Default - Fast & Quality)...
     [Beautiful image appears]
```

### Play Music
```
User: !play Believer
Bot: 🎵 Now Playing
     Imagine Dragons - Believer
     Duration: 3:24
     Requested by @User
```

### Voice Features
```
User: !speak Namaste! Kaise ho aap?
Bot: 🔊 Here's your audio: [speech.mp3]

User: !transcribe [uploads audio]
Bot: 📝 Transcription: Hello, this is a test message
```

## 🎨 Beautiful UI Features

### Rich Embeds
- 🖼️ Thumbnails for music and images
- 📊 Queue position display
- 👤 Requester mentions
- 🎨 Color-coded status

### Music Queue Display
```
🎵 Music Queue
━━━━━━━━━━━━━━━
🎶 Now Playing
Current Song - 3:24

📋 Up Next
1. Song Title - 4:15
2. Another Song - 3:30
3. More Music - 5:00

Total: 10 songs
```

## 🔑 Discord Bot Setup

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create New Application
3. Go to "Bot" section → Add Bot
4. **Enable Privileged Gateway Intents:**
   - ✅ Message Content Intent (CRITICAL!)
   - ✅ Server Members Intent
5. Copy Bot Token
6. Go to OAuth2 → URL Generator:
   - Scopes: `bot`
   - Permissions: 
     - Read Messages/View Channels
     - Send Messages
     - Embed Links
     - Attach Files
     - Connect (voice)
     - Speak (voice)
7. Invite bot to your server

## ⚙️ Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DISCORD_BOT_TOKEN` | Yes | Your Discord bot token |
| `PORT` | No | Port for health checks (default: 5000) |
| `RENDER_EXTERNAL_URL` | No | For keep-alive on Render |

## 🐳 Docker Configuration

The `Dockerfile.bot` includes:
- Python 3.11
- FFmpeg (for audio processing)
- All required Python packages
- Optimized for Render free tier

## 🔒 Security

- Never commit your bot token
- Use environment variables
- Add `.env` to `.gitignore`
- Restrict bot permissions to only what's needed

## 📊 Resource Usage (Render Free Tier)

| Feature | Memory | CPU | Disk |
|---------|--------|-----|------|
| Base Bot | ~50MB | Low | 0MB |
| Image Gen | ~5MB | Low | 0MB |
| TTS | ~5MB | Low | 0MB |
| Music Stream | ~15MB | Med | 0MB (streaming) |
| **Total** | ~75MB | Low-Med | 0MB |

✅ Well within Render's free tier limits!

## 🚨 Troubleshooting

### Commands not working
1. ✅ Enable **Message Content Intent** in Discord Developer Portal
2. ✅ Restart bot after code changes
3. ✅ Check bot has permissions in channel
4. ✅ Verify bot token is correct

### Music not playing
1. ✅ Check FFmpeg is installed
2. ✅ Bot needs "Connect" and "Speak" permissions
3. ✅ Join a voice channel first

### Image generation fails
1. ✅ Try different model: `!setimagemodel flux`
2. ✅ Free providers may have temporary outages

### Voice features not working
1. ✅ Verify FFmpeg is installed (included in Docker)
2. ✅ Check voice permissions
3. ✅ For transcription, use supported formats (mp3, wav, ogg, m4a)

## 🎯 Tips

1. **Chat Context**: Use `?` for conversations, `!ask` for single questions
2. **Clear History**: Use `!clear` if responses seem off-context
3. **Music Search**: Be specific: `!play believer imagine dragons`
4. **Image Quality**: Try different models for best results
5. **Voice Quality**: Use clear audio for better transcription

## 📦 Dependencies

- `discord.py` - Discord API wrapper
- `g4f` - Free AI chat and image generation
- `edge-tts` - Text-to-speech
- `yt-dlp` - YouTube downloader
- `SpeechRecognition` - Speech-to-text
- `pydub` - Audio processing
- `PyNaCl` - Voice encryption
- `FFmpeg` - Audio encoding/decoding

## 🎉 Features Summary

✅ AI Chat with GPT-4
✅ 6 Image generation models
✅ Image analysis with vision AI
✅ Text-to-speech (Indian voice)
✅ Speech-to-text transcription
✅ YouTube music player
✅ Queue system with auto-advance
✅ Rich embeds with thumbnails
✅ Channel restrictions
✅ Admin controls
✅ 100% Free APIs
✅ No API keys required
✅ Render free tier compatible
✅ Beautiful UI

## 📄 License

MIT License - Feel free to use and modify!

## 🤝 Contributing

Pull requests welcome! For major changes, please open an issue first.

## ⚠️ Disclaimer

This bot uses free APIs which may have rate limits or availability issues. For production use, consider official APIs with proper authentication.

---

**Made with ❤️ - Enjoy your all-in-one Discord bot! 🚀**
