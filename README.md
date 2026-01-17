# Discord AI Bot with g4f - Deployment Guide

This project provides a Discord bot using n8n that leverages g4f (gpt4free) for AI chat and image generation capabilities.

## Project Structure

- `app.py` - Flask API server that wraps g4f functionality
- `requirements.txt` - Python dependencies
- `Dockerfile` - Docker configuration for deployment
- `n8n-discord-bot-workflow.json` - n8n workflow to import

## Part 1: Deploy the g4f API Server

You need to deploy the Python API server to a hosting service. Here are free options:

### Option A: Deploy to Render (Recommended - Free Tier Available)

1. Create account at [render.com](https://render.com)
2. Click "New +" → "Web Service"
3. Connect your GitHub repository or use "Deploy from Docker"
4. Configure:
   - **Name**: `g4f-api` (or your choice)
   - **Environment**: `Docker`
   - **Region**: Choose closest to you
   - **Branch**: `main`
   - **Instance Type**: `Free`
5. Click "Create Web Service"
6. Wait for deployment (5-10 minutes)
7. Copy your API URL (e.g., `https://g4f-api-xxxx.onrender.com`)

### Option B: Deploy to Railway

1. Create account at [railway.app](https://railway.app)
2. Click "New Project" → "Deploy from GitHub repo"
3. Select your repository
4. Railway will auto-detect the Dockerfile
5. Wait for deployment
6. Copy your API URL from the deployment settings

### Option C: Deploy to Fly.io

```bash
# Install flyctl
# Windows (PowerShell)
iwr https://fly.io/install.ps1 -useb | iex

# Login
fly auth login

# Deploy (run from project folder)
fly launch
fly deploy
```

## Part 2: Set Up Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" → Give it a name
3. Go to "Bot" section:
   - Click "Add Bot"
   - Copy the **Bot Token** (you'll need this for n8n)
   - Enable these Privileged Gateway Intents:
     - ✅ Message Content Intent
     - ✅ Server Members Intent
4. Go to "OAuth2" → "URL Generator":
   - Scopes: `bot`
   - Bot Permissions: 
     - Send Messages
     - Read Messages/View Channels
     - Send Messages in Threads
     - Embed Links
     - Attach Files
5. Copy the generated URL and open it to invite bot to your server

## Part 3: Configure n8n Workflow

1. Log into your hosted n8n instance
2. Click on "Workflows" → "Import from File"
3. Upload `n8n-discord-bot-workflow.json`
4. Configure the workflow:

### Step 1: Add Discord Bot Credentials
- Click on any Discord node
- Click "Create New Credential"
- Paste your Discord Bot Token
- Save

### Step 2: Update API URLs
You need to replace `YOUR_API_URL` in two nodes:
- **Generate Image** node: Change URL to `https://your-api-url.com/image`
- **Generate Chat Response** node: Change URL to `https://your-api-url.com/chat`

### Step 3: Activate Workflow
- Click "Active" toggle at top right
- Your bot is now live!

## How to Use the Bot

### Chat (LLM)
Just type any message in Discord:
```
User: What is the capital of France?
Bot: The capital of France is Paris.
```

### Image Generation
Use the `/imagine` command:
```
User: /imagine a beautiful sunset over mountains
Bot: [Returns generated image]
```

## API Endpoints

Your deployed API has these endpoints:

### `GET /`
Health check and service info

### `POST /chat`
Generate text responses
```json
{
  "message": "Your question here",
  "model": "gpt-4",
  "conversation_history": []
}
```

### `POST /image`
Generate images
```json
{
  "prompt": "Your image description"
}
```

### `GET /providers`
List available g4f providers

## Troubleshooting

### Bot not responding
1. Check n8n workflow is **Active**
2. Verify Discord bot has proper permissions in your server
3. Check API server is running (visit its URL, should show status page)
4. Check n8n execution logs for errors

### Image generation not working
- g4f image providers can be unstable
- Try different prompts
- Check API logs

### API timing out
- Some providers are slower than others
- Render free tier spins down after inactivity (takes ~30s to wake up)
- Consider upgrading to paid tier if needed

## Advanced Configuration

### Change AI Model
In the n8n workflow, edit the "Generate Chat Response" node:
- Change `model` parameter to: `gpt-3.5-turbo`, `claude-3`, `gemini-pro`, etc.

### Add Conversation Memory
You can store conversation history using n8n's built-in memory nodes or a database to maintain context across messages.

### Rate Limiting
Add n8n's "Limit" node before the API calls to prevent spam.

## Cost

- **g4f API**: Free (uses reverse-engineered providers)
- **n8n**: Your existing hosted instance
- **Discord Bot**: Free
- **Hosting**: 
  - Render: Free tier available (spins down after 15min inactivity)
  - Railway: $5 credit/month on free tier
  - Fly.io: Free tier available

## Notes

- g4f providers can be unstable and change frequently
- Free hosting services may have cold start delays
- For production use, consider paid hosting for better reliability
- Respect rate limits and terms of service

## Support

If you encounter issues:
1. Check API health endpoint: `https://your-api-url.com/health`
2. Review n8n execution logs
3. Check g4f GitHub for provider status updates
