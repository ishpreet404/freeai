import discord
from discord.ext import commands
import g4f
from g4f.client import Client
import os
import logging
import asyncio
from flask import Flask, jsonify
from threading import Thread
import requests
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize bot first
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# AI Chat prefix (messages must start with this to get AI response)
AI_PREFIX = "?"

# Initialize g4f client
g4f_client = Client()

# Store conversation history (in-memory, resets on restart)
conversation_history = {}

# Store allowed channels per guild (in-memory, resets on restart)
# Format: {guild_id: [channel_id1, channel_id2, ...]}
allowed_channels = {}

# Available image generation models
AVAILABLE_IMAGE_MODELS = {
    "flux": "Flux (Default - Fast & Quality)",
    "flux-pro": "Flux Pro (Higher Quality)",
    "flux-realism": "Flux Realism (Photorealistic)",
    "dalle": "DALL-E (OpenAI)",
    "sdxl": "Stable Diffusion XL",
    "playground-v2.5": "Playground v2.5"
}

# Store selected image model per guild (in-memory, resets on restart)
# Format: {guild_id: model_name}
image_models = {}

# Flask app for health checks (keeps Render active)
app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({
        'status': 'online',
        'bot': bot.user.name if bot.user else 'connecting',
        'guilds': len(bot.guilds) if bot.is_ready() else 0,
        'latency': round(bot.latency * 1000) if bot.is_ready() else 0,
        'timestamp': datetime.utcnow().isoformat()
    })

@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'bot_ready': bot.is_ready()})

def run_flask():
    """Run Flask server in a separate thread"""
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

def start_flask():
    """Start Flask server in background"""
    thread = Thread(target=run_flask, daemon=True)
    thread.start()
    logger.info("Flask health server started")

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
    
    # Check if channel restrictions are enabled for this guild
    if message.guild:
        guild_id = str(message.guild.id)
        if guild_id in allowed_channels and allowed_channels[guild_id]:
            # Channel restrictions exist, check if current channel is allowed
            if str(message.channel.id) not in allowed_channels[guild_id]:
                return  # Ignore messages from non-allowed channels
    
    # Check if message has image attachments
    if message.attachments:
        # Check for image attachments
        image_attachments = [att for att in message.attachments if att.content_type and att.content_type.startswith('image/')]
        if image_attachments:
            # Handle image with optional text prompt
            prompt = message.content.strip() if message.content else "Describe this image"
            await handle_image_analysis(message, image_attachments[0].url, prompt)
            return
    
    # Only respond to messages starting with AI_PREFIX
    if message.content.startswith(AI_PREFIX):
        # Remove prefix and handle as chat
        prompt = message.content[len(AI_PREFIX):].strip()
        if prompt:
            await handle_chat(message, prompt)

async def handle_chat(message, prompt=None):
    """Handle regular chat messages with AI"""
    try:
        # Show typing indicator
        async with message.channel.typing():
            user_id = str(message.author.id)
            
            # Use provided prompt or message content
            user_message = prompt if prompt else message.content
            
            # Get or create conversation history for this user
            if user_id not in conversation_history:
                conversation_history[user_id] = []
            
            # Add user message to history
            conversation_history[user_id].append({
                "role": "user",
                "content": user_message
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

async def handle_image_analysis(message, image_url, prompt):
    """Handle image analysis with AI"""
    try:
        # Show typing indicator
        async with message.channel.typing():
            user_id = str(message.author.id)
            
            # Get or create conversation history for this user
            if user_id not in conversation_history:
                conversation_history[user_id] = []
            
            # Create message with image
            user_message = {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_url}}
                ]
            }
            
            # Add to history
            conversation_history[user_id].append(user_message)
            
            # Keep only last 10 messages
            if len(conversation_history[user_id]) > 10:
                conversation_history[user_id] = conversation_history[user_id][-10:]
            
            # Generate response using g4f with vision capability
            response = await asyncio.to_thread(
                g4f_client.chat.completions.create,
                model="gpt-4-vision-preview",
                messages=conversation_history[user_id]
            )
            
            ai_response = response.choices[0].message.content
            
            # Add AI response to history
            conversation_history[user_id].append({
                "role": "assistant",
                "content": ai_response
            })
            
            # Split long messages if needed
            if len(ai_response) > 2000:
                chunks = [ai_response[i:i+2000] for i in range(0, len(ai_response), 2000)]
                for chunk in chunks:
                    await message.reply(chunk)
            else:
                await message.reply(ai_response)
                
    except Exception as e:
        logger.error(f"Image analysis error: {str(e)}")
        await message.reply(f"Sorry, I couldn't analyze that image: {str(e)}")

@bot.command(name='imagine')
async def imagine_command(ctx, *, prompt: str = None):
    """Generate an image from text prompt"""
    try:
        if not prompt:
            await ctx.reply("Please provide a prompt! Example: `!imagine a beautiful sunset`")
            return
        
        # Get selected model for this guild
        guild_id = str(ctx.guild.id) if ctx.guild else "dm"
        selected_model = image_models.get(guild_id, "flux")
        
        # Show typing indicator
        async with ctx.typing():
            await ctx.reply(f"🎨 Generating image with **{AVAILABLE_IMAGE_MODELS.get(selected_model, selected_model)}**: *{prompt}*\nThis may take a moment...")
            
            # Generate image using g4f
            response = await asyncio.to_thread(
                g4f_client.images.generate,
                model=selected_model,
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
                    embed.set_footer(text=f"Requested by {ctx.author.display_name}")
                    
                    await ctx.send(embed=embed)
                else:
                    await ctx.reply("Failed to generate image. Please try again.")
            else:
                await ctx.reply("Failed to generate image. Please try again.")
                
    except Exception as e:
        logger.error(f"Image generation error: {str(e)}")
        await ctx.reply(f"Sorry, I couldn't generate that image: {str(e)}")

@bot.command(name='ask')
async def ask_command(ctx, *, question: str = None):
    """Ask AI a question"""
    if not question:
        await ctx.reply("Please provide a question! Example: `!ask What is Python?`")
        return
    
    try:
        # Show typing indicator
        async with ctx.typing():
            user_id = str(ctx.author.id)
            
            # Get or create conversation history for this user
            if user_id not in conversation_history:
                conversation_history[user_id] = []
            
            # Add user message to history
            conversation_history[user_id].append({
                "role": "user",
                "content": question
            })
            
            # Keep only last 10 messages
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
                    await ctx.reply(chunk)
            else:
                await ctx.reply(ai_response)
                
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        await ctx.reply(f"Sorry, I encountered an error: {str(e)}")

@bot.command(name='clear')
async def clear_history(ctx):
    """Clear conversation history for the user"""
    user_id = str(ctx.author.id)
    if user_id in conversation_history:
        conversation_history[user_id] = []
        await ctx.reply("✅ Your conversation history has been cleared!")
    else:
        await ctx.reply("You don't have any conversation history.")

@bot.command(name='bothelp')
async def help_command(ctx):
    """Show help message"""
    embed = discord.Embed(
        title="🤖 AI Bot Help",
        description="I'm an AI assistant powered by g4f!",
        color=discord.Color.green()
    )
    embed.add_field(
        name="💬 Chat with Prefix",
        value=f"Start your message with `{AI_PREFIX}` to chat with AI\nExample: `{AI_PREFIX}What is Python?`",
        inline=False
    )
    embed.add_field(
        name="📷 Image Analysis",
        value="Upload an image with optional text to analyze it\nExample: Upload image + type 'What's in this image?'",
        inline=False
    )
    embed.add_field(
        name="⚡ Commands",
        value=(
            "`!ask <question>` - Ask AI a question\n"
            "`!imagine <prompt>` - Generate an image from text\n"
            "`!clear` - Clear your conversation history\n"
            "`!ping` - Check bot latency\n"
            "`!listimagemodels` - List available image models\n"
            "`!bothelp` - Show this message"
        ),
        inline=False
    )
    embed.add_field(
        name="🔒 Admin Commands",
        value=(
            "`!setchannel` - Set current channel as active\n"
            "`!removechannel` - Remove current channel\n"
            "`!listchannels` - List active channels\n"
            "`!clearallchannels` - Remove all restrictions\n"
            "`!setimagemodel <model>` - Set image generation model"
        ),
        inline=False
    )
    await ctx.reply(embed=embed)

@bot.command(name='ping')
async def ping(ctx):
    """Check bot latency"""
    latency = round(bot.latency * 1000)
    await ctx.reply(f"🏓 Pong! Latency: {latency}ms")



@bot.command(name='setimagemodel')
@commands.has_permissions(manage_channels=True)
async def set_image_model(ctx, model: str = None):
    """Set the image generation model for this server (Admin only)"""
    if not ctx.guild:
        await ctx.reply("This command can only be used in a server!")
        return
    
    if not model:
        current_model = image_models.get(str(ctx.guild.id), "flux")
        await ctx.reply(f"Current model: **{AVAILABLE_IMAGE_MODELS.get(current_model, current_model)}**\n\nUse `!listimagemodels` to see available models.")
        return
    
    model = model.lower()
    if model not in AVAILABLE_IMAGE_MODELS:
        await ctx.reply(f"❌ Invalid model! Use `!listimagemodels` to see available models.")
        return
    
    image_models[str(ctx.guild.id)] = model
    await ctx.reply(f"✅ Image generation model set to: **{AVAILABLE_IMAGE_MODELS[model]}**")

@bot.command(name='listimagemodels')
async def list_image_models(ctx):
    """List all available image generation models"""
    guild_id = str(ctx.guild.id) if ctx.guild else "dm"
    current_model = image_models.get(guild_id, "flux")
    
    embed = discord.Embed(
        title="🎨 Available Image Generation Models",
        description="Choose a model with `!setimagemodel <model>`",
        color=discord.Color.purple()
    )
    
    for model_key, model_name in AVAILABLE_IMAGE_MODELS.items():
        indicator = "✅ (Current)" if model_key == current_model else ""
        embed.add_field(
            name=f"{model_name} {indicator}",
            value=f"Command: `!setimagemodel {model_key}`",
            inline=False
        )
    
    await ctx.reply(embed=embed)

@bot.command(name='setchannel')
@commands.has_permissions(manage_channels=True)
async def set_channel(ctx):
    """Set the current channel as allowed for bot responses (Admin only)"""
    if not ctx.guild:
        await ctx.reply("This command can only be used in a server!")
        return
    
    guild_id = str(ctx.guild.id)
    channel_id = str(ctx.channel.id)
    
    # Initialize guild's allowed channels if not exists
    if guild_id not in allowed_channels:
        allowed_channels[guild_id] = []
    
    # Add channel if not already in list
    if channel_id not in allowed_channels[guild_id]:
        allowed_channels[guild_id].append(channel_id)
        await ctx.reply(f"✅ Bot is now active in {ctx.channel.mention}!")
    else:
        await ctx.reply(f"ℹ️ This channel is already active!")

@bot.command(name='removechannel')
@commands.has_permissions(manage_channels=True)
async def remove_channel(ctx):
    """Remove the current channel from allowed list (Admin only)"""
    if not ctx.guild:
        await ctx.reply("This command can only be used in a server!")
        return
    
    guild_id = str(ctx.guild.id)
    channel_id = str(ctx.channel.id)
    
    if guild_id in allowed_channels and channel_id in allowed_channels[guild_id]:
        allowed_channels[guild_id].remove(channel_id)
        await ctx.reply(f"❌ Bot will no longer respond in {ctx.channel.mention}")
    else:
        await ctx.reply(f"ℹ️ This channel wasn't active anyway!")

@bot.command(name='listchannels')
@commands.has_permissions(manage_channels=True)
async def list_channels(ctx):
    """List all allowed channels in this server (Admin only)"""
    if not ctx.guild:
        await ctx.reply("This command can only be used in a server!")
        return
    
    guild_id = str(ctx.guild.id)
    
    if guild_id not in allowed_channels or not allowed_channels[guild_id]:
        await ctx.reply("ℹ️ No channel restrictions set. Bot responds in all channels!")
        return
    
    channels_list = []
    for channel_id in allowed_channels[guild_id]:
        channel = ctx.guild.get_channel(int(channel_id))
        if channel:
            channels_list.append(channel.mention)
    
    if channels_list:
        await ctx.reply(f"✅ **Active Channels:**\n" + "\n".join(channels_list))
    else:
        await ctx.reply("ℹ️ No valid channels found in the list!")

@bot.command(name='clearallchannels')
@commands.has_permissions(manage_channels=True)
async def clear_all_channels(ctx):
    """Remove all channel restrictions (Admin only)"""
    if not ctx.guild:
        await ctx.reply("This command can only be used in a server!")
        return
    
    guild_id = str(ctx.guild.id)
    
    if guild_id in allowed_channels:
        allowed_channels[guild_id] = []
        await ctx.reply("✅ All channel restrictions removed! Bot now responds in all channels.")
    else:
        await ctx.reply("ℹ️ No restrictions were set!")

@set_channel.error
@remove_channel.error
@list_channels.error
@clear_all_channels.error
@set_image_model.error
async def channel_command_error(ctx, error):
    """Handle permission errors for channel commands"""
    if isinstance(error, commands.MissingPermissions):
        await ctx.reply("❌ You need **Manage Channels** permission to use this command!")

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
