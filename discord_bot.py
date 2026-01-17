import discord
from discord.ext import commands
import g4f
from g4f.client import Client
import os
import logging
import asyncio
from flask import Flask
from threading import Thread
import requests
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask app for health checks (keeps Render active)
app = Flask(__name__)

@app.route('/')
def home():
    return {
        'status': 'online',
        'bot': bot.user.name if bot.user else 'connecting',
        'guilds': len(bot.guilds),
        'latency': round(bot.latency * 1000) if bot.is_ready() else 0,
        'timestamp': datetime.utcnow().isoformat()
    }

@app.route('/health')
def health():
    return {'status': 'healthy', 'bot_ready': bot.is_ready()}

def run_flask():
    """Run Flask server in a separate thread"""
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

def start_flask():
    """Start Flask server in background"""
    thread = Thread(target=run_flask, daemon=True)
    thread.start()
    logger.info("Flask health server started")

# Initialize bot
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Initialize g4f client
g4f_client = Client()

# Store conversation history (in-memory, resets on restart)
conversation_history = {}

@bot.event
async def on_ready():
    logger.info(f'{bot.user} has connected to Discord!')
    logger.info(f'Bot is in {len(bot.guilds)} guilds')
    # Start the keep-alive task
    bot.loop.create_task(keep_alive())

async def keep_alive():
    """Self-ping to keep Render instance awake"""
    await bot.wait_until_ready()
    url = os.getenv('RENDER_EXTERNAL_URL')
    
    if not url:
        logger.warning("RENDER_EXTERNAL_URL not set, skip self-ping")
        return
    
    while not bot.is_closed():
        try:
            await asyncio.sleep(600)  # Ping every 10 minutes
            response = await asyncio.to_thread(requests.get, f"{url}/health", timeout=10)
            logger.info(f"Keep-alive ping: {response.status_code}")
        except Exception as e:
            logger.error(f"Keep-alive error: {e}")
            await asyncio.sleep(60)  # Wait 1 min on error

@bot.event
async def on_message(message):
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return
    
    # Process commands first
    await bot.process_commands(message)
    
    # If message starts with !, it's a command, so skip
    if message.content.startswith('!'):
        return
    
    # Handle /imagine for image generation
    if message.content.startswith('/imagine'):
        await handle_image_generation(message)
        return
    
    # Handle regular chat messages
    if message.content.strip():
        await handle_chat(message)

async def handle_chat(message):
    """Handle regular chat messages with AI"""
    try:
        # Show typing indicator
        async with message.channel.typing():
            user_id = str(message.author.id)
            
            # Get or create conversation history for this user
            if user_id not in conversation_history:
                conversation_history[user_id] = []
            
            # Add user message to history
            conversation_history[user_id].append({
                "role": "user",
                "content": message.content
            })
            
            # Keep only last 10 messages to avoid token limits
            if len(conversation_history[user_id]) > 10:
                conversation_history[user_id] = conversation_history[user_id][-10:]
            
            # Generate response using g4f
            response = await asyncio.to_thread(
                g4f_client.chat.completions.create,
                model="gpt-4",
                messages=conversation_history[user_id]
            )
            
            ai_response = response.choices[0].message.content
            
            # Add AI response to history
            conversation_history[user_id].append({
                "role": "assistant",
                "content": ai_response
            })
            
            # Split long messages (Discord has 2000 char limit)
            if len(ai_response) > 2000:
                chunks = [ai_response[i:i+2000] for i in range(0, len(ai_response), 2000)]
                for chunk in chunks:
                    await message.reply(chunk)
            else:
                await message.reply(ai_response)
                
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        await message.reply(f"Sorry, I encountered an error: {str(e)}")

async def handle_image_generation(message):
    """Handle image generation with /imagine command"""
    try:
        # Extract prompt
        prompt = message.content.replace('/imagine', '').strip()
        
        if not prompt:
            await message.reply("Please provide a prompt! Example: `/imagine a beautiful sunset`")
            return
        
        # Show typing indicator
        async with message.channel.typing():
            await message.reply(f"🎨 Generating image: *{prompt}*\nThis may take a moment...")
            
            # Generate image using g4f
            response = await asyncio.to_thread(
                g4f_client.images.generate,
                model="flux",
                prompt=prompt
            )
            
            # Get image URL
            if response.data and len(response.data) > 0:
                image_url = response.data[0].url if hasattr(response.data[0], 'url') else None
                
                if image_url:
                    # Create embed with image
                    embed = discord.Embed(
                        title="Generated Image",
                        description=prompt,
                        color=discord.Color.blue()
                    )
                    embed.set_image(url=image_url)
                    embed.set_footer(text=f"Requested by {message.author.display_name}")
                    
                    await message.channel.send(embed=embed)
                else:
                    await message.reply("Failed to generate image. Please try again.")
            else:
                await message.reply("Failed to generate image. Please try again.")
                
    except Exception as e:
        logger.error(f"Image generation error: {str(e)}")
        await message.reply(f"Sorry, I couldn't generate that image: {str(e)}")

@bot.command(name='clear')
async def clear_history(ctx):
    """Clear conversation history for the user"""
    user_id = str(ctx.author.id)
    if user_id in conversation_history:
        conversation_history[user_id] = []
        await ctx.reply("✅ Your conversation history has been cleared!")
    else:
        await ctx.reply("You don't have any conversation history.")

@bot.command(name='help')
async def help_command(ctx):
    """Show help message"""
    embed = discord.Embed(
        title="🤖 AI Bot Help",
        description="I'm an AI assistant powered by g4f!",
        color=discord.Color.green()
    )
    embed.add_field(
        name="💬 Chat",
        value="Just send any message and I'll respond!",
        inline=False
    )
    embed.add_field(
        name="🎨 Generate Images",
        value="`/imagine your prompt here`\nExample: `/imagine a sunset over mountains`",
        inline=False
    )
    embed.add_field(
        name="🗑️ Clear History",
        value="`!clear` - Clear your conversation history",
        inline=False
    )
    embed.add_field(
        name="❓ Help",
        value="`!help` - Show this message",
        inline=False
    )
    await ctx.reply(embed=embed)

@bot.command(name='ping')
async def ping(ctx):
    """Check bot latency"""
    latency = round(bot.latency * 1000)
    await ctx.reply(f"🏓 Pong! Latency: {latency}ms")

# Run the bot
if __name__ == "__main__":
    TOKEN = os.getenv('DISCORD_BOT_TOKEN')
    
    if not TOKEN:
        logger.error("DISCORD_BOT_TOKEN environment variable not set!")
        exit(1)
    
    # Start Flask server for health checks
    start_flask()
    
    # Run Discord bot
    bot.run(TOKEN)
