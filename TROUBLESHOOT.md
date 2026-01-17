# Troubleshooting Discord Bot Offline

## Quick Checks

### 1. Check Render Logs
Go to your Render dashboard → Your service → Logs tab

Look for errors like:
- `DISCORD_BOT_TOKEN environment variable not set!` → Add token in environment
- `Privileged intent provided is not enabled` → Enable intents in Discord portal
- `Improper token has been passed` → Token is wrong/expired

### 2. Verify Environment Variables on Render

Required:
- `DISCORD_BOT_TOKEN` = Your Discord bot token
- `PORT` = 5000 (usually auto-set by Render)

Optional:
- `RENDER_EXTERNAL_URL` = Your Render URL (for keep-alive)

### 3. Verify Discord Bot Settings

Go to [Discord Developer Portal](https://discord.com/developers/applications):
1. Click your application → Bot
2. Check these are **ENABLED**:
   - ✅ **Message Content Intent**
   - ✅ **Server Members Intent**
3. If you just enabled them, **regenerate the token** and update it on Render

### 4. Check Dockerfile Configuration on Render

In Render settings:
- **Dockerfile Path**: Should be `Dockerfile.bot`
- **Docker Command**: Leave empty (uses CMD from Dockerfile)

### 5. Common Issues & Fixes

#### Issue: "Bot user is None"
- Token not set or wrong
- Go to Render → Environment → Add `DISCORD_BOT_TOKEN`

#### Issue: "Intents Error"
- Enable Message Content Intent in Discord portal
- Wait 5 minutes for changes to propagate
- Redeploy on Render

#### Issue: Service keeps restarting
- Check if Dockerfile.bot exists
- Verify requirements.txt has correct versions
- Check Render logs for Python errors

#### Issue: Bot shows online but doesn't respond
- Verify bot is in your Discord server
- Check bot has proper permissions in server
- Test with `!ping` command

### 6. Manual Testing

Test if your API is responding:

```bash
# Test health endpoint
curl https://your-service.onrender.com/health

# Should return: {"bot_ready":true,"status":"healthy"}
```

If `bot_ready: false`, bot isn't connecting to Discord.

### 7. Verify Bot Invite

Make sure bot was invited with correct permissions:
1. Discord Developer Portal → OAuth2 → URL Generator
2. Select:
   - **Scopes**: `bot`
   - **Permissions**: 
     - Send Messages
     - Read Messages/View Channels
     - Embed Links
     - Attach Files
3. Use generated URL to re-invite bot if needed

### 8. Check g4f Compatibility

If bot starts but crashes when responding:
- g4f version might be incompatible
- Check Render logs for g4f errors
- Try pinning to stable version in requirements.txt

### 9. Force Redeploy

Sometimes Render needs a manual redeploy:
1. Go to your service on Render
2. Click "Manual Deploy" → "Deploy latest commit"
3. Wait 5-10 minutes

### 10. Test Locally (If Possible)

```bash
# Install dependencies
pip install -r requirements.txt

# Set token
$env:DISCORD_BOT_TOKEN="your_token_here"

# Run bot
python discord_bot.py
```

If it works locally but not on Render, it's likely an environment variable issue.

## Quick Fix Checklist

- [ ] Discord bot token is set in Render environment variables
- [ ] Message Content Intent is enabled in Discord portal  
- [ ] Dockerfile.bot exists and is specified in Render settings
- [ ] Bot is invited to your Discord server
- [ ] requirements.txt has g4f==6.9.3
- [ ] Render logs don't show errors
- [ ] `/health` endpoint returns `bot_ready: true`

## Still Not Working?

Share your Render logs (hide any tokens!) to diagnose further.
