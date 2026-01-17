# 🎮 Quick Command Reference

## 💬 Chat Commands

```
?hello                          Chat with AI (maintains context)
!ask What is Python?           Ask a question (one-time)
!clear                         Clear your chat history
```

## 🖼️ Image Commands

```
!imagine a beautiful sunset    Generate an image
!listimagemodels              List all available models
```

## 📸 Image Analysis

```
Upload image + type:
"What's in this image?"       Analyze uploaded image
```

## 🎙️ Voice Commands

```
!speak Hello everyone       Text-to-speech (Indian female voice)
!transcribe                Transcribe uploaded audio file
!join                      Join your voice channel
!leave                     Leave voice channel
!listen 10                 Listen for 10 seconds
```

## 🎵 Music Commands

```
!play <url or query>       Play music from YouTube
!pause                     Pause current song
!resume                    Resume paused song
!skip                      Skip to next song
!stop                      Stop and clear queue
!queue                     Show music queue
!nowplaying or !np         Show current song
!disconnect or !dc         Leave voice channel
```

## 🔧 Utility Commands

```
!ping                         Check bot latency
!bothelp                      Show full help menu
```

## 👑 Admin Commands (Requires: Manage Channels)

### Channel Management
```
!setchannel                   Enable bot in current channel
!removechannel                Disable bot in current channel
!listchannels                 Show all active channels
!clearallchannels             Remove all restrictions
```

### Image Model Selection
```
!setimagemodel flux           Set to Flux (default)
!setimagemodel flux-pro       Set to Flux Pro
!setimagemodel flux-realism   Set to Flux Realism
!setimagemodel dalle          Set to DALL-E
!setimagemodel sdxl           Set to Stable Diffusion XL
!setimagemodel playground-v2.5 Set to Playground
```

## 📋 Model Options

| Model | Description |
|-------|-------------|
| `flux` | Fast & Quality (Default) |
| `flux-pro` | Higher Quality |
| `flux-realism` | Photorealistic |
| `dalle` | DALL-E (OpenAI) |
| `sdxl` | Stable Diffusion XL |
| `playground-v2.5` | Playground v2.5 |

## 🎯 Usage Examples

### Basic Chat
```
User: ?Tell me a joke
Bot: [AI responds with a joke]

User: ?That was funny!
Bot: [AI continues the conversation]
```

### Image Generation
```
User: !imagine a cat wearing a crown, digital art
Bot: 🎨 Generating image with Flux (Default - Fast & Quality): a cat wearing a crown, digital art
     [Image appears]
```

### Image Analysis
```
User: [Uploads photo of a sunset]
      What colors do you see?
Bot: [Analyzes the image and describes colors]
```

### Admin Setup
```
Admin: !setchannel
Bot: ✅ Bot is now active in #general!

Admin: !setimagemodel flux-pro
Bot: ✅ Image generation model set to: Flux Pro (Higher Quality)
```

## ⚡ Tips

1. **Chat Context**: Use `?` for conversations, `!ask` for one-off questions
2. **Clear History**: Use `!clear` if bot responses seem off
3. **Channel Control**: Restrict bot to specific channels to avoid spam
4. **Model Selection**: Try different models if image quality isn't great
5. **Image Analysis**: Works with JPG, PNG, GIF, WEBP formats

## 🚨 Common Issues

| Issue | Solution |
|-------|----------|
| Bot not responding | Check `!listchannels` - may be restricted |
| Image gen fails | Try `!setimagemodel flux` |
| Commands ignored | Make sure you use `!` prefix |
| No admin access | Need "Manage Channels" permission |

## 📱 Mobile Quick Guide

```
Chat:    ?<message>
Ask:     !ask <question>
Image:   !imagine <prompt>
Help:    !bothelp
```

---

💡 **Pro Tip**: Type `!bothelp` in Discord to see this info anytime!
