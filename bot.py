import os
import discord
import random
import aiohttp
import requests
import google.generativeai as genai
from discord import app_commands
from dotenv import load_dotenv
import traceback
from datetime import datetime
import asyncio
import pathlib
import re

print("Starting Discord bot initialization...")

# Create logs directory if it doesn't exist
logs_dir = pathlib.Path("logs")
logs_dir.mkdir(exist_ok=True)

# Load environment variables
print("Loading environment variables...")
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
HUGGINGFACE_API_KEY = os.getenv('HUGGINGFACE_API_KEY')
OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY')

# Debug prints for troubleshooting
print(f"Discord Token loaded: {'Yes' if TOKEN else 'No'}")
print(f"Gemini API Key loaded: {'Yes' if GEMINI_API_KEY else 'No'}")
print(f"Hugging Face API Key loaded: {'Yes' if HUGGINGFACE_API_KEY else 'No'}")
print(f"OpenWeather API Key loaded: {'Yes' if OPENWEATHER_API_KEY else 'No'}")
print(f"Hugging Face API Key value: {HUGGINGFACE_API_KEY[:4]}...{HUGGINGFACE_API_KEY[-4:] if HUGGINGFACE_API_KEY and len(HUGGINGFACE_API_KEY) > 8 else '(too short)'}")

# Check for placeholder values
if TOKEN == "your_bot_token_here":
    print("Error: You need to replace 'your_bot_token_here' with your actual Discord bot token in the .env file")
    exit(1)

# Set up Gemini
try:
    genai.configure(api_key=GEMINI_API_KEY)
    # Set up the model - using gemini-1.5-flash (Gemini 2.0 Flash)
    gemini_model = genai.GenerativeModel('gemini-2.0-flash')
    # Test the model with a simple query
    response = gemini_model.generate_content("Hello")
    ai_working = True
    print("Gemini API connection successful using gemini-2.0-flash model")
except Exception as e:
    ai_working = False
    print(f"Gemini API initialization error: {str(e)}")
    print("The /tlme command will be disabled due to Gemini API issues")

# Set up intents
intents = discord.Intents.default()
intents.message_content = True

# Create bot client
class MyClient(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.synced = False
        
    async def on_ready(self):
        await self.wait_until_ready()
        if not self.synced:
            await tree.sync()
            self.synced = True
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print('------')
    
    # Helper method to get conversation log file path
    def get_log_file_path(self, user_id):
        # Create a universal log file for each user: logs/users/user_id.txt
        users_dir = logs_dir / "users"
        users_dir.mkdir(exist_ok=True)
        
        return users_dir / f"{user_id}.txt"
    
    # Load conversation history from log file
    def load_conversation_history(self, user_id):
        log_file = self.get_log_file_path(user_id)
        
        try:
            if log_file.exists():
                with open(log_file, 'r', encoding='utf-8') as f:
                    log_content = f.read()
                
                return log_content
            else:
                return ""
        except Exception as e:
            print(f"Error loading conversation history: {e}")
            return ""
    
    # Add a new message to the conversation log
    def append_to_conversation_log(self, user_id, message_info, sender, message):
        log_file = self.get_log_file_path(user_id)
        
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Create the log entry with location information
            log_entry = f"[{timestamp}] [{message_info}] {sender}: {message}\n\n"
            
            # Append to the log file
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)
                
            return True
        except Exception as e:
            print(f"Error appending to conversation log: {e}")
            return False
    
    # Format conversation history for the AI context
    def format_conversation_for_ai(self, history):
        if not history:
            return ""
        
        # Return the full conversation history without trimming
        return history
    
    # Function to filter out log content from responses
    def clean_response(self, response_text):
        # Check if the response accidentally includes log-formatted content
        if re.search(r'\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\]', response_text):
            print("Warning: Bot response contained log-like timestamp format. Cleaning response.")
            
            # Extract only the meaningful part of the response
            # Look for patterns that indicate it's trying to repeat conversation history
            lines = response_text.split('\n')
            cleaned_lines = []
            
            # Skip log-formatted lines and history markers
            skip_line = False
            for line in lines:
                # Skip timestamp lines
                if re.search(r'\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\]', line):
                    skip_line = True
                    continue
                    
                # Skip lines that look like log entries
                if re.search(r'\[.*\] (USER|BOT):', line):
                    skip_line = True
                    continue
                    
                # Skip lines that are clearly indicating history
                if any(marker in line.lower() for marker in [
                    "conversation history", 
                    "chat history",
                    "previous messages",
                    "our conversation",
                    "earlier conversation",
                    "from our previous"
                ]):
                    skip_line = True
                    continue
                    
                # If we're skipping but encounter an empty line, stop skipping
                if skip_line and not line.strip():
                    skip_line = False
                    continue
                    
                # Add non-skipped lines
                if not skip_line:
                    cleaned_lines.append(line)
            
            # If we filtered out too much, look for the actual response at the end
            if not cleaned_lines or "".join(cleaned_lines).strip() == "":
                # Try to find the actual response by looking for the last portion after timestamps
                parts = re.split(r'\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\].*?(?=\n|$)', response_text)
                if parts and parts[-1].strip():
                    cleaned_response = parts[-1].strip()
                else:
                    # Fallback if nothing works
                    cleaned_response = "I understand your message, but I'm having trouble formulating a proper response. Could you try asking again in a different way?"
            else:
                cleaned_response = "\n".join(cleaned_lines)
                
            return cleaned_response.strip()
        
        return response_text

    async def on_message(self, message):
        # Don't respond to our own messages
        if message.author == self.user:
            return
            
        # Handle DMs - respond to all messages without prefix or mention
        if isinstance(message.channel, discord.DMChannel):
            query = message.content.strip()
            
            # Skip empty messages
            if not query:
                return
                
            # Send "typing" indicator
            async with message.channel.typing():
                if ai_working:
                    try:
                        location_info = "Direct Message"
                        
                        # Load this user's conversation history
                        conversation_history = self.load_conversation_history(message.author.id)
                        
                        # Format for AI context
                        context = self.format_conversation_for_ai(conversation_history)
                        
                        # Log the user's message before generating a response
                        self.append_to_conversation_log(
                            message.author.id,
                            location_info,
                            "USER",
                            query
                        )
                        
                        # Call Gemini API with conversation history included
                        prompt = f"""You are responding as a friendly, casual person in a Discord chat. 
                        Keep your response conversational, relatable, and authentic, like a real friend would talk.
                        Use some casual language, emoji, or slang where appropriate, but don't overdo it.
                        Avoid sounding formal or robotic. Don't mention AI, models or prompts.
                        
                        I'll provide you with conversation history with this user, but DO NOT repeat or reference the 
                        raw log format in your response. Your response should be natural and not quote timestamp entries.
                        Do not include any timestamps or log markers like [2023-01-01 12:00:00] in your response.
                        
                        Here is the conversation history with this user for context only:
                        {context}
                        
                        The user is currently messaging in {location_info}.
                        
                        Respond ONLY with your direct reply to: "{query}"
                        Do not include or repeat the conversation history in your response.
                        """
                        
                        response = gemini_model.generate_content(prompt)
                        reply_text = response.text
                        
                        # Clean the response to remove any log-like content
                        reply_text = self.clean_response(reply_text)
                        
                        # Trim if too long
                        if len(reply_text) > 2000:
                            reply_text = reply_text[:1997] + "..."
                        
                        # Send the response as a normal message, not a reply
                        await message.channel.send(reply_text)
                        
                        # Log the bot's response
                        self.append_to_conversation_log(
                            message.author.id,
                            location_info,
                            "BOT",
                            reply_text
                        )
                        
                    except Exception as e:
                        print(f"Error generating DM response: {str(e)}")
                        traceback.print_exc()
                        await message.channel.send("Sorry, I'm having trouble thinking right now. Try again later?")
                else:
                    await message.channel.send("Sorry, I can't chat right now. Try again later?")
                
            # Return early for DMs to avoid checking other conditions
            return
            
        # Check if the message starts with "." (prefix for conversational responses)
        if message.content.startswith('.'):
            # Get the message content without the prefix
            query = message.content[1:].strip()
            
            # Skip empty messages
            if not query:
                return
                
            # Send "typing" indicator
            async with message.channel.typing():
                if ai_working:
                    try:
                        # Get message location info
                        if message.guild:
                            location_info = f"Server: {message.guild.name}, Channel: {message.channel.name}"
                        else:
                            location_info = "Direct Message"
                        
                        # Load this user's conversation history (universal)
                        conversation_history = self.load_conversation_history(message.author.id)
                        
                        # Format for AI context
                        context = self.format_conversation_for_ai(conversation_history)
                        
                        # Log the user's message before generating a response
                        self.append_to_conversation_log(
                            message.author.id,
                            location_info,
                            "USER",
                            query
                        )
                        
                        # Call Gemini API with conversation history included
                        prompt = f"""You are responding as a friendly, casual person in a Discord chat. 
                        Keep your response conversational, relatable, and authentic, like a real friend would talk.
                        Use some casual language, emoji, or slang where appropriate, but don't overdo it.
                        Avoid sounding formal or robotic. Don't mention AI, models or prompts.
                        
                        I'll provide you with conversation history with this user, but DO NOT repeat or reference the 
                        raw log format in your response. Your response should be natural and not quote timestamp entries.
                        Do not include any timestamps or log markers like [2023-01-01 12:00:00] in your response.
                        
                        Here is the conversation history with this user for context only:
                        {context}
                        
                        The user is currently messaging in {location_info}.
                        
                        Respond ONLY with your direct reply to: "{query}"
                        Do not include or repeat the conversation history in your response.
                        """
                        
                        response = gemini_model.generate_content(prompt)
                        reply_text = response.text
                        
                        # Clean the response to remove any log-like content
                        reply_text = self.clean_response(reply_text)
                        
                        # Trim if too long
                        if len(reply_text) > 2000:
                            reply_text = reply_text[:1997] + "..."
                        
                        # Send the response
                        await message.reply(reply_text)
                        
                        # Log the bot's response
                        self.append_to_conversation_log(
                            message.author.id,
                            location_info,
                            "BOT",
                            reply_text
                        )
                        
                    except Exception as e:
                        print(f"Error generating conversational response: {str(e)}")
                        traceback.print_exc()
                        await message.reply("Sorry, I'm having trouble thinking right now. Try again later?")
                else:
                    await message.reply("Sorry, I can't chat right now. Try again later?")
        
        # Check if the bot was mentioned or if the message is a reply to the bot's message
        elif self.user.mentioned_in(message) or (message.reference and message.reference.resolved and message.reference.resolved.author.id == self.user.id):
            # Skip messages with command prefixes, as these might be intended for other bots
            if message.content.startswith(('/', '!', '?', '-', '>')):
                return
                
            # Get the content - remove the mention for cleaner input
            query = message.content.replace(f'<@{self.user.id}>', '').strip()
            if not query and message.reference:
                # If they just pinged the bot with no content but it's a reply, use "hi" as default
                query = "hi"
            elif not query:
                # If they just pinged the bot with no content, use their greeting as context
                query = "hello"
            
            # Send "typing" indicator
            async with message.channel.typing():
                if ai_working:
                    try:
                        # Get message location info
                        if message.guild:
                            location_info = f"Server: {message.guild.name}, Channel: {message.channel.name}"
                        else:
                            location_info = "Direct Message"
                        
                        # Load this user's conversation history (universal)
                        conversation_history = self.load_conversation_history(message.author.id)
                        
                        # Format for AI context
                        context = self.format_conversation_for_ai(conversation_history)
                        
                        direct_context = ""
                        # If it's a reply to the bot, add the original message as context
                        if message.reference and message.reference.resolved:
                            original_message = message.reference.resolved
                            if original_message.author.id == self.user.id:
                                direct_context = f"This is a reply to your previous message where you said: '{original_message.content}'. "
                        
                        # Log the user's message before generating a response
                        self.append_to_conversation_log(
                            message.author.id,
                            location_info,
                            "USER",
                            query
                        )
                        
                        # Call Gemini API with a prompt to act like a casual, friendly human
                        prompt = f"""You are responding as a friendly, casual person in a Discord chat.
                        {direct_context}Someone has mentioned you or replied to your message. 
                        Keep your response conversational, relatable, and authentic, like a real friend would talk.
                        Use some casual language, emoji, or slang where appropriate, but don't overdo it.
                        Avoid sounding formal or robotic. Don't mention AI, models or prompts.
                        
                        I'll provide you with conversation history with this user, but DO NOT repeat or reference the 
                        raw log format in your response. Your response should be natural and not quote timestamp entries.
                        Do not include any timestamps or log markers like [2023-01-01 12:00:00] in your response.
                        
                        Here is the conversation history with this user for context only:
                        {context}
                        
                        The user is currently messaging in {location_info}.
                        
                        Respond ONLY with your direct reply to: "{query}"
                        Do not include or repeat the conversation history in your response.
                        """
                        
                        response = gemini_model.generate_content(prompt)
                        reply_text = response.text
                        
                        # Clean the response to remove any log-like content
                        reply_text = self.clean_response(reply_text)
                        
                        # Trim if too long
                        if len(reply_text) > 2000:
                            reply_text = reply_text[:1997] + "..."
                        
                        # Send the response
                        await message.reply(reply_text)
                        
                        # Log the bot's response
                        self.append_to_conversation_log(
                            message.author.id,
                            location_info,
                            "BOT",
                            reply_text
                        )
                        
                    except Exception as e:
                        print(f"Error generating mention response: {str(e)}")
                        traceback.print_exc()
                        await message.reply("Sorry, I'm having trouble thinking right now. Try again later?")
                else:
                    await message.reply("Sorry, I can't chat right now. Try again later?")

client = MyClient()
tree = app_commands.CommandTree(client)

# Define slash commands
@tree.command(name="hello", description="Says hello to you")
async def hello_command(interaction: discord.Interaction):
    await interaction.response.send_message(f"Hello, {interaction.user.mention}!")

@tree.command(name="ping", description="Check bot latency")
async def ping_command(interaction: discord.Interaction):
    latency = round(client.latency * 1000)
    await interaction.response.send_message(f"Pong! Latency: {latency}ms")

@tree.command(name="roll", description="Roll a dice")
@app_commands.describe(sides="Number of sides on the dice")
async def roll_command(interaction: discord.Interaction, sides: int = 6):
    result = random.randint(1, sides)
    await interaction.response.send_message(f"🎲 You rolled a {result}!")

@tree.command(name="flip", description="Flip a coin")
async def flip_command(interaction: discord.Interaction):
    result = "Heads" if random.choice([0, 1]) == 0 else "Tails"
    await interaction.response.send_message(f"🪙 {result}!")

@tree.command(name="info", description="Get information about the server")
async def info_command(interaction: discord.Interaction):
    guild = interaction.guild
    embed = discord.Embed(title=f"{guild.name} Info", color=discord.Color.blue())
    embed.add_field(name="Server ID", value=guild.id, inline=True)
    embed.add_field(name="Created On", value=guild.created_at.strftime("%b %d, %Y"), inline=True)
    embed.add_field(name="Owner", value=guild.owner.mention if guild.owner else "Unknown", inline=True)
    embed.add_field(name="Members", value=guild.member_count, inline=True)
    embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
    await interaction.response.send_message(embed=embed)

# Avatar command
@tree.command(name="avatar", description="View a user's profile picture in a larger size")
@app_commands.describe(user="The user whose avatar you want to see (leave empty for your own)")
async def avatar_command(interaction: discord.Interaction, user: discord.Member = None):
    # If no user is provided, use the command invoker
    target_user = user or interaction.user
    
    # Create an embed with the avatar
    embed = discord.Embed(
        title=f"{target_user.display_name}'s Avatar",
        color=discord.Color.random()
    )
    
    # Get the avatar URL with the largest size (4096 pixels)
    avatar_url = target_user.display_avatar.with_size(4096).url
    
    # Add the avatar to the embed
    embed.set_image(url=avatar_url)
    
    # Add footer with timestamp
    embed.set_footer(text=f"Requested by {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
    
    # Add some additional info
    if target_user.avatar:
        if target_user.avatar.is_animated():
            embed.description = "This is an animated avatar (GIF)"
    
    # Send the embed
    await interaction.response.send_message(embed=embed)

# Clear messages command
@tree.command(name="clear", description="Delete a specified number of messages")
@app_commands.describe(amount="Number of messages to delete (1-100)")
async def clear_command(interaction: discord.Interaction, amount: int = 5):
    # Check permissions
    if not interaction.channel.permissions_for(interaction.guild.me).manage_messages:
        await interaction.response.send_message("I don't have permission to delete messages in this channel.", ephemeral=True)
        return
        
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
        return
    
    # Validate amount
    if amount < 1:
        await interaction.response.send_message("Please provide a positive number of messages to delete.", ephemeral=True)
        return
    
    if amount > 100:
        amount = 100  # Discord API limit
        
    # Defer response to avoid timeout
    await interaction.response.defer(ephemeral=True)
    
    try:
        # Delete messages
        deleted = await interaction.channel.purge(limit=amount)
        
        # Send confirmation
        await interaction.followup.send(f"✅ Successfully deleted {len(deleted)} messages.", ephemeral=True)
    except discord.errors.Forbidden:
        await interaction.followup.send("I don't have permission to delete some of these messages.", ephemeral=True)
    except Exception as e:
        print(f"Error deleting messages: {str(e)}")
        await interaction.followup.send(f"An error occurred while deleting messages: {str(e)}", ephemeral=True)

# Help command
@tree.command(name="help", description="Show all available commands and features")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Bot Commands & Features",
        description="Here's everything I can do!",
        color=discord.Color.blue()
    )
    
    # Basic Commands Section
    basic_commands = (
        "`/hello` - Says hello to you\n"
        "`/ping` - Shows the bot's latency\n"
        "`/roll [sides]` - Rolls a dice with a specified number of sides (default: 6)\n"
        "`/flip` - Flips a coin\n"
        "`/info` - Shows information about the server\n"
        "`/avatar [user]` - Shows a user's avatar in full size\n"
        "`/whois [user]` - Displays detailed information about a user\n"
        "`/weather [city]` - Gets current weather information for a city\n"
        "`/clear [amount]` - Deletes a specified number of messages (default: 5)\n"
        "`/help` - Shows this help message"
    )
    embed.add_field(name="📋 Basic Commands", value=basic_commands, inline=False)
    
    # Meme and Image Commands Section
    meme_commands = (
        "`/meme` - Gets a random meme from Reddit\n"
        "`/meme_category [category]` - Gets a meme from a specific category\n"
        "`/cat` - Gets a random cat picture\n"
        "`/dog` - Gets a random dog picture\n"
        "`/imgen [prompt]` - Generate an image from your text description"
    )
    embed.add_field(name="🖼️ Meme & Image Commands", value=meme_commands, inline=False)
    
    # Games Section
    games_commands = (
        "`/tictactoe [opponent]` - Start a game of Tic Tac Toe with another server member"
    )
    embed.add_field(name="🎮 Games", value=games_commands, inline=False)
    
    # AI Integration Section
    ai_commands = (
        "`/tlme [question]` - Ask any question and get an AI-powered response\n"
        "`.message` - Use a period prefix in any channel to have a casual conversation\n"
        "@mention or reply - Mention the bot or reply to its messages for a human-like response\n"
        "**Direct Messages** - In DMs, just message normally with no prefix needed"
    )
    embed.add_field(name="🤖 AI Features", value=ai_commands, inline=False)
    
    # Examples Section
    examples = (
        "`/meme_category programming` - Get a programming meme\n"
        "`/roll 20` - Roll a 20-sided dice\n"
        "`/clear 10` - Delete the last 10 messages in the channel\n"
        "`/avatar @username` - View someone's profile picture\n"
        "`/whois @username` - Get detailed info about a server member\n"
        "`/weather Tokyo` - Check the current weather in Tokyo\n"
        "`/tlme Explain quantum computing` - Get an explanation of quantum computing\n"
        "`/imgen a cat riding a skateboard` - Generate an AI image\n"
        "`/tictactoe @username` - Challenge someone to Tic Tac Toe\n"
        "`.How's your day going?` - Have a casual conversation\n"
        "@BotName hey there - Ping the bot for a response\n"
        "DM: \"Hello there!\" - Message the bot directly without prefixes"
    )
    embed.add_field(name="💡 Examples", value=examples, inline=False)
    
    # Set footer
    embed.set_footer(text="Need more help? Contact the server admin.")
    
    await interaction.response.send_message(embed=embed)

# Gemini integration
@tree.command(name="tlme", description="Ask a question and get an AI-powered response using Google's Gemini 2.0 Flash")
@app_commands.describe(question="The question or prompt you want to ask")
async def tlme_command(interaction: discord.Interaction, question: str):
    global ai_working
    
    if not ai_working:
        await interaction.response.send_message(
            "Sorry, the AI response feature is currently unavailable. Please check the Gemini API key and try again later.", 
            ephemeral=True
        )
        return

    await interaction.response.defer(thinking=True)
    
    try:
        # Call Gemini API
        response = gemini_model.generate_content(question)
        
        # Format and trim the response if needed
        response_text = response.text
        if len(response_text) > 4000:
            response_text = response_text[:3997] + "..."
        
        # Create an embed for the response
        embed = discord.Embed(
            title="Gemini 2.0 Flash Response",
            description=response_text,
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Question by {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        error_message = str(e)
        print(f"Gemini API Error: {error_message}")
        
        user_message = f"Sorry, I encountered an error when generating a response: {error_message}"
        await interaction.followup.send(user_message, ephemeral=True)

# New meme commands
@tree.command(name="meme", description="Get a random meme from Reddit")
async def meme_command(interaction: discord.Interaction):
    await interaction.response.defer()
    async with aiohttp.ClientSession() as session:
        async with session.get('https://meme-api.com/gimme') as response:
            if response.status == 200:
                data = await response.json()
                embed = discord.Embed(
                    title=data['title'],
                    url=data['postLink'],
                    color=discord.Color.random()
                )
                embed.set_image(url=data['url'])
                embed.set_footer(text=f"👍 {data['ups']} | From r/{data['subreddit']}")
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send("Couldn't fetch a meme right now. Try again later.")

@tree.command(name="cat", description="Get a random cat picture")
async def cat_command(interaction: discord.Interaction):
    await interaction.response.defer()
    async with aiohttp.ClientSession() as session:
        async with session.get('https://api.thecatapi.com/v1/images/search') as response:
            if response.status == 200:
                data = await response.json()
                embed = discord.Embed(
                    title="Random Cat",
                    color=discord.Color.gold()
                )
                embed.set_image(url=data[0]['url'])
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send("Couldn't fetch a cat picture right now. Try again later.")

@tree.command(name="dog", description="Get a random dog picture")
async def dog_command(interaction: discord.Interaction):
    await interaction.response.defer()
    async with aiohttp.ClientSession() as session:
        async with session.get('https://api.thedogapi.com/v1/images/search') as response:
            if response.status == 200:
                data = await response.json()
                embed = discord.Embed(
                    title="Random Dog",
                    color=discord.Color.green()
                )
                embed.set_image(url=data[0]['url'])
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send("Couldn't fetch a dog picture right now. Try again later.")

@tree.command(name="meme_category", description="Get a meme from a specific category")
@app_commands.describe(category="Category of meme (programming, wholesome, dank, anime)")
async def meme_category_command(interaction: discord.Interaction, category: str):
    await interaction.response.defer()
    
    # Map categories to subreddits
    subreddit_map = {
        "programming": "ProgrammerHumor",
        "wholesome": "wholesomememes",
        "dank": "dankmemes",
        "anime": "animememes",
    }
    
    # Default to dankmemes if category not found
    subreddit = subreddit_map.get(category.lower(), "dankmemes")
    
    async with aiohttp.ClientSession() as session:
        async with session.get(f'https://meme-api.com/gimme/{subreddit}') as response:
            if response.status == 200:
                data = await response.json()
                embed = discord.Embed(
                    title=data['title'],
                    url=data['postLink'],
                    color=discord.Color.random()
                )
                embed.set_image(url=data['url'])
                embed.set_footer(text=f"👍 {data['ups']} | From r/{data['subreddit']}")
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send(f"Couldn't fetch a {category} meme right now. Try again later.")

# Image generation command using Hugging Face's API
@tree.command(name="imgen", description="Generate an image from your text prompt")
@app_commands.describe(prompt="Describe the image you want to generate")
async def imgen_command(interaction: discord.Interaction, prompt: str):
    print(f"\n--- IMAGE GENERATION REQUEST ---")
    print(f"User: {interaction.user.name} (ID: {interaction.user.id})")
    print(f"Prompt: {prompt}")
    
    # Check if Hugging Face API key is set
    if not HUGGINGFACE_API_KEY:
        print("Error: Hugging Face API key not found")
        await interaction.response.send_message(
            "The image generation feature is not available. Please add a Hugging Face API key to the .env file.",
            ephemeral=True
        )
        return
    
    # Defer response since image generation can take time
    await interaction.response.defer(thinking=True)
    print("Response deferred - bot is 'thinking'")
    
    try:
        # Print debug info
        print(f"Starting image generation process...")
        print(f"API Key being used: {HUGGINGFACE_API_KEY[:4]}...{HUGGINGFACE_API_KEY[-4:]}")
        
        # Using Stable Diffusion XL via Hugging Face API
        API_URL = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
        headers = {
            "Authorization": f"Bearer {HUGGINGFACE_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Prepare the payload
        payload = {"inputs": prompt}
        
        print(f"Making API request to: {API_URL}")
        print(f"Headers: {headers}")
        print(f"Payload: {payload}")
        
        # Make the API request with timeout
        print("Sending request to Hugging Face API...")
        response = requests.post(API_URL, headers=headers, json=payload, timeout=90)
        
        print(f"Response received!")
        print(f"Status code: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        
        # Check if the response is successful
        if response.status_code == 200:
            print(f"Successful response (200)")
            print(f"Content type: {response.headers.get('Content-Type', 'unknown')}")
            print(f"Content length: {len(response.content)} bytes")
            
            # Check if the response is actually an image
            if response.headers.get('Content-Type', '').startswith('image/'):
                print("Response contains image data, saving...")
                # Save the image temporarily
                image_filename = f"generated_image_{interaction.id}.png"
                with open(image_filename, "wb") as image_file:
                    image_file.write(response.content)
                print(f"Image saved to {image_filename}")
                
                # Create a Discord file object
                file = discord.File(image_filename, filename="generated_image.png")
                
                # Create an embed
                embed = discord.Embed(
                    title="Generated Image",
                    description=f"**Prompt:** {prompt}",
                    color=discord.Color.purple()
                )
                embed.set_image(url="attachment://generated_image.png")
                embed.set_footer(text=f"Generated by Stable Diffusion XL • Requested by {interaction.user.display_name}", 
                                icon_url=interaction.user.display_avatar.url)
                
                # Send the embed with the image
                print("Sending image to Discord...")
                await interaction.followup.send(embed=embed, file=file)
                print("Image sent successfully!")
                
                # Clean up the temporary file
                try:
                    os.remove(image_filename)
                    print(f"Temporary file {image_filename} removed")
                except Exception as cleanup_error:
                    print(f"Error cleaning up temporary file: {cleanup_error}")
            
            # Handle case where response is JSON (possibly an error)
            elif response.headers.get('Content-Type', '').startswith('application/json'):
                print("Response contains JSON data instead of an image")
                try:
                    error_data = response.json()
                    print(f"JSON content: {error_data}")
                    
                    error_message = "The API returned JSON data instead of an image."
                    if "error" in error_data:
                        error_message = f"API Error: {error_data['error']}"
                    elif "estimated_time" in error_data:
                        wait_time = error_data.get('estimated_time', 'unknown')
                        error_message = f"Model is currently loading (wait ~{wait_time} seconds). Please try again soon."
                    
                    print(f"Sending error message to user: {error_message}")
                    await interaction.followup.send(f"Failed to generate the image. {error_message}", ephemeral=True)
                except Exception as json_error:
                    print(f"Error parsing JSON response: {json_error}")
                    print(f"Raw response content: {response.content[:500]}...")
                    await interaction.followup.send("Failed to generate the image. The API returned an unexpected response format.", ephemeral=True)
            else:
                print(f"Unexpected content type in response: {response.headers.get('Content-Type', 'unknown')}")
                print(f"First 500 bytes of response: {response.content[:500]}...")
                await interaction.followup.send("Failed to generate the image. The API returned an unexpected content type.", ephemeral=True)
            
        else:
            # Handle API errors
            print(f"Error response received: {response.status_code}")
            error_message = f"Error: API returned status code {response.status_code}"
            try:
                error_data = response.json()
                print(f"Error response JSON: {error_data}")
                if "error" in error_data:
                    error_message = f"API Error: {error_data['error']}"
            except Exception as parse_error:
                print(f"Error parsing error response: {parse_error}")
                print(f"Raw error response: {response.text[:500]}")
            
            print(f"Final error message: {error_message}")
            await interaction.followup.send(f"Failed to generate the image. {error_message}", ephemeral=True)
            
    except requests.exceptions.Timeout:
        print("Request timed out after 90 seconds")
        await interaction.followup.send("The image generation request timed out. The service might be overloaded. Please try again later.", ephemeral=True)
    except Exception as e:
        print(f"Unexpected exception during image generation:")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        print("Full traceback:")
        traceback.print_exc()
        
        # Provide more helpful error messages based on common issues
        user_message = "Error generating image: "
        
        if "401" in str(e) or "unauthorized" in str(e).lower():
            user_message += "Invalid API key. Please check your Hugging Face API key."
        elif "429" in str(e) or "rate limit" in str(e).lower():
            user_message += "Rate limit exceeded. Please try again later."
        elif "503" in str(e) or "service unavailable" in str(e).lower():
            user_message += "The image generation service is currently overloaded. Please try again later."
        elif "connection" in str(e).lower() or "timeout" in str(e).lower():
            user_message += "Network connection issue. Please try again later."
        else:
            user_message += f"{str(e)}"
        
        print(f"Sending error message to user: {user_message}")
        await interaction.followup.send(user_message, ephemeral=True)
    
    print("--- IMAGE GENERATION REQUEST COMPLETED ---\n")

# Weather command
@tree.command(name="weather", description="Get current weather information for a city")
@app_commands.describe(city="The city name to get weather for (e.g., 'London', 'New York', 'Tokyo')")
async def weather_command(interaction: discord.Interaction, city: str):
    # Check if OpenWeather API key is set
    if not OPENWEATHER_API_KEY:
        await interaction.response.send_message(
            "The weather feature is not available. Please add an OpenWeatherMap API key to the .env file.",
            ephemeral=True
        )
        return
    
    # First, acknowledge the interaction to avoid timeouts
    await interaction.response.defer(thinking=True)
    
    try:
        print(f"Fetching weather for city: {city}")
        
        # Call the OpenWeatherMap API to get current weather
        base_url = "https://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": city,
            "appid": OPENWEATHER_API_KEY,
            "units": "metric"  # Use metric for Celsius
        }
        
        # Make the API request
        response = requests.get(base_url, params=params, timeout=15)
        
        # Check if the response is successful
        if response.status_code == 200:
            # Parse the weather data
            weather_data = response.json()
            
            # Extract the main weather information
            weather_main = weather_data["weather"][0]["main"]
            weather_description = weather_data["weather"][0]["description"]
            temperature = weather_data["main"]["temp"]
            feels_like = weather_data["main"]["feels_like"]
            humidity = weather_data["main"]["humidity"]
            wind_speed = weather_data["wind"]["speed"]
            country = weather_data["sys"]["country"]
            city_name = weather_data["name"]
            
            # Get weather icon code and create URL
            icon_code = weather_data["weather"][0]["icon"]
            icon_url = f"https://openweathermap.org/img/wn/{icon_code}@2x.png"
            
            # Get timestamp of data calculation and convert to readable format
            timestamp = weather_data["dt"]
            time_string = datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S UTC')
            
            # Convert metrics for better readability
            wind_speed_kmh = wind_speed * 3.6  # Convert m/s to km/h
            
            # Create an embed for the weather information
            embed = discord.Embed(
                title=f"Weather in {city_name}, {country}",
                description=f"**{weather_main}**: {weather_description.capitalize()}",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            
            # Add weather information fields
            embed.add_field(name="Temperature", value=f"{temperature:.1f}°C", inline=True)
            embed.add_field(name="Feels Like", value=f"{feels_like:.1f}°C", inline=True)
            embed.add_field(name="Humidity", value=f"{humidity}%", inline=True)
            embed.add_field(name="Wind Speed", value=f"{wind_speed_kmh:.1f} km/h", inline=True)
            
            # Add pressure if available
            if "pressure" in weather_data["main"]:
                pressure = weather_data["main"]["pressure"]
                embed.add_field(name="Pressure", value=f"{pressure} hPa", inline=True)
            
            # Add visibility if available (convert from meters to km)
            if "visibility" in weather_data:
                visibility = weather_data["visibility"] / 1000
                embed.add_field(name="Visibility", value=f"{visibility:.1f} km", inline=True)
            
            # Set the weather icon as the thumbnail
            embed.set_thumbnail(url=icon_url)
            
            # Add footer with data timestamp
            embed.set_footer(text=f"Data from OpenWeatherMap • Last updated: {time_string}", 
                            icon_url="https://openweathermap.org/themes/openweathermap/assets/vendor/owm/img/icons/logo_60x60.png")
            
            # Send the embed
            await interaction.followup.send(embed=embed)
            print(f"Weather data sent successfully for {city_name}, {country}")
            
        elif response.status_code == 404:
            await interaction.followup.send(f"City '{city}' not found. Please check the spelling and try again.", ephemeral=True)
        else:
            error_data = response.json() if response.content else {"message": "Unknown error"}
            error_message = error_data.get("message", "Unknown error")
            await interaction.followup.send(f"Error fetching weather data: {error_message}", ephemeral=True)
            
    except Exception as e:
        print(f"Error in weather command: {str(e)}")
        traceback.print_exc()
        await interaction.followup.send(f"Error fetching weather data: {str(e)}", ephemeral=True)

# User information command
@tree.command(name="whois", description="Display detailed information about a user")
@app_commands.describe(user="The user you want to get information about")
async def whois_command(interaction: discord.Interaction, user: discord.Member = None):
    # If no user is provided, use the command invoker
    target_user = user or interaction.user
    
    # Create an embed with user information
    embed = discord.Embed(
        title=f"User Information: {target_user.display_name}",
        color=target_user.color if target_user.color.value else discord.Color.blue(),
        timestamp=datetime.utcnow()
    )
    
    # Add user's avatar as thumbnail
    embed.set_thumbnail(url=target_user.display_avatar.url)
    
    # Basic information
    embed.add_field(name="Username", value=f"{target_user.name}", inline=True)
    embed.add_field(name="User ID", value=f"{target_user.id}", inline=True)
    embed.add_field(name="Nickname", value=f"{target_user.nick or 'None'}", inline=True)
    
    # Time information
    created_at = int(target_user.created_at.timestamp())
    joined_at = int(target_user.joined_at.timestamp()) if target_user.joined_at else "Unknown"
    
    embed.add_field(name="Account Created", value=f"<t:{created_at}:F>\n(<t:{created_at}:R>)", inline=False)
    
    if joined_at != "Unknown":
        embed.add_field(name="Joined Server", value=f"<t:{joined_at}:F>\n(<t:{joined_at}:R>)", inline=False)
    
    # Status and activity
    status_map = {
        discord.Status.online: "🟢 Online",
        discord.Status.idle: "🟡 Idle",
        discord.Status.dnd: "🔴 Do Not Disturb",
        discord.Status.offline: "⚫ Offline/Invisible",
        None: "⚫ Unknown"
    }
    
    status = status_map.get(target_user.status, "⚫ Unknown")
    embed.add_field(name="Status", value=status, inline=True)
    
    # Check if user is bot
    is_bot = "Yes" if target_user.bot else "No"
    embed.add_field(name="Bot", value=is_bot, inline=True)
    
    # User activity
    if target_user.activity:
        activity_type = str(target_user.activity.type).split('.')[-1].title()
        activity_name = target_user.activity.name
        activity_text = f"{activity_type} {activity_name}"
        embed.add_field(name="Activity", value=activity_text, inline=True)
    
    # Roles information
    roles = [role.mention for role in target_user.roles if role.name != "@everyone"]
    roles_text = ", ".join(roles) if roles else "No roles"
    
    # If roles list is too long, truncate it
    if len(roles_text) > 1024:
        roles_text = roles_text[:1021] + "..."
    
    embed.add_field(name=f"Roles [{len(roles)}]", value=roles_text, inline=False)
    
    # Server-specific permissions
    key_permissions = []
    permissions = target_user.guild_permissions
    
    if permissions.administrator:
        key_permissions.append("Administrator")
    else:
        if permissions.manage_guild:
            key_permissions.append("Manage Server")
        if permissions.manage_roles:
            key_permissions.append("Manage Roles")
        if permissions.manage_channels:
            key_permissions.append("Manage Channels")
        if permissions.manage_messages:
            key_permissions.append("Manage Messages")
        if permissions.manage_webhooks:
            key_permissions.append("Manage Webhooks")
        if permissions.manage_nicknames:
            key_permissions.append("Manage Nicknames")
        if permissions.kick_members:
            key_permissions.append("Kick Members")
        if permissions.ban_members:
            key_permissions.append("Ban Members")
        if permissions.mention_everyone:
            key_permissions.append("Mention Everyone")
    
    if key_permissions:
        embed.add_field(name="Key Permissions", value=", ".join(key_permissions), inline=False)
    
    # Add footer
    embed.set_footer(text=f"Requested by {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
    
    await interaction.response.send_message(embed=embed)

# TicTacToe Command - Game between two players
class TicTacToeButton(discord.ui.Button):
    def __init__(self, x: int, y: int):
        super().__init__(style=discord.ButtonStyle.secondary, label="\u200b", row=y)
        self.x = x
        self.y = y

    async def callback(self, interaction: discord.Interaction):
        view: TicTacToeView = self.view
        
        # Check if it's this player's turn
        if view.current_player != interaction.user:
            await interaction.response.send_message("It's not your turn!", ephemeral=True)
            return

        # Check if the game has already ended
        if view.winner is not None:
            await interaction.response.send_message("The game is already over!", ephemeral=True)
            return

        # Place the mark
        if self.label != "\u200b":  # If button is already clicked
            await interaction.response.send_message("That space is already taken!", ephemeral=True)
            return

        # Cancel the turn timer since a move was made
        if view.turn_timer_task and not view.turn_timer_task.done():
            view.turn_timer_task.cancel()

        # Set the button with X or O
        self.label = view.current_symbol
        self.style = discord.ButtonStyle.danger if view.current_symbol == "X" else discord.ButtonStyle.success
        self.disabled = True
        
        # Update the board state
        view.board[self.y][self.x] = view.current_symbol
        
        # Check for a winner
        winner = view.check_winner()
        if winner:
            view.winner = winner
            
            # Disable all buttons and keep the game board visible
            for child in view.children:
                child.disabled = True
            
            # Remove the Abandon button
            for child in view.children[:]:
                if isinstance(child, view.AbandonGameButton):
                    view.remove_item(child)
            
            # Determine win message
            if winner == "Tie":
                result_message = "**Game Over! It's a tie!**"
            else:
                result_message = f"**Game Over! {interaction.user.mention} wins as {view.current_symbol}!**"
            
            # Update the game message with final result
            await interaction.response.edit_message(content=result_message, view=view)
            
            # Create a new message with New Game and Cancel options
            new_game_view = GameResultView(view.player_x, view.player_o, interaction.channel)
            await interaction.channel.send(
                f"Game finished! {view.player_x.mention} vs {view.player_o.mention}\nStart a new game?",
                view=new_game_view
            )
            return
        
        # Switch to the next player
        view.current_symbol = "O" if view.current_symbol == "X" else "X"
        view.current_player = view.player_o if view.current_player == view.player_x else view.player_x
        
        # Start the turn timer for the next player
        await interaction.response.edit_message(
            content=f"It's {view.current_player.mention}'s turn ({view.current_symbol})\n⏱️ Time remaining: 30 seconds", 
            view=view
        )
        
        # Start the turn timer
        view.turn_timer_task = asyncio.create_task(view.turn_timer(interaction))

class TicTacToeView(discord.ui.View):
    def __init__(self, player_x: discord.Member, player_o: discord.Member):
        super().__init__(timeout=1800)  # 30 minute total game timeout
        
        # Randomly decide which player goes first
        if random.choice([True, False]):
            self.player_x = player_x
            self.player_o = player_o 
            self.current_player = player_x
            self.first_player = player_x
        else:
            # Swap the players if second player goes first
            self.player_x = player_o  
            self.player_o = player_x
            self.current_player = player_o
            self.first_player = player_o
            
        self.current_symbol = "X"
        self.winner = None
        self.turn_timer_task = None
        self.message = None
        
        # Initialize the board (3x3 grid)
        self.board = [["\u200b" for _ in range(3)] for _ in range(3)]
        
        # Add the tic-tac-toe buttons (3x3 grid)
        for y in range(3):
            for x in range(3):
                self.add_item(TicTacToeButton(x, y))
                
        # Add only Abandon button during active game
        self.add_item(self.AbandonGameButton())
    
    async def turn_timer(self, interaction):
        """Timer that ends the game if a player doesn't move within 30 seconds"""
        try:
            # Wait for 30 seconds
            await asyncio.sleep(30)
            
            # If we get here, the timer wasn't cancelled, meaning no move was made
            if self.winner is None:
                # Mark the current game as over
                self.winner = "Timeout"
                
                # Disable all buttons to gray them out
                for child in self.children:
                    child.disabled = True
                
                # Remove the Abandon button
                for child in self.children[:]:
                    if isinstance(child, self.AbandonGameButton):
                        self.remove_item(child)
                
                # Update the message to show timeout
                timeout_message = f"**Game Over! {self.current_player.mention} took too long to make a move.**"
                
                try:
                    # Update the original game message
                    await self.message.edit(content=timeout_message, view=self)
                    
                    # Create a new message with new game options
                    new_game_view = GameResultView(self.player_x, self.player_o, self.message.channel)
                    await self.message.channel.send(
                        f"Game finished! {self.player_x.mention} vs {self.player_o.mention}\nStart a new game?",
                        view=new_game_view
                    )
                except Exception as e:
                    print(f"Error sending timeout results: {e}")
        except asyncio.CancelledError:
            # Timer was cancelled because a move was made
            pass
        except Exception as e:
            print(f"Error in turn timer: {e}")
    
    def check_winner(self):
        # Check rows
        for row in self.board:
            if row[0] != "\u200b" and row[0] == row[1] == row[2]:
                return row[0]
        
        # Check columns
        for x in range(3):
            if self.board[0][x] != "\u200b" and self.board[0][x] == self.board[1][x] == self.board[2][x]:
                return self.board[0][x]
        
        # Check diagonals
        if self.board[0][0] != "\u200b" and self.board[0][0] == self.board[1][1] == self.board[2][2]:
            return self.board[0][0]
        if self.board[0][2] != "\u200b" and self.board[0][2] == self.board[1][1] == self.board[2][0]:
            return self.board[0][2]
        
        # Check for a tie
        if all(self.board[y][x] != "\u200b" for y in range(3) for x in range(3)):
            return "Tie"
        
        return None
    
    async def on_timeout(self):
        if self.turn_timer_task and not self.turn_timer_task.done():
            self.turn_timer_task.cancel()
            
        # Disable all buttons
        for child in self.children:
            child.disabled = True
        
        try:
            # Try to edit the message content to show the game timed out
            await self.message.edit(content="⏱️ **Game timed out!** No activity for 30 minutes.", view=self)
        except:
            pass
            
    class AbandonGameButton(discord.ui.Button):
        def __init__(self):
            super().__init__(style=discord.ButtonStyle.danger, label="Abandon Game", row=3)
        
        async def callback(self, interaction: discord.Interaction):
            view: TicTacToeView = self.view
            
            # Verify it's one of the players
            if interaction.user not in [view.player_x, view.player_o]:
                await interaction.response.send_message("Only players in the game can abandon it!", ephemeral=True)
                return
            
            # Cancel the turn timer if active
            if view.turn_timer_task and not view.turn_timer_task.done():
                view.turn_timer_task.cancel()
                
            # Mark as abandoned
            view.winner = "Abandoned"
                
            # Disable all buttons to gray them out
            for child in view.children:
                child.disabled = True
            
            # Remove this button
            view.remove_item(self)
            
            # Update message
            await interaction.response.edit_message(
                content=f"**Game abandoned by {interaction.user.mention}!**", 
                view=view
            )
            
            # Create a new message with New Game and Cancel options
            new_game_view = GameResultView(view.player_x, view.player_o, interaction.channel)
            await interaction.channel.send(
                f"Game abandoned! {view.player_x.mention} vs {view.player_o.mention}\nStart a new game?",
                view=new_game_view
            )

# View that shows after a game ends
class GameResultView(discord.ui.View):
    def __init__(self, player_x: discord.Member, player_o: discord.Member, channel):
        super().__init__(timeout=300)  # 5 minute timeout for decision
        self.player_x = player_x
        self.player_o = player_o
        self.channel = channel
        self.add_item(self.NewGameButton())
        self.add_item(self.CancelButton())
        
    async def on_timeout(self):
        # Disable buttons after timeout
        for child in self.children:
            child.disabled = True
            
        try:
            await self.message.edit(content="Game options timed out.", view=self)
        except:
            pass
            
    class NewGameButton(discord.ui.Button):
        def __init__(self):
            super().__init__(style=discord.ButtonStyle.primary, label="New Game", row=0)
            
        async def callback(self, interaction: discord.Interaction):
            view: GameResultView = self.view
            
            # Verify it's one of the players
            if interaction.user not in [view.player_x, view.player_o]:
                await interaction.response.send_message("Only players in the game can start a new game!", ephemeral=True)
                return
                
            # Start a new game in this message with randomized first player
            new_game_view = TicTacToeView(view.player_x, view.player_o)
            
            # Update message with the randomly chosen first player
            await interaction.response.edit_message(
                content=f"Tic Tac Toe: {new_game_view.player_x.mention} (X) vs {new_game_view.player_o.mention} (O)\nIt's {new_game_view.current_player.mention}'s turn ({new_game_view.current_symbol})\n⏱️ Time remaining: 30 seconds",
                view=new_game_view
            )
            
            # Store the message reference
            new_game_view.message = await interaction.original_response()
            
            # Start the turn timer
            new_game_view.turn_timer_task = asyncio.create_task(new_game_view.turn_timer(interaction))
            
    class CancelButton(discord.ui.Button):
        def __init__(self):
            super().__init__(style=discord.ButtonStyle.danger, label="Cancel", row=0)
            
        async def callback(self, interaction: discord.Interaction):
            view: GameResultView = self.view
            
            # Verify it's one of the players
            if interaction.user not in [view.player_x, view.player_o]:
                await interaction.response.send_message("Only players in the game can cancel!", ephemeral=True)
                return
                
            # Disable all buttons
            for child in view.children:
                child.disabled = True
                
            # Update message
            await interaction.response.edit_message(content="Game cancelled.", view=view)

@tree.command(name="tictactoe", description="Start a game of Tic Tac Toe with another player")
@app_commands.describe(opponent="The player you want to challenge")
async def tictactoe_command(interaction: discord.Interaction, opponent: discord.Member):
    # Check if user is trying to play against themselves
    if opponent.id == interaction.user.id:
        await interaction.response.send_message("You can't play against yourself!", ephemeral=True)
        return
    
    # Check if opponent is a bot
    if opponent.bot:
        await interaction.response.send_message("You can't play against a bot!", ephemeral=True)
        return
    
    # Create the view - player assignment and first turn are randomized inside the view
    view = TicTacToeView(interaction.user, opponent)
    
    # Display initial message with randomized first player
    await interaction.response.send_message(
        f"Tic Tac Toe: {view.player_x.mention} (X) vs {view.player_o.mention} (O)\nIt's {view.current_player.mention}'s turn ({view.current_symbol})\n⏱️ Time remaining: 30 seconds",
        view=view
    )
    
    # Store the message for timeout handling
    view.message = await interaction.original_response()
    
    # Start the turn timer for the first player
    view.turn_timer_task = asyncio.create_task(view.turn_timer(interaction))

# Start the bot
if __name__ == "__main__":
    if TOKEN is None or TOKEN == "your_bot_token_here":
        print("Error: No valid Discord token found. Please set the DISCORD_TOKEN environment variable in the .env file.")
        print("You need to get a real Discord bot token from the Discord Developer Portal.")
    else:
        try:
            print("\n=== STARTING BOT ===")
            print(f"Bot will connect to Discord with token: {TOKEN[:5]}...{TOKEN[-5:]}")
            print("Running client.run()...")
            client.run(TOKEN)
        except discord.errors.LoginFailure as e:
            print(f"Error: Failed to login to Discord: {e}")
            print("Check if your Discord token is correct in the .env file.")
        except Exception as e:
            print(f"Unexpected error starting bot: {e}")
            print("Full traceback:")
            traceback.print_exc()
            print("\nPlease fix the issues above and try again.") 
            