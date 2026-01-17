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
import yt_dlp
from collections import deque
import re

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

# Voice settings
TTS_VOICE = "en-IN-NeerjaNeural"  # Indian female voice
voice_clients = {}  # Store voice connections per guild

# Music system
music_queues = {}  # Format: {guild_id: deque([song_info, ...])}
now_playing = {}   # Format: {guild_id: song_info}

# YouTube downloader options
YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'extractaudio': True,
    'audioformat': 'mp3',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': False,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'ytsearch',
    'source_address': '0.0.0.0',
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

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
            
            try:
                # Create a synchronous wrapper function
                def generate_image():
                    try:
                        response = g4f_client.images.generate(
                            model=selected_model,
                            prompt=prompt
                        )
                        return response
                    except Exception as inner_e:
                        logger.error(f"Inner generation error: {str(inner_e)}")
                        return None
                
                # Run in thread pool
                response = await asyncio.get_event_loop().run_in_executor(None, generate_image)
                
                # Check if response is valid
                if response is None:
                    await ctx.reply("❌ Image generation failed. The provider may be unavailable. Try: `!listimagemodels` to see other options.")
                    return
                
                # Get image URL from response
                image_url = None
                
                # Try different response formats
                if hasattr(response, 'data') and response.data:
                    if len(response.data) > 0:
                        first_item = response.data[0]
                        if hasattr(first_item, 'url'):
                            image_url = first_item.url
                        elif isinstance(first_item, str):
                            image_url = first_item
                elif isinstance(response, str):
                    image_url = response
                
                if image_url:
                    # Create embed with image
                    embed = discord.Embed(
                        title="Generated Image",
                        description=prompt,
                        color=discord.Color.blue()
                    )
                    embed.set_image(url=image_url)
                    embed.set_footer(text=f"Requested by {ctx.author.display_name} | Model: {selected_model}")
                    
                    await ctx.send(embed=embed)
                else:
                    await ctx.reply("❌ Could not extract image from response. Try: `!setimagemodel flux`")
                    
            except Exception as gen_error:
                logger.error(f"Generation wrapper error: {str(gen_error)}")
                await ctx.reply(f"❌ Image generation error: {str(gen_error)}\nTry: `!setimagemodel flux`")
                
    except Exception as e:
        logger.error(f"Image command error: {str(e)}")
        await ctx.reply(f"❌ Command error: {str(e)}\nTry: `!listimagemodels` to see available models")



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
    
    try:
        async with ctx.typing():
            # Generate speech with Edge TTS
            communicate = edge_tts.Communicate(text, TTS_VOICE)
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
                tmp_filename = tmp_file.name
                await communicate.save(tmp_filename)
            
            # Send audio file
            await ctx.reply("🔊 Here's your audio:", file=discord.File(tmp_filename, "speech.mp3"))
            
            # Clean up
            os.unlink(tmp_filename)
            
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
    
    try:
        if guild_id in voice_clients and voice_clients[guild_id].is_connected():
            await ctx.reply("ℹ️ Already in a voice channel! Use `!leave` first.")
            return
        
        voice_client = await channel.connect()
        voice_clients[guild_id] = voice_client
        await ctx.reply(f"✅ Joined {channel.name}! Say something and I'll transcribe it.")
        
    except Exception as e:
        logger.error(f"Voice join error: {str(e)}")
        await ctx.reply(f"Sorry, couldn't join voice channel: {str(e)}")

@bot.command(name='leave')
async def leave_voice(ctx):
    """Leave the voice channel"""
    guild_id = str(ctx.guild.id)
    
    if guild_id not in voice_clients or not voice_clients[guild_id].is_connected():
        await ctx.reply("❌ I'm not in a voice channel!")
        return
    
    try:
        await voice_clients[guild_id].disconnect()
        del voice_clients[guild_id]
        await ctx.reply("👋 Left the voice channel!")
        
    except Exception as e:
        logger.error(f"Voice leave error: {str(e)}")
        await ctx.reply(f"Sorry, couldn't leave voice channel: {str(e)}")

@bot.command(name='listen')
async def listen_command(ctx, duration: int = 5):
    """Listen and transcribe voice (duration in seconds, max 30)"""
    guild_id = str(ctx.guild.id)
    
    if guild_id not in voice_clients or not voice_clients[guild_id].is_connected():
        await ctx.reply("❌ Bot must be in voice channel! Use `!join` first.")
        return
    
    if duration > 30:
        duration = 30
        
    try:
        await ctx.reply(f"🎤 Listening for {duration} seconds...")
        
        # Create a sink to record audio
        voice_client = voice_clients[guild_id]
        
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

# YouTube Music Player Commands

def get_music_queue(guild_id):
    """Get or create music queue for guild"""
    if guild_id not in music_queues:
        music_queues[guild_id] = deque()
    return music_queues[guild_id]

async def play_next(ctx):
    """Play next song in queue"""
    guild_id = str(ctx.guild.id)
    queue = get_music_queue(guild_id)
    
    if not queue:
        now_playing.pop(guild_id, None)
        return
    
    if guild_id not in voice_clients or not voice_clients[guild_id].is_connected():
        return
    
    voice_client = voice_clients[guild_id]
    song_info = queue.popleft()
    now_playing[guild_id] = song_info
    
    try:
        # Extract audio URL
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(song_info['url'], download=False)
            url2 = info['url']
        
        # Create audio source
        source = discord.FFmpegPCMAudio(url2, **FFMPEG_OPTIONS)
        
        # Play audio
        def after_playing(error):
            if error:
                logger.error(f"Player error: {error}")
            asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)
        
        voice_client.play(source, after=after_playing)
        
        # Send now playing embed
        embed = discord.Embed(
            title="🎵 Now Playing",
            description=f"**[{song_info['title']}]({song_info['url']})**",
            color=discord.Color.green()
        )
        embed.add_field(name="Duration", value=song_info['duration'], inline=True)
        embed.add_field(name="Requested by", value=song_info['requester'], inline=True)
        if song_info.get('thumbnail'):
            embed.set_thumbnail(url=song_info['thumbnail'])
        embed.set_footer(text=f"Songs in queue: {len(queue)}")
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error playing song: {str(e)}")
        await ctx.send(f"❌ Error playing song: {str(e)}")
        await play_next(ctx)

@bot.command(name='play')
async def play_music(ctx, *, query: str = None):
    """Play music from YouTube (URL or search query)"""
    if not query:
        await ctx.reply("Please provide a YouTube URL or search query!\nExample: `!play Imagine Dragons Believer`")
        return
    
    # Check if user is in voice channel
    if not ctx.author.voice:
        await ctx.reply("❌ You need to be in a voice channel!")
        return
    
    guild_id = str(ctx.guild.id)
    
    # Join voice channel if not connected
    if guild_id not in voice_clients or not voice_clients[guild_id].is_connected():
        try:
            channel = ctx.author.voice.channel
            voice_client = await channel.connect()
            voice_clients[guild_id] = voice_client
        except Exception as e:
            await ctx.reply(f"❌ Couldn't join voice channel: {str(e)}")
            return
    
    async with ctx.typing():
        try:
            # Search or get video info
            with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
                # If it's not a URL, search for it
                if not query.startswith('http'):
                    query = f"ytsearch:{query}"
                
                info = ydl.extract_info(query, download=False)
                
                # Handle playlist
                if 'entries' in info:
                    info = info['entries'][0]
                
                song_info = {
                    'url': info['webpage_url'],
                    'title': info['title'],
                    'duration': f"{info.get('duration', 0) // 60}:{info.get('duration', 0) % 60:02d}",
                    'thumbnail': info.get('thumbnail'),
                    'requester': ctx.author.mention
                }
            
            queue = get_music_queue(guild_id)
            voice_client = voice_clients[guild_id]
            
            # If nothing is playing, play immediately
            if not voice_client.is_playing():
                queue.append(song_info)
                await play_next(ctx)
            else:
                # Add to queue
                queue.append(song_info)
                
                embed = discord.Embed(
                    title="➕ Added to Queue",
                    description=f"**[{song_info['title']}]({song_info['url']})**",
                    color=discord.Color.blue()
                )
                embed.add_field(name="Position", value=f"#{len(queue)}", inline=True)
                embed.add_field(name="Duration", value=song_info['duration'], inline=True)
                if song_info.get('thumbnail'):
                    embed.set_thumbnail(url=song_info['thumbnail'])
                
                await ctx.reply(embed=embed)
                
        except Exception as e:
            logger.error(f"Error adding song: {str(e)}")
            await ctx.reply(f"❌ Error: {str(e)}")

@bot.command(name='pause')
async def pause_music(ctx):
    """Pause currently playing music"""
    guild_id = str(ctx.guild.id)
    
    if guild_id not in voice_clients or not voice_clients[guild_id].is_connected():
        await ctx.reply("❌ Bot is not in a voice channel!")
        return
    
    voice_client = voice_clients[guild_id]
    
    if voice_client.is_playing():
        voice_client.pause()
        await ctx.reply("⏸️ Paused music")
    else:
        await ctx.reply("❌ Nothing is playing!")

@bot.command(name='resume')
async def resume_music(ctx):
    """Resume paused music"""
    guild_id = str(ctx.guild.id)
    
    if guild_id not in voice_clients or not voice_clients[guild_id].is_connected():
        await ctx.reply("❌ Bot is not in a voice channel!")
        return
    
    voice_client = voice_clients[guild_id]
    
    if voice_client.is_paused():
        voice_client.resume()
        await ctx.reply("▶️ Resumed music")
    else:
        await ctx.reply("❌ Music is not paused!")

@bot.command(name='skip')
async def skip_music(ctx):
    """Skip current song"""
    guild_id = str(ctx.guild.id)
    
    if guild_id not in voice_clients or not voice_clients[guild_id].is_connected():
        await ctx.reply("❌ Bot is not in a voice channel!")
        return
    
    voice_client = voice_clients[guild_id]
    
    if voice_client.is_playing():
        voice_client.stop()
        await ctx.reply("⏭️ Skipped song")
    else:
        await ctx.reply("❌ Nothing is playing!")

@bot.command(name='stop')
async def stop_music(ctx):
    """Stop music and clear queue"""
    guild_id = str(ctx.guild.id)
    
    if guild_id not in voice_clients or not voice_clients[guild_id].is_connected():
        await ctx.reply("❌ Bot is not in a voice channel!")
        return
    
    voice_client = voice_clients[guild_id]
    
    # Clear queue
    if guild_id in music_queues:
        music_queues[guild_id].clear()
    now_playing.pop(guild_id, None)
    
    # Stop playing
    if voice_client.is_playing():
        voice_client.stop()
    
    await ctx.reply("⏹️ Stopped music and cleared queue")

@bot.command(name='queue')
async def show_queue(ctx):
    """Show current music queue"""
    guild_id = str(ctx.guild.id)
    queue = get_music_queue(guild_id)
    
    if not queue and guild_id not in now_playing:
        await ctx.reply("📭 Queue is empty!")
        return
    
    embed = discord.Embed(
        title="🎵 Music Queue",
        color=discord.Color.purple()
    )
    
    # Now playing
    if guild_id in now_playing:
        current = now_playing[guild_id]
        embed.add_field(
            name="🎶 Now Playing",
            value=f"**[{current['title']}]({current['url']})**\nRequested by {current['requester']}",
            inline=False
        )
    
    # Queue list
    if queue:
        queue_text = ""
        for i, song in enumerate(list(queue)[:10], 1):
            queue_text += f"`{i}.` [{song['title']}]({song['url']}) - {song['duration']}\n"
        
        if len(queue) > 10:
            queue_text += f"\n*...and {len(queue) - 10} more songs*"
        
        embed.add_field(name="📋 Up Next", value=queue_text, inline=False)
        embed.set_footer(text=f"Total songs in queue: {len(queue)}")
    else:
        embed.add_field(name="📋 Up Next", value="*Queue is empty*", inline=False)
    
    await ctx.reply(embed=embed)

@bot.command(name='nowplaying', aliases=['np'])
async def now_playing_command(ctx):
    """Show currently playing song"""
    guild_id = str(ctx.guild.id)
    
    if guild_id not in now_playing:
        await ctx.reply("❌ Nothing is playing!")
        return
    
    song = now_playing[guild_id]
    queue = get_music_queue(guild_id)
    
    embed = discord.Embed(
        title="🎵 Now Playing",
        description=f"**[{song['title']}]({song['url']})**",
        color=discord.Color.green()
    )
    embed.add_field(name="Duration", value=song['duration'], inline=True)
    embed.add_field(name="Requested by", value=song['requester'], inline=True)
    embed.add_field(name="Queue", value=f"{len(queue)} songs", inline=True)
    
    if song.get('thumbnail'):
        embed.set_thumbnail(url=song['thumbnail'])
    
    await ctx.reply(embed=embed)

@bot.command(name='disconnect', aliases=['dc'])
async def disconnect_music(ctx):
    """Disconnect bot from voice channel"""
    guild_id = str(ctx.guild.id)
    
    if guild_id not in voice_clients or not voice_clients[guild_id].is_connected():
        await ctx.reply("❌ Bot is not in a voice channel!")
        return
    
    # Clean up
    if guild_id in music_queues:
        music_queues[guild_id].clear()
    now_playing.pop(guild_id, None)
    
    await voice_clients[guild_id].disconnect()
    del voice_clients[guild_id]
    
    await ctx.reply("👋 Disconnected from voice channel")

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
        name="🎵 Music Commands",
        value=(
            "`!play <url/query>` - Play music from YouTube\n"
            "`!pause` - Pause music\n"
            "`!resume` - Resume music\n"
            "`!skip` - Skip current song\n"
            "`!stop` - Stop and clear queue\n"
            "`!queue` - Show music queue\n"
            "`!nowplaying` or `!np` - Show current song\n"
            "`!disconnect` or `!dc` - Leave voice"
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
