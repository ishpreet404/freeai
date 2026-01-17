# 🎵 YouTube Music Player Guide

## 🎸 New Music Features

Your Discord bot now has a **full-featured YouTube music player** with queue system and beautiful embeds!

### ✅ What's Added
- **YouTube Search**: Play songs by name or URL
- **Queue System**: Add multiple songs with automatic playback
- **Playback Controls**: Pause, resume, skip, stop
- **Beautiful UI**: Rich embeds with thumbnails and song info
- **100% Free**: Uses yt-dlp (no YouTube API key needed)

## 🎮 Music Commands

### Play Music
```bash
!play Imagine Dragons Believer          # Search by name
!play https://youtube.com/watch?v=...   # Direct URL
```

### Playback Controls
```bash
!pause          # Pause current song
!resume         # Resume paused song
!skip           # Skip to next song
!stop           # Stop music and clear queue
```

### Queue Management
```bash
!queue          # Show all songs in queue
!nowplaying     # Show current song (alias: !np)
```

### Voice Controls
```bash
!disconnect     # Leave voice channel (alias: !dc)
```

## 💎 Beautiful Chat Interface

### Now Playing Embed
When a song starts playing:
```
┌─────────────────────────────┐
│ 🎵 Now Playing              │
├─────────────────────────────┤
│ Imagine Dragons - Believer  │
│                             │
│ Duration: 3:24              │
│ Requested by: @User         │
│ Songs in queue: 5           │
│                             │
│ [Thumbnail Image]           │
└─────────────────────────────┘
```

### Added to Queue Embed
When adding a song:
```
┌─────────────────────────────┐
│ ➕ Added to Queue           │
├─────────────────────────────┤
│ Song Title Here             │
│                             │
│ Position: #3                │
│ Duration: 4:15              │
│                             │
│ [Thumbnail Image]           │
└─────────────────────────────┘
```

### Queue Display
```
┌─────────────────────────────┐
│ 🎵 Music Queue              │
├─────────────────────────────┤
│ 🎶 Now Playing              │
│ Current Song - 3:24         │
│ Requested by @User          │
│                             │
│ 📋 Up Next                  │
│ 1. Song Title - 4:15        │
│ 2. Another Song - 3:30      │
│ 3. More Music - 5:00        │
│                             │
│ Total songs in queue: 10    │
└─────────────────────────────┘
```

## 📖 Usage Examples

### Example 1: Simple Playback
```
User: !play Despacito
Bot: ➕ Added to Queue
     Despacito - Luis Fonsi
     Position: #1
     Duration: 3:48

[After a moment]
Bot: 🎵 Now Playing
     Despacito - Luis Fonsi
     Duration: 3:48
     Requested by @User
```

### Example 2: Building a Queue
```
User: !play Believer
Bot: 🎵 Now Playing [Believer...]

User: !play Thunder
Bot: ➕ Added to Queue [Thunder...] Position: #1

User: !play Radioactive
Bot: ➕ Added to Queue [Radioactive...] Position: #2

User: !queue
Bot: [Shows full queue with 3 songs]
```

### Example 3: Playback Control
```
User: !pause
Bot: ⏸️ Paused music

User: !resume
Bot: ▶️ Resumed music

User: !skip
Bot: ⏭️ Skipped song
     🎵 Now Playing [Next Song...]
```

## 🎯 Features Breakdown

### Smart Search
- **By Name**: `!play shape of you` - Searches YouTube automatically
- **By URL**: `!play https://youtube.com/watch?v=...` - Direct link
- **Auto-Queue**: Songs play automatically one after another

### Queue System
- **Unlimited Queue**: Add as many songs as you want
- **FIFO Order**: First In, First Out
- **Auto-Advance**: Automatically plays next song
- **Clear Queue**: Use `!stop` to clear everything

### Rich Embeds
- **Thumbnails**: Shows video thumbnail
- **Song Info**: Title, duration, requester
- **Queue Status**: Shows position and total songs
- **Color Coded**: Green for playing, blue for queued, purple for queue list

### Voice Integration
- **Auto-Join**: Bot joins your voice channel automatically
- **Persistent**: Stays in channel while queue has songs
- **Clean Exit**: Use `!disconnect` or `!dc` to leave

## 🔧 Technical Details

### YouTube Downloader
- **Library**: yt-dlp (most reliable YouTube downloader)
- **No API Key**: Doesn't use YouTube API (no quota limits)
- **Format**: Best audio quality (bestaudio)
- **Search**: Built-in YouTube search

### Audio Streaming
- **FFmpeg**: Streams audio without downloading full file
- **Low Latency**: Starts playing quickly
- **Reconnect**: Handles network issues automatically

### Memory Efficient
- **Queue Storage**: Only metadata (no audio files)
- **Streaming**: No disk usage for audio
- **Clean Up**: Auto-cleanup after playback

## 📊 Resource Usage (Render Free Tier)

| Component | Memory | CPU | Notes |
|-----------|--------|-----|-------|
| yt-dlp | ~10MB | Low | Metadata extraction |
| FFmpeg Streaming | ~15MB | Medium | Per voice connection |
| Queue System | ~1MB | Minimal | Metadata only |
| **Total Impact** | ~26MB | Med | Well within free tier |

## 💡 Tips & Tricks

1. **Faster Search**: Use specific song names: `!play believer imagine dragons`
2. **Playlist URLs**: Bot extracts first video (playlist support can be added)
3. **Check Queue**: Use `!queue` to see what's coming up
4. **Quick Stop**: `!dc` stops and leaves immediately
5. **Alias Commands**: `!np` instead of `!nowplaying`, `!dc` instead of `!disconnect`

## 🎨 Embed Colors

- 🟢 **Green**: Now Playing
- 🔵 **Blue**: Added to Queue
- 🟣 **Purple**: Queue List

## ⚠️ Limitations

### Free Tier Considerations
1. **Concurrent Streams**: Best with 1-2 voice connections
2. **Queue Size**: No hard limit, but keep reasonable (<50 songs)
3. **Long Videos**: Very long videos (>1 hour) may use more memory

### YouTube Limitations
1. **Age-Restricted**: Cannot play age-restricted videos
2. **Private Videos**: Cannot access private videos
3. **Geo-Blocked**: Some videos may be blocked in certain regions

## 🐛 Troubleshooting

### Music won't play
- Verify FFmpeg is installed (included in Docker)
- Check bot has "Connect" and "Speak" permissions
- Ensure you're in a voice channel

### Search not working
- Try using full song name with artist
- Or use direct YouTube URL
- Check internet connection on server

### Audio quality issues
- May depend on YouTube source quality
- Bot always requests best audio available

### Queue not advancing
- Check bot is still connected to voice
- View logs for any errors
- Try `!stop` and replay

## 🚀 Advanced Usage

### Commands Chaining
```bash
# Join and play immediately
User: !play song name
# (Bot auto-joins and plays)

# Add multiple songs
!play song1
!play song2
!play song3
# (Builds queue automatically)

# Manage playback
!pause
!skip
!nowplaying
```

### Aliases
```bash
!nowplaying = !np
!disconnect = !dc
```

## 🎊 Updated Help Menu

The `!bothelp` command now includes a complete music section:
```
🎵 Music Commands
!play <url/query> - Play music from YouTube
!pause - Pause music
!resume - Resume music
!skip - Skip current song
!stop - Stop and clear queue
!queue - Show music queue
!nowplaying or !np - Show current song
!disconnect or !dc - Leave voice
```

## 📦 Dependencies Added

```
yt-dlp==2024.12.13    # YouTube downloader (no API needed)
```

Already have:
```
discord.py==2.3.2     # Voice support
PyNaCl==1.5.0         # Voice encryption
FFmpeg                # Audio processing (in Docker)
```

## 🎉 Production Ready

All music features are:
- ✅ Fully implemented
- ✅ Error handled
- ✅ Free tier compatible
- ✅ Beautiful UI
- ✅ No API keys needed
- ✅ Queue system
- ✅ Auto-advance
- ✅ Rich embeds

## 🔍 About g4f and YouTube

**Note**: g4f (gpt4free) is for AI chat and image generation only. It does **not** provide YouTube support. 

For YouTube functionality, we're using:
- **yt-dlp**: YouTube video/audio extraction
- **FFmpeg**: Audio streaming
- **discord.py**: Voice channel integration

All completely free and Render-compatible! 🚀

---

**Enjoy your feature-rich music bot! 🎵**
