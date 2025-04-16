# Discord Bot

A simple Discord bot with slash commands built using discord.py.

## Features

### Basic Commands
- `/hello` - Says hello to the user
- `/ping` - Shows the bot's latency
- `/roll [sides]` - Rolls a dice with a specified number of sides (default: 6)
- `/flip` - Flips a coin
- `/info` - Shows information about the server
- `/avatar [user]` - Shows a user's avatar in full size
- `/weather [city]` - Gets current weather information for a city
- `/whois [user]` - Displays detailed information about a user
- `/clear [amount]` - Deletes a specified number of messages (default: 5, max: 100)
- `/help` - Shows all available commands and features

### Meme and Image Commands
- `/meme` - Gets a random meme from Reddit
- `/meme_category [category]` - Gets a meme from a specific category (programming, wholesome, dank, anime)
- `/cat` - Gets a random cat picture
- `/dog` - Gets a random dog picture
- `/imgen [prompt]` - Generates an image from your text description using AI

### Games
- `/tictactoe [opponent]` - Start a game of Tic Tac Toe with another server member

### AI Integration
- `/tlme [question]` - Ask any question and get an AI-powered response using Google's Gemini 2.0 Flash model
- `.message` - Use a period prefix in any channel to have a casual conversation with the bot (responds like a human)
- `@BotName` or reply - Mention the bot or reply to its messages to get a human-like response
- **Direct Messages** - In DMs, the bot responds to all messages without requiring any prefix or mention

## Setup Instructions

1. **Clone this repository**

2. **Install dependencies**
   ```
   pip install -r requirements.txt
   ```

3. **Create a Discord Bot**
   - Go to [Discord Developer Portal](https://discord.com/developers/applications)
   - Click "New Application" and give it a name
   - Go to the "Bot" tab and click "Add Bot"
   - Under "Privileged Gateway Intents", enable "Message Content Intent"
   - Copy the bot token

4. **Get a Google Gemini API Key**
   - Go to [Google AI Studio](https://ai.google.dev/)
   - Create a free account
   - Go to "API keys" in the left sidebar
   - Create a new API key and copy it
   - Note: Gemini offers free credits to get started (this bot uses Gemini 2.0 Flash)

5. **Get a Hugging Face API Key (for image generation)**
   - Go to [Hugging Face](https://huggingface.co/)
   - Create a free account
   - Go to your profile → Settings → Access Tokens
   - Create a new token and copy it
   - Note: Hugging Face offers free access to text-to-image models

6. **Setup Environment Variables**
   - Create a file named `.env` in the project directory
   - Add your tokens:
     ```
     DISCORD_TOKEN=your_bot_token_here
     GEMINI_API_KEY=your_gemini_api_key_here
     HUGGINGFACE_API_KEY=your_huggingface_token_here
     ```

7. **Invite the Bot to your server**
   - Go to OAuth2 -> URL Generator in the Discord Developer Portal
   - Select the "bot" and "applications.commands" scopes
   - Select permissions: "Send Messages", "Use Slash Commands", "Embed Links", "Manage Messages" (for /clear command)
   - Copy the generated URL and open it in your browser to add the bot to your server

8. **Run the bot**
   ```
   python bot.py
   ```

## Using the Conversational Bot

### Dot Prefix
You can have a casual conversation with the bot by starting your message with a dot (`.`):

Example:
```
.How's your day going?
.Tell me something funny
.What do you think about pizza?
```

### Direct Messages
When messaging the bot directly in DMs, you don't need any prefix or mention. Just send a message like you would to a friend:

Example:
```
Hello there!
What's the meaning of life?
Tell me a joke
```

The bot will respond naturally to all direct messages.

### Mentions and Replies
You can also get a human-like response by:
- Mentioning the bot: `@BotName hey there!`
- Replying to any of the bot's previous messages

The bot will respond in a casual, conversational manner like a human friend would. When replying to its messages, it remembers the context of the conversation.

## Message Management

The `/clear` command allows you to delete multiple messages at once:
- `/clear` - Deletes the last 5 messages in the channel
- `/clear 10` - Deletes the last 10 messages in the channel
- `/clear 100` - Deletes the last 100 messages (maximum allowed by Discord)

Note: Both the bot and the user must have the "Manage Messages" permission to use this command.

## User Profile Features

The `/avatar` command allows users to view profile pictures in full resolution:
- `/avatar` - Shows your own avatar in full size
- `/avatar @username` - Shows the specified user's avatar in full size

Animated avatars (GIFs) are also supported and will be displayed with their animation.

The `/whois` command provides detailed information about a server member:
- `/whois` - Shows your own user information
- `/whois @username` - Shows detailed information about the specified user

This command displays:
- Basic user details (username, ID, nickname)
- Account creation and server join dates
- Current status and activity
- Role list and key permissions
- Profile picture

## Image Generation

The `/imgen` command allows you to generate high-quality images using AI:
- `/imgen a cat playing piano` - Generates an image of a cat playing piano
- `/imgen sunset over mountains in watercolor style` - Generates a watercolor-style image of a sunset

This feature uses the Stable Diffusion model via Hugging Face's free API. The model produces high-quality images based on your text prompts.

To use this command, you'll need a Hugging Face API key:
1. Create a free account at [Hugging Face](https://huggingface.co/)
2. Go to your profile → Settings → Access Tokens
3. Create a new token and copy it
4. Add it to your `.env` file as `HUGGINGFACE_API_KEY=your_token_here`

## Getting Help

Type `/help` in any channel to see a list of available commands and features.

## Weather Information

The `/weather` command allows you to get current weather information for any city around the world:
- `/weather London` - Get current weather in London
- `/weather Tokyo` - Get current weather in Tokyo
- `/weather New York` - Get current weather in New York

This feature uses the OpenWeatherMap API to provide real-time weather data including:
- Current temperature and "feels like" temperature
- Weather conditions (sunny, cloudy, rain, etc.)
- Humidity, wind speed, and pressure
- Visibility information

To use this command, you'll need an OpenWeatherMap API key:
1. Create a free account at [OpenWeatherMap](https://openweathermap.org/)
2. Go to your account → API Keys
3. Copy your API key
4. Add it to your `.env` file as `OPENWEATHER_API_KEY=your_key_here`

## Additional Information

- This bot uses the discord.py library with slash commands
- Requires Python 3.8 or higher
- Uses external APIs to fetch memes, jokes, and animal pictures
- Integrates with Google's Gemini 2.0 Flash AI for intelligent responses 

## Games

The bot includes interactive games you can play with other server members:

### Tic Tac Toe

The `/tictactoe` command lets you challenge another member to a game of Tic Tac Toe:
- `/tictactoe @username` - Starts a game with the specified user

Game features:
- Interactive button-based gameplay
- Random selection of who goes first
- 30-second turn timer
- Option to abandon the game
- Rematch functionality when a game ends 