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
import edge_tts
import io
from pydub import AudioSegment
import speech_recognition as sr
import tempfile
from collections import deque
import re
from tmdbv3api import TMDb, Movie, TV
from PIL import Image

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

# Initialize TMDB
tmdb = TMDb()
tmdb.api_key = 'ae4bd1b6fce2a5648671bfc171d15ba4'
tmdb.language = 'en'
movie_api = Movie()
tv_api = TV()

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

# Voice settings
TTS_VOICE = "en-IN-NeerjaNeural"  # Indian female voice
voice_clients = {}  # Store voice connections per guild

def get_voice_client(guild):
    """Get the actual voice client for a guild - robust check"""
    # First check Discord's internal state
    if guild.voice_client and guild.voice_client.is_connected():
        return guild.voice_client
    
    # Check our cache
    guild_id = str(guild.id)
    if guild_id in voice_clients:
        vc = voice_clients[guild_id]
        if vc.is_connected():
            return vc
        else:
            # Clean up stale entry
            del voice_clients[guild_id]
    
    return None

def cleanup_voice_client(guild_id):
    """Clean up voice client entry"""
    guild_id = str(guild_id)
    if guild_id in voice_clients:
        try:
            if voice_clients[guild_id].is_connected():
                # Don't delete if actually connected
                return
        except:
            pass
        del voice_clients[guild_id]

# Music system


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

@bot.event
async def on_voice_state_update(member, before, after):
    """Track voice state changes to keep our state in sync"""
    # Only track bot's own voice state
    if member.id != bot.user.id:
        return
    
    guild_id = str(member.guild.id)
    
    # Bot left or was disconnected from voice
    if before.channel and not after.channel:
        logger.info(f"Bot left voice channel in guild {guild_id}")
        cleanup_voice_client(guild_id)
    
    # Bot joined or moved to a voice channel
    elif not before.channel and after.channel:
        logger.info(f"Bot joined voice channel in guild {guild_id}")
        # Sync our cache with actual state
        if member.guild.voice_client:
            voice_clients[guild_id] = member.guild.voice_client
    
    # Bot moved between channels
    elif before.channel and after.channel and before.channel.id != after.channel.id:
        logger.info(f"Bot moved from {before.channel.name} to {after.channel.name} in guild {guild_id}")
        # Update cache
        if member.guild.voice_client:
            voice_clients[guild_id] = member.guild.voice_client

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
    
    # Check if bot is mentioned or replied to
    is_mentioned = bot.user in message.mentions
    is_reply_to_bot = message.reference and message.reference.resolved and message.reference.resolved.author == bot.user
    
    # If bot is mentioned or replied to, treat the message as a prompt
    if is_mentioned or is_reply_to_bot:
        # Remove bot mention from content if present
        prompt = message.content
        if is_mentioned:
            prompt = prompt.replace(f'<@{bot.user.id}>', '').replace(f'<@!{bot.user.id}>', '').strip()
        if prompt:
            await handle_chat(message, prompt)
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

def compress_image(image_bytes, max_size_mb=8):
    """Compress image if it exceeds Discord's size limit"""
    max_size_bytes = max_size_mb * 1024 * 1024
    
    # If already under limit, return as-is
    if len(image_bytes) <= max_size_bytes:
        return image_bytes
    
    try:
        # Open image
        img = Image.open(io.BytesIO(image_bytes))
        
        # Convert RGBA to RGB if needed
        if img.mode == 'RGBA':
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background
        
        # Start with quality 85 and reduce until under size limit
        quality = 85
        while quality > 20:
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=quality, optimize=True)
            compressed_bytes = output.getvalue()
            
            if len(compressed_bytes) <= max_size_bytes:
                return compressed_bytes
            
            quality -= 5
        
        # If still too large, resize the image
        scale = 0.8
        while scale > 0.3:
            new_width = int(img.width * scale)
            new_height = int(img.height * scale)
            resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            output = io.BytesIO()
            resized.save(output, format='JPEG', quality=85, optimize=True)
            compressed_bytes = output.getvalue()
            
            if len(compressed_bytes) <= max_size_bytes:
                return compressed_bytes
            
            scale -= 0.1
        
        # Return best effort
        return compressed_bytes
    except Exception as e:
        logger.error(f"Compression error: {str(e)}")
        return image_bytes

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
        
        # Discord file size limits: 8MB for free servers, 50MB for boosted (Level 2), 100MB for Level 3
        # We'll use 8MB as safe default
        MAX_FILE_SIZE = 8 * 1024 * 1024  # 8 MB in bytes
        
        # Show typing indicator
        status_msg = await ctx.reply(f"🎨 Generating images with **{AVAILABLE_IMAGE_MODELS.get(selected_model, selected_model)}**\n> _{prompt}_\n\n⏳ Trying multiple providers...")
        
        try:
            # Import providers
            from g4f.Provider import Blackbox, PollinationsAI, Airforce
            
            # Define providers to try for each model
            provider_map = {
                'flux': [Blackbox, PollinationsAI, Airforce],
                'flux-pro': [Blackbox, Airforce, PollinationsAI],
                'flux-realism': [Blackbox, PollinationsAI, Airforce],
                'sdxl': [PollinationsAI, Airforce, Blackbox],
                'playground-v2.5': [Airforce, Blackbox, PollinationsAI],
                'dalle': [Airforce, Blackbox, PollinationsAI]
            }
            
            # Get providers for selected model
            providers_to_try = provider_map.get(selected_model, [Blackbox, PollinationsAI, Airforce])
            
            # Function to generate image with a specific provider
            def generate_with_provider(provider):
                try:
                    provider_name = provider.__name__
                    logger.info(f"Trying provider: {provider_name} for model: {selected_model}")
                    response = g4f_client.images.generate(
                        model=selected_model,
                        prompt=prompt,
                        provider=provider
                    )
                    logger.info(f"Success with {provider_name}")
                    return (provider_name, response)
                except Exception as e:
                    logger.warning(f"Provider {provider.__name__} failed: {str(e)}")
                    return (provider.__name__, None)
            
            # Try all providers in parallel
            tasks = [asyncio.get_event_loop().run_in_executor(None, generate_with_provider, provider) 
                     for provider in providers_to_try]
            results = await asyncio.gather(*tasks)
            
            # Filter successful results
            successful_results = [(name, resp) for name, resp in results if resp is not None]
            
            if not successful_results:
                await status_msg.edit(content=f"❌ All providers failed for **{selected_model}** model.\n\n💡 Try another model: `!listimagemodels`")
                return
            
            # Update status
            provider_count = len(successful_results)
            await status_msg.edit(content=f"✅ Generated {provider_count} image(s) from {provider_count} provider(s)!\n⏳ Downloading...")
            # Update status
            provider_count = len(successful_results)
            await status_msg.edit(content=f"✅ Generated {provider_count} image(s) from {provider_count} provider(s)!\n⏳ Downloading...")
                
            # Process each successful response
            images_to_send = []
            
            for provider_name, response in successful_results:
                # Get image URL or data from response
                image_url = None
                image_data = None
                
                # Try different response formats
                logger.info(f"Parsing response from {provider_name}, type: {type(response)}")
                
                if hasattr(response, 'data') and response.data:
                    if len(response.data) > 0:
                        first_item = response.data[0]
                        if hasattr(first_item, 'url'):
                            image_url = first_item.url
                        elif isinstance(first_item, str):
                            image_url = first_item
                        elif hasattr(first_item, 'b64_json'):
                            import base64
                            image_data = base64.b64decode(first_item.b64_json)
                elif isinstance(response, str):
                    image_url = response
                elif isinstance(response, bytes):
                    image_data = response
                    
                # If we have image data directly
                if image_data:
                    size_mb = len(image_data) / (1024 * 1024)
                    logger.info(f"Image data from {provider_name}: {size_mb:.2f}MB")
                    
                    if len(image_data) > MAX_FILE_SIZE:
                        image_data = await asyncio.get_event_loop().run_in_executor(None, compress_image, image_data)
                    
                    images_to_send.append((provider_name, image_data))
                    
                # If we have a URL, download it
                elif image_url:
                    try:
                        def download_image():
                            resp = requests.get(image_url, timeout=30)
                            resp.raise_for_status()
                            return resp.content
                        
                        image_bytes = await asyncio.get_event_loop().run_in_executor(None, download_image)
                        logger.info(f"Downloaded {len(image_bytes)} bytes from {provider_name}")
                        
                        # Check size and compress if needed
                        if len(image_bytes) > MAX_FILE_SIZE:
                            image_bytes = await asyncio.get_event_loop().run_in_executor(None, compress_image, image_bytes)
                        
                        images_to_send.append((provider_name, image_bytes))
                    except Exception as download_error:
                        logger.error(f"Download error from {provider_name}: {str(download_error)}")
                        continue
            
            # Send all images
            if not images_to_send:
                await status_msg.edit(content=f"❌ Could not process any images.\n\n💡 Try another model: `!listimagemodels`")
                return
            
            # Create embeds and files for all images
            if len(images_to_send) == 1:
                # Single image - send with embed
                provider_name, image_data = images_to_send[0]
                file = discord.File(io.BytesIO(image_data), filename="generated_image.jpg")
                embed = discord.Embed(
                    title="🎨 Generated Image",
                    description=f"> {prompt}",
                    color=discord.Color.green()
                )
                embed.set_image(url="attachment://generated_image.jpg")
                embed.set_footer(text=f"Requested by {ctx.author.display_name} • Model: {selected_model} • Provider: {provider_name}")
                await ctx.send(embed=embed, file=file)
            else:
                # Multiple images - send all at once
                files = []
                for i, (provider_name, image_data) in enumerate(images_to_send, 1):
                    files.append(discord.File(io.BytesIO(image_data), filename=f"image_{i}_{provider_name}.jpg"))
                
                embed = discord.Embed(
                    title=f"🎨 Generated {len(images_to_send)} Images",
                    description=f"> {prompt}\n\n**Providers:** {', '.join([name for name, _ in images_to_send])}",
                    color=discord.Color.green()
                )
                embed.set_footer(text=f"Requested by {ctx.author.display_name} • Model: {selected_model}")
                await ctx.send(embed=embed, files=files)
            
            await status_msg.delete()
                    
        except Exception as gen_error:
            logger.error(f"Generation wrapper error: {str(gen_error)}", exc_info=True)
            try:
                await status_msg.edit(content=f"❌ Image generation failed: {str(gen_error)}\n\n💡 Try: `!setimagemodel flux` or check `!listimagemodels`")
            except:
                await ctx.reply(f"❌ Image generation error: {str(gen_error)}\n\n💡 Try: `!setimagemodel flux`")
                
    except Exception as e:
        logger.error(f"Image command error: {str(e)}", exc_info=True)
        await ctx.reply(f"❌ Command error: {str(e)}\n\n💡 Use `!listimagemodels` to see available models")



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

@bot.command(name='speak')
async def speak_command(ctx, *, text: str = None):
    """Convert text to speech with Indian female voice"""
    if not text:
        await ctx.reply("Please provide text! Example: `!speak Hello, how are you?`")
        return
    
    # List of backup voices in case primary fails
    voices_to_try = [
        "en-IN-NeerjaNeural",  # Indian female (primary)
        "en-US-JennyNeural",    # US female (backup)
        "en-GB-SoniaNeural"     # UK female (backup)
    ]
    
    tmp_filename = None
    try:
        async with ctx.typing():
            last_error = None
            
            # Try each voice until one works
            for voice in voices_to_try:
                try:
                    # Generate speech with Edge TTS
                    communicate = edge_tts.Communicate(text, voice)
                    
                    # Save to temporary file
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
                        tmp_filename = tmp_file.name
                        await communicate.save(tmp_filename)
                    
                    # Send audio file
                    voice_label = "🔊" if voice == voices_to_try[0] else "🔊 (backup voice)"
                    await ctx.reply(f"{voice_label} Here's your audio:", file=discord.File(tmp_filename, "speech.mp3"))
                    
                    # Clean up and return on success
                    if tmp_filename and os.path.exists(tmp_filename):
                        os.unlink(tmp_filename)
                    return
                    
                except Exception as voice_error:
                    logger.warning(f"Failed with voice {voice}: {str(voice_error)}")
                    last_error = voice_error
                    if tmp_filename and os.path.exists(tmp_filename):
                        os.unlink(tmp_filename)
                    continue
            
            # If all voices failed
            raise last_error if last_error else Exception("All voices failed")
            
    except Exception as e:
        logger.error(f"TTS error: {str(e)}")
        await ctx.reply(f"Sorry, I couldn't generate speech: {str(e)}")

@bot.command(name='join')
async def join_voice(ctx):
    """Join your voice channel"""
    if not ctx.author.voice:
        await ctx.reply("❌ You need to be in a voice channel!")
        return
    
    channel = ctx.author.voice.channel
    guild_id = str(ctx.guild.id)
    
    # Check if already connected using robust check
    existing_vc = get_voice_client(ctx.guild)
    if existing_vc:
        if existing_vc.channel.id == channel.id:
            await ctx.reply(f"ℹ️ Already in {channel.name}!")
        else:
            await ctx.reply(f"ℹ️ Already in {existing_vc.channel.name}! Use `!leave` first.")
        return
    
    try:
        voice_client = await channel.connect()
        voice_clients[guild_id] = voice_client
        await ctx.reply(f"✅ Joined {channel.name}!")
        
    except discord.errors.ClientException:
        # Stale connection detected - force cleanup and retry
        cleanup_voice_client(guild_id)
        try:
            # Force disconnect from Discord's perspective
            if ctx.guild.voice_client:
                await ctx.guild.voice_client.disconnect(force=True)
            await asyncio.sleep(0.5)  # Brief delay for cleanup
            
            voice_client = await channel.connect()
            voice_clients[guild_id] = voice_client
            await ctx.reply(f"✅ Joined {channel.name}! (Cleaned up stale connection)")
        except Exception as retry_error:
            logger.error(f"Voice join retry failed: {str(retry_error)}")
            await ctx.reply(f"❌ Failed to join after cleanup: {str(retry_error)}")
    except Exception as e:
        logger.error(f"Voice join error: {str(e)}")
        await ctx.reply(f"❌ Couldn't join voice channel: {str(e)}")

@bot.command(name='leave')
async def leave_voice(ctx):
    """Leave the voice channel"""
    guild_id = str(ctx.guild.id)
    
    # Use robust check
    voice_client = get_voice_client(ctx.guild)
    
    if not voice_client:
        await ctx.reply("❌ I'm not in a voice channel!")
        return
    
    try:
        await voice_client.disconnect()
        cleanup_voice_client(guild_id)
        await ctx.reply("👋 Left the voice channel!")
        
    except Exception as e:
        logger.error(f"Voice leave error: {str(e)}")
        # Force cleanup even if disconnect fails
        cleanup_voice_client(guild_id)
        await ctx.reply(f"⚠️ Left with errors: {str(e)}")

@bot.command(name='listen')
async def listen_command(ctx, duration: int = 5):
    """Listen and transcribe voice (duration in seconds, max 30)"""
    guild_id = str(ctx.guild.id)
    
    voice_client = get_voice_client(ctx.guild)
    if not voice_client:
        await ctx.reply("❌ Bot must be in voice channel! Use `!join` first.")
        return
    
    if not voice_client.is_connected():
        await ctx.reply("❌ Bot is not properly connected to voice! Use `!leave` then `!join` again.")
        cleanup_voice_client(guild_id)
        return
    
    if duration > 30:
        duration = 30
        
    try:
        await ctx.reply(f"🎤 Listening for {duration} seconds...")
        
        # Note: Discord.py voice recording is complex and requires additional setup
        # For Render free tier, we'll use a simpler approach with audio attachments
        await ctx.reply("ℹ️ Voice recording from channels requires additional setup. Please upload an audio file instead or use `!transcribe` with an audio attachment.")
        
    except Exception as e:
        logger.error(f"Listen error: {str(e)}")
        await ctx.reply(f"Sorry, couldn't listen: {str(e)}")

@bot.command(name='transcribe')
async def transcribe_command(ctx):
    """Transcribe audio from an attachment"""
    if not ctx.message.attachments:
        await ctx.reply("Please attach an audio file (mp3, wav, ogg, m4a)!")
        return
    
    attachment = ctx.message.attachments[0]
    
    # Check if it's an audio file
    if not any(attachment.filename.lower().endswith(ext) for ext in ['.mp3', '.wav', '.ogg', '.m4a', '.webm']):
        await ctx.reply("❌ Please attach an audio file (mp3, wav, ogg, m4a)!")
        return
    
    try:
        async with ctx.typing():
            # Download audio file
            audio_data = await attachment.read()
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(attachment.filename)[1]) as tmp_file:
                tmp_file.write(audio_data)
                tmp_filename = tmp_file.name
            
            # Convert to WAV if needed
            wav_filename = tmp_filename
            if not tmp_filename.endswith('.wav'):
                audio = AudioSegment.from_file(tmp_filename)
                wav_filename = tmp_filename.rsplit('.', 1)[0] + '.wav'
                audio.export(wav_filename, format='wav')
            
            # Transcribe using speech_recognition
            recognizer = sr.Recognizer()
            with sr.AudioFile(wav_filename) as source:
                audio = recognizer.record(source)
                text = await asyncio.to_thread(
                    recognizer.recognize_google,
                    audio
                )
            
            # Clean up
            os.unlink(tmp_filename)
            if wav_filename != tmp_filename:
                os.unlink(wav_filename)
            
            await ctx.reply(f"📝 **Transcription:**\n{text}")
            
    except sr.UnknownValueError:
        await ctx.reply("❌ Could not understand the audio. Please try again with clearer audio.")
    except sr.RequestError as e:
        await ctx.reply(f"❌ Could not request transcription service: {str(e)}")
    except Exception as e:
        logger.error(f"Transcription error: {str(e)}")
        await ctx.reply(f"Sorry, couldn't transcribe audio: {str(e)}")



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
            "`!speak <text>` - Convert text to speech (Indian voice)\n"
            "`!transcribe` - Transcribe audio attachment\n"
            "`!clear` - Clear your conversation history\n"
            "`!ping` - Check bot latency\n"
            "`!listimagemodels` - List available image models"
        ),
        inline=False
    )
    embed.add_field(
        name="🎙️ Voice Commands",
        value=(
            "`!join` - Join your voice channel\n"
            "`!leave` - Leave voice channel\n"
            "`!listen [seconds]` - Listen and transcribe (max 30s)"
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

# Movie/TV Streaming Commands

STREAMING_PROVIDERS = {
    'vidsrc': 'VidSrc (Recommended)',
    'vixsrc': 'VixSrc',
    'godrive': 'GoDrive Player',
    'embedsu': 'Embed.su',
    '2embed': '2Embed',
    'vidfast': 'VidFast'
}

def get_streaming_url(media_type: str, tmdb_id: str, imdb_id: str = None, provider: str = 'vidsrc', season: int = None, episode: int = None) -> str:
    """Generate streaming URL based on provider and media type"""
    if media_type == 'movie':
        if provider == 'vixsrc':
            return f"https://vixsrc.to/movie/{tmdb_id}"
        elif provider == 'vidsrc':
            return f"https://vidsrc.to/embed/movie/{imdb_id if imdb_id else tmdb_id}"
        elif provider == 'godrive':
            return f"https://godriveplayer.com/player.php?imdb={imdb_id}" if imdb_id else f"https://godriveplayer.com/player.php?tmdb={tmdb_id}"
        elif provider == 'embedsu':
            return f"https://embed.su/embed/movie/{tmdb_id}"
        elif provider == '2embed':
            return f"https://www.2embed.cc/embed/{imdb_id if imdb_id else tmdb_id}"
        elif provider == 'vidfast':
            return f"https://vidfast.pro/movie/{tmdb_id}?autoPlay=true"
    elif media_type == 'tv':
        if provider == 'vixsrc':
            return f"https://vixsrc.to/tv/{tmdb_id}/{season}/{episode}"
        elif provider == 'vidsrc':
            return f"https://vidsrc.to/embed/tv/{imdb_id if imdb_id else tmdb_id}/{season}/{episode}"
        elif provider == 'godrive':
            return f"https://godriveplayer.com/player.php?type=series&imdb={imdb_id}&season={season}&episode={episode}" if imdb_id else f"https://godriveplayer.com/player.php?type=series&tmdb={tmdb_id}&season={season}&episode={episode}"
        elif provider == 'embedsu':
            return f"https://embed.su/embed/tv/{tmdb_id}/{season}/{episode}"
        elif provider == '2embed':
            return f"https://www.2embed.cc/embedtv/{imdb_id if imdb_id else tmdb_id}&s={season}&e={episode}"
        elif provider == 'vidfast':
            return f"https://vidfast.pro/tv/{tmdb_id}/{season}/{episode}?autoPlay=true"
    return None

@bot.command(name='movie')
async def search_movie(ctx, *, query: str = None):
    """Search for a movie and get streaming links"""
    if not query:
        await ctx.reply("Please provide a movie name!\nExample: `!movie Inception`")
        return
    
    async with ctx.typing():
        try:
            # Search TMDB
            results = movie_api.search(query)
            
            if not results:
                await ctx.reply(f"❌ No movies found for: {query}")
                return
            
            # Convert results to list and get first movie
            results_list = list(results)
            if not results_list:
                await ctx.reply(f"❌ No movies found for: {query}")
                return
            
            movie = results_list[0]
            movie_details = movie_api.details(movie.id)
            
            # Get external IDs for IMDb
            external_ids = movie_api.external_ids(movie.id)
            imdb_id = external_ids.get('imdb_id', None)
            
            # Create embed
            release_year = movie_details.release_date[:4] if hasattr(movie_details, 'release_date') and movie_details.release_date else 'N/A'
            overview = movie_details.overview if hasattr(movie_details, 'overview') else "No overview available."
            description = overview[:300] + "..." if len(overview) > 300 else overview
            
            embed = discord.Embed(
                title=f"{movie_details.title} ({release_year})",
                description=description,
                color=discord.Color.blue(),
                url=f"https://www.themoviedb.org/movie/{movie.id}"
            )
            
            # Add poster
            if movie_details.poster_path:
                embed.set_thumbnail(url=f"https://image.tmdb.org/t/p/w500{movie_details.poster_path}")
            
            # Add fields - safely handle genres
            embed.add_field(name="⭐ Rating", value=f"{movie_details.vote_average:.1f}/10", inline=True)
            embed.add_field(name="🎬 Runtime", value=f"{movie_details.runtime} min" if movie_details.runtime else "N/A", inline=True)
            
            # Get genres safely
            genres_text = "N/A"
            if hasattr(movie_details, 'genres') and movie_details.genres:
                try:
                    genres_list = list(movie_details.genres)
                    # Handle both dict and object formats
                    genre_names = []
                    for g in genres_list[:3]:
                        if isinstance(g, dict):
                            genre_names.append(g.get('name', ''))
                        elif hasattr(g, 'name'):
                            genre_names.append(g.name)
                    genres_text = ", ".join(genre_names) if genre_names else "N/A"
                except Exception as e:
                    logger.warning(f"Error processing genres: {e}")
            embed.add_field(name="🎭 Genres", value=genres_text, inline=True)
            
            # Create buttons for streaming providers
            view = discord.ui.View()
            for provider_key, provider_name in STREAMING_PROVIDERS.items():
                stream_url = get_streaming_url('movie', str(movie.id), imdb_id, provider_key)
                if stream_url:
                    view.add_item(discord.ui.Button(
                        label=f"▶️ {provider_name}",
                        url=stream_url,
                        style=discord.ButtonStyle.link
                    ))
            
            embed.set_footer(text=f"TMDB ID: {movie.id} | IMDb ID: {imdb_id if imdb_id else 'N/A'}")
            
            await ctx.reply(embed=embed, view=view)
            
        except Exception as e:
            logger.error(f"Movie search error: {str(e)}")
            await ctx.reply(f"❌ Error searching movie: {str(e)}")

@bot.command(name='tv', aliases=['series', 'show'])
async def search_tv(ctx, *, query: str = None):
    """Search for a TV show and get streaming links"""
    if not query:
        await ctx.reply("Please provide a TV show name!\nExample: `!tv Breaking Bad`")
        return
    
    async with ctx.typing():
        try:
            # Search TMDB
            results = tv_api.search(query)
            
            if not results:
                await ctx.reply(f"❌ No TV shows found for: {query}")
                return
            
            # Convert results to list and get first show
            results_list = list(results)
            if not results_list:
                await ctx.reply(f"❌ No TV shows found for: {query}")
                return
            
            show = results_list[0]
            show_details = tv_api.details(show.id)
            
            # Get external IDs for IMDb
            external_ids = tv_api.external_ids(show.id)
            imdb_id = external_ids.get('imdb_id', None)
            
            # Create embed
            embed = discord.Embed(
                title=f"{show_details.name} ({show_details.first_air_date[:4] if show_details.first_air_date else 'N/A'})",
                description=show_details.overview[:300] + "..." if len(show_details.overview) > 300 else show_details.overview,
                color=discord.Color.purple(),
                url=f"https://www.themoviedb.org/tv/{show.id}"
            )
            
            # Add poster
            if show_details.poster_path:
                embed.set_thumbnail(url=f"https://image.tmdb.org/t/p/w500{show_details.poster_path}")
            
            # Add fields
            embed.add_field(name="⭐ Rating", value=f"{show_details.vote_average:.1f}/10", inline=True)
            embed.add_field(name="📺 Seasons", value=str(show_details.number_of_seasons), inline=True)
            embed.add_field(name="🎬 Episodes", value=str(show_details.number_of_episodes), inline=True)
            
            # Get genres safely
            genres_text = "N/A"
            if hasattr(show_details, 'genres') and show_details.genres:
                try:
                    genres_list = list(show_details.genres)
                    # Handle both dict and object formats
                    genre_names = []
                    for g in genres_list[:3]:
                        if isinstance(g, dict):
                            genre_names.append(g.get('name', ''))
                        elif hasattr(g, 'name'):
                            genre_names.append(g.name)
                    genres_text = ", ".join(genre_names) if genre_names else "N/A"
                except Exception as e:
                    logger.warning(f"Error processing genres: {e}")
            embed.add_field(name="🎭 Genres", value=genres_text, inline=True)
            embed.add_field(name="📅 Status", value=show_details.status, inline=True)
            
            # Default to Season 1 Episode 1
            season = 1
            episode = 1
            
            # Create buttons for streaming providers
            view = discord.ui.View()
            for provider_key, provider_name in STREAMING_PROVIDERS.items():
                stream_url = get_streaming_url('tv', str(show.id), imdb_id, provider_key, season, episode)
                if stream_url:
                    view.add_item(discord.ui.Button(
                        label=f"▶️ {provider_name}",
                        url=stream_url,
                        style=discord.ButtonStyle.link
                    ))
            
            embed.set_footer(text=f"TMDB ID: {show.id} | IMDb ID: {imdb_id if imdb_id else 'N/A'} | S{season}E{episode}")
            embed.add_field(name="💡 Tip", value=f"Use `!tvepisode {show.id} <season> <episode>` for specific episodes", inline=False)
            
            await ctx.reply(embed=embed, view=view)
            
        except Exception as e:
            logger.error(f"TV search error: {str(e)}")
            await ctx.reply(f"❌ Error searching TV show: {str(e)}")

@bot.command(name='tvepisode', aliases=['episode', 'ep'])
async def tv_episode(ctx, tmdb_id: str = None, season: int = 1, episode: int = 1):
    """Get streaming links for a specific TV episode"""
    if not tmdb_id:
        await ctx.reply("Please provide TMDB ID, season, and episode!\nExample: `!tvepisode 1396 1 1`")
        return
    
    async with ctx.typing():
        try:
            show_details = tv_api.details(int(tmdb_id))
            external_ids = tv_api.external_ids(int(tmdb_id))
            imdb_id = external_ids.get('imdb_id', None)
            
            # Create embed
            embed = discord.Embed(
                title=f"{show_details.name} - S{season}E{episode}",
                description=show_details.overview[:200] + "..." if len(show_details.overview) > 200 else show_details.overview,
                color=discord.Color.purple()
            )
            
            if show_details.poster_path:
                embed.set_thumbnail(url=f"https://image.tmdb.org/t/p/w500{show_details.poster_path}")
            
            # Create buttons
            view = discord.ui.View()
            for provider_key, provider_name in STREAMING_PROVIDERS.items():
                stream_url = get_streaming_url('tv', tmdb_id, imdb_id, provider_key, season, episode)
                if stream_url:
                    view.add_item(discord.ui.Button(
                        label=f"▶️ {provider_name}",
                        url=stream_url,
                        style=discord.ButtonStyle.link
                    ))
            
            embed.set_footer(text=f"TMDB ID: {tmdb_id} | Season {season} Episode {episode}")
            
            await ctx.reply(embed=embed, view=view)
            
        except Exception as e:
            logger.error(f"Episode error: {str(e)}")
            await ctx.reply(f"❌ Error: {str(e)}")

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
