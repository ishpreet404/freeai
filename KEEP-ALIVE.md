# Keep Render Instance Awake

This guide shows multiple methods to keep your Discord bot running 24/7 on Render's free tier.

## Method 1: Built-in Self-Ping (Already Implemented!)

The bot now includes a self-ping mechanism that keeps it awake.

### Setup on Render:

1. After deploying, go to your service settings
2. Add environment variable:
   - **Key**: `RENDER_EXTERNAL_URL`
   - **Value**: `https://your-service-name.onrender.com` (your Render URL)
3. Redeploy

The bot will ping itself every 10 minutes!

## Method 2: UptimeRobot (Recommended - 100% Free)

[UptimeRobot](https://uptimerobot.com) will ping your bot every 5 minutes.

### Setup:

1. Sign up at [uptimerobot.com](https://uptimerobot.com) (free)
2. Click "Add New Monitor"
3. Configure:
   - **Monitor Type**: HTTP(s)
   - **Friendly Name**: Discord Bot
   - **URL**: `https://your-service.onrender.com/health`
   - **Monitoring Interval**: 5 minutes
4. Click "Create Monitor"

Done! Your bot stays awake 24/7.

## Method 3: Cron-Job.org

Free alternative to UptimeRobot.

1. Go to [cron-job.org](https://cron-job.org)
2. Sign up (free)
3. Create new cronjob:
   - **URL**: `https://your-service.onrender.com/health`
   - **Interval**: Every 10 minutes
4. Save

## Method 4: GitHub Actions (Free)

Create a GitHub Action to ping your bot.

Create `.github/workflows/keep-alive.yml`:

```yaml
name: Keep Alive

on:
  schedule:
    - cron: '*/10 * * * *'  # Every 10 minutes
  workflow_dispatch:

jobs:
  keep-alive:
    runs-on: ubuntu-latest
    steps:
      - name: Ping service
        run: curl https://your-service.onrender.com/health
```

## Method 5: Upgrade to Paid (No Workarounds Needed)

Render paid plans ($7/month) don't sleep:
- No spin-down
- Better performance
- More resources

## Comparison

| Method | Cost | Reliability | Setup |
|--------|------|-------------|-------|
| Self-Ping | Free | Good | Easy |
| UptimeRobot | Free | Excellent | Easy |
| Cron-Job.org | Free | Good | Easy |
| GitHub Actions | Free | Good | Medium |
| Paid Plan | $7/mo | Excellent | Easy |

## Recommendation

**Best Free Solution**: UptimeRobot + Built-in Self-Ping

1. The bot pings itself every 10 min
2. UptimeRobot pings every 5 min as backup
3. 100% uptime on free tier!

## Important Notes

### Render Free Tier Limits:
- 750 hours/month (enough for 24/7 if you have 1 service)
- If you have multiple free services, they share the 750 hours
- Solution: Use paid tier or multiple accounts (violates ToS)

### Cold Start Behavior:
- Even with pings, Render may briefly spin down during deployments
- First request after spin-down takes ~30 seconds
- This is normal for free tier

### Better Free Alternatives:

If Render's limits are too restrictive:

1. **Railway** - $5 free credit/month (no sleep!)
2. **Fly.io** - Free tier, 3 small VMs
3. **Koyeb** - Free tier with no sleep
4. **Cyclic** - Serverless, always on (for Node.js)

## Testing

Test if your bot stays awake:

```bash
# Ping health endpoint
curl https://your-service.onrender.com/health

# Should return: {"status": "healthy", "bot_ready": true}
```

Check UptimeRobot dashboard after 30 minutes - should show 100% uptime!
