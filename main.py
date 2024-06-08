import os
import re
import sys
import time
import uuid
import ctypes
import random
import asyncio
import discord
import pyttsx3
import yt_dlp
import traceback
import urllib.request
from discord import Member, VoiceChannel
from discord.ext import commands, tasks
from datetime import datetime, timedelta
from dotenv import load_dotenv
load_dotenv()

ytdlp_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0', # bind to ipv4 since ipv6 addresses cause issues sometimes
    'extract_audio': True,
}

ffmpeg_options = {
    'options': '-vn',
}

ytdl = yt_dlp.YoutubeDL(ytdlp_format_options)
audiodir = 'audio'
permInt = os.getenv('PERM_INT')
appId = os.getenv('APP_ID')
token = os.getenv('BOT_TOKEN')

# playsThisPlayer 
def playThisPlayer(ctx, player):
    ctx.voice_client.play(player, after=lambda e: print(f'Player error: {e}') if e else None)

# SAY IT!
def sayit(ctx, message=None, after=None):
    if message is None:
        return

    print(f"Saying '{message}'")

    # Create unique speech audio file
    filename = uuid.uuid4()
    file = f'{audiodir}/{filename}.mp3'

    # Create engine
    engine = pyttsx3.init()
    # voices = engine.getProperty('voices')
    # engine.setProperty('voice', voices[1].id)
    engine.save_to_file(message, file)
    engine.runAndWait()
    time.sleep(0.1)

    # Speak Utterance
    source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(file))
    ctx.voice_client.play(source, after=after)

async def playUrl(bot, ctx, url):
    async with ctx.typing():
        player = await YTDLSource.from_url(url, loop=bot.loop)
        sayit(ctx, f'Now playing: {player.title}', after=lambda e: playThisPlayer(ctx, player))
    await ctx.send(f'Now playing: {player.title}')

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

class SimpleCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def invite(self, ctx):
        await ctx.send('https://discord.com/oauth2/authorize/?permissions='+ permInt +'&scope=bot&client_id=' + appId)

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def join(self, ctx, *, channel: discord.VoiceChannel):
        """Joins a voice channel"""
        if ctx.voice_client is not None:
            return await ctx.voice_client.move_to(channel)

        await channel.connect()

    @commands.command()
    async def speak(self, ctx, *, message=None):
        """Speak a message in voice chat"""
        sayit(ctx, message)

    @commands.command()
    async def time(self, ctx, *, message=None):
        """Speak the current time"""
        currenttime = time.strftime("%A, %B ") \
                      + time.strftime("%d at ").lstrip("0") \
                      + time.strftime("%I %M %p").lstrip("0")
        sayit(ctx, f'The current time is {currenttime}')

    @commands.command()
    async def yt(self, ctx, *, url):
        """Plays from a url (almost anything youtube_dl supports)"""
        await playUrl(self.bot, ctx, url)

    @commands.command()
    async def p(self, ctx, *, query):
        """Search a video"""
        # Get first video id
        html = urllib.request.urlopen("https://www.youtube.com/results?search_query=" + query.replace(' ', '+'))
        video_ids = re.findall(r"watch\?v=(\S{11})", html.read().decode())
        if len(video_ids) == 0:
            await ctx.send(f'Could not find a video for {query}')
            return

        url = "https://www.youtube.com/watch?v=" + video_ids[0]
        # Play it
        await playUrl(self.bot, ctx, url)

    @commands.command()
    async def play(self, ctx, *, query=None):
        """Plays a file from the local filesystem"""
        message_start = "Chosen song: "

        # If no specific query, play a random song
        if query is None:
            query = self.get_random_song()
            message_start = "Random song: "

        # If query does not exist, send error
        if not os.path.exists(query):
            return await ctx.send("Error: Song Not Found")

        source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(query))
        ctx.voice_client.play(source, after=lambda e: print(f'Player error: {e}') if e else None)

        await ctx.send(f'{message_start}{query}')

    @p.before_invoke
    @yt.before_invoke
    @time.before_invoke
    @play.before_invoke
    @speak.before_invoke
    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send("You are not connected to a voice channel.")
                raise commands.CommandError("Author not connected to a voice channel.")
        elif ctx.voice_client.is_playing():
            ctx.voice_client.stop()

    @commands.command()
    async def volume(self, ctx, volume: int):
        """Changes the player's volume"""
        if ctx.voice_client is None:
            return await ctx.send("Not connected to a voice channel.")

        ctx.voice_client.source.volume = volume / 100
        await ctx.send(f"Changed volume to {volume}%")

    @commands.command()
    async def stop(self, ctx):
        """Stops and disconnects the bot from voice"""
        if ctx.voice_client is not None and ctx.voice_client.is_playing():
            ctx.voice_client.stop()

        sayit(ctx, 'Goodbye')
        time.sleep(1.0)
        await ctx.voice_client.disconnect()


    def get_random_song(self):
        """Gets a random song from the available songs"""
        songs_directory = os.path.abspath(audiodir)
        songs = [f"{audiodir}/{filename}" for filename in os.listdir(songs_directory)]
        return random.choice(songs)

    @commands.command()
    async def error(self, ctx):
        """Errors"""
        poop(10)

    @play.before_invoke
    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send("You are not connected to a voice channel.")
                raise commands.CommandError("Author not connected to a voice channel.")
        elif ctx.voice_client.is_playing():
            ctx.voice_client.stop()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix=commands.when_mentioned_or("v!"),
    description='VOICE BOT',
    intents=intents,
)

# We are SO back
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')

# This works
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MemberNotFound):
        await ctx.send("I could not find member '{error.argument}'. Please try again")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"'{error.param.name}' is a required argument.")
    else:
        print(f'*** Exception in command "{ctx.command}" ***', file=sys.stderr)
        traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)

async def main():
    async with bot:
        await bot.add_cog(SimpleCommands(bot))
        await bot.add_cog(Music(bot))
        await bot.start(token)

asyncio.run(main())
