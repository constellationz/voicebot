# Voicebot

A discord bot that speaks in voice chat

# Installation

- For voice chat commands to work, install ffmpeg
- On Windows, use `winget install -e --id Gyan.FFmpeg`
- On Linux, install `ffmpeg`

# Configuration

1. Make a file named `.env`
2. Paste the code block below into the file
3. Replace everything in quotes (keep the quotes) with your bot's information
4. Replace `MOD_ID` with your server's Mod/Admin role id
5. Replace `TEXT_CHANNEL_ID` with your server's main text channel's id
6. Replace `VC_CHANNEL_ID` with your server's main voice channel's id

```
BOT_TOKEN="YourTokenHere"
PERM_INT="YourPermIntHere"
PUBLIC_KEY="YourKeyHere"
APP_ID="YourAppIdHere"
MOD_ID='YourModRoleIdHere'
CHANNEL_ID='YourBotChannelIdHere'
```

# Running the bot

Type `python3 main.py` to start the bot

# Usage

All commands require the prefix `v!`
