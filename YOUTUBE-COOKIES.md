# 🍪 YouTube Cookies Setup Guide

## Why Use Cookies?

YouTube cookies will **completely bypass bot detection**, allowing you to play any video without restrictions.

## 📋 How to Export YouTube Cookies

### Method 1: Using Browser Extension (Easiest)

1. **Install Cookie Editor Extension:**
   - Chrome: [Cookie Editor](https://chrome.google.com/webstore/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm)
   - Firefox: [Cookie Editor](https://addons.mozilla.org/en-US/firefox/addon/cookie-editor/)

2. **Export Cookies:**
   - Go to `youtube.com` and make sure you're logged in
   - Click the Cookie Editor extension icon
   - Click "Export" → Choose "Netscape" format
   - Save as `youtube_cookies.txt`

3. **Place in Bot Directory:**
   ```
   freeaidc/
   ├── discord_bot.py
   ├── youtube_cookies.txt  ← Put it here!
   └── ...
   ```

### Method 2: Using yt-dlp (Command Line)

```bash
# Export cookies from Chrome
yt-dlp --cookies-from-browser chrome --cookies youtube_cookies.txt "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# Or from Firefox
yt-dlp --cookies-from-browser firefox --cookies youtube_cookies.txt "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# Or from Edge
yt-dlp --cookies-from-browser edge --cookies youtube_cookies.txt "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

### Method 3: Manual Cookie Export (Chrome)

1. Open Chrome DevTools (F12)
2. Go to YouTube.com (logged in)
3. Go to "Application" tab → "Cookies" → "https://www.youtube.com"
4. Right-click → "Copy All"
5. Use an online converter to convert to Netscape format
6. Save as `youtube_cookies.txt`

## 📝 Cookie File Format

The file should look like this (Netscape format):
```
# Netscape HTTP Cookie File
.youtube.com	TRUE	/	TRUE	1234567890	CONSENT	YES+
.youtube.com	TRUE	/	FALSE	1234567890	VISITOR_INFO1_LIVE	xxxxx
.youtube.com	TRUE	/	TRUE	1234567890	LOGIN_INFO	xxxxx
```

## 🚀 Using Cookies with the Bot

### 1. Place Cookie File

Put `youtube_cookies.txt` in the same directory as `discord_bot.py`:

```
d:\freeaidc\
├── discord_bot.py
├── youtube_cookies.txt  ← Here!
├── requirements.txt
└── ...
```

### 2. Restart Bot

The bot will automatically detect and use the cookies file:

```powershell
python discord_bot.py
```

You'll see in logs:
```
INFO - Found YouTube cookies file: youtube_cookies.txt
```

### 3. Test Music Command

```
!play any youtube video
```

Should work without bot detection errors!

## 🐳 Docker Deployment with Cookies

### Update Dockerfile.bot

Add this line before `CMD`:

```dockerfile
# Copy cookies file if it exists
COPY youtube_cookies.txt* /app/ || true
```

### Or Mount as Volume

```bash
docker run -d \
  -e DISCORD_BOT_TOKEN=your_token \
  -v $(pwd)/youtube_cookies.txt:/app/youtube_cookies.txt \
  discord-ai-bot
```

## ☁️ Render Deployment with Cookies

### Option 1: Include in Repository

1. Add `youtube_cookies.txt` to your repo
2. **⚠️ WARNING**: This exposes your YouTube session. Use a throwaway account!

### Option 2: Environment Variable (Not Recommended)

Cookies are too large for environment variables. Not recommended.

### Option 3: Use Secret File (Best for Render)

1. Go to Render dashboard
2. Your Web Service → "Environment" tab
3. Add "Secret File":
   - **Filename**: `youtube_cookies.txt`
   - **Contents**: Paste your cookie file contents
4. Deploy

## 🔒 Security Considerations

### ⚠️ Important Warnings

1. **Your Account Access**: Cookies give full YouTube access to your account
2. **Use Throwaway Account**: Don't use your personal YouTube account
3. **Cookie Expiry**: Cookies expire after ~6 months, need to refresh
4. **Don't Share**: Never share your cookies file publicly

### 🛡️ Best Practices

1. ✅ Create a separate Google/YouTube account just for the bot
2. ✅ Add `youtube_cookies.txt` to `.gitignore` if not using throwaway account
3. ✅ Refresh cookies every few months
4. ✅ Revoke access if cookies are exposed

### Add to .gitignore

```bash
echo "youtube_cookies.txt" >> .gitignore
```

## 🔄 Updating Cookies

Cookies expire eventually. When you see bot detection errors again:

1. Export fresh cookies (follow methods above)
2. Replace `youtube_cookies.txt`
3. Restart bot

## ✅ Verification

After adding cookies, test with a video that was previously blocked:

```
!play restricted video
```

Should work perfectly now! 🎵

## 🐛 Troubleshooting

### Bot still getting blocked

- ✅ Check cookie file format (must be Netscape format)
- ✅ Ensure you're logged into YouTube when exporting
- ✅ Verify file is named exactly `youtube_cookies.txt`
- ✅ Check file is in same directory as `discord_bot.py`
- ✅ Restart the bot

### Cookie file not detected

Check bot logs for:
```
INFO - Found YouTube cookies file: youtube_cookies.txt
```

If not showing, file is in wrong location or wrong name.

### Cookies expired

Export fresh cookies and replace the file.

## 📚 Additional Resources

- [yt-dlp Cookie FAQ](https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp)
- [Exporting YouTube Cookies Guide](https://github.com/yt-dlp/yt-dlp/wiki/Extractors#exporting-youtube-cookies)

---

**With cookies, your bot will have zero YouTube restrictions! 🎉**
