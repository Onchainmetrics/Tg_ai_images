# AI Image Generation Telegram Bot 🎨

A Telegram bot that helps users generate high-quality AI images using Leonardo.ai's API. The bot guides users through an interactive process to create images either from scratch or based on reference images.

## Features 🌟

- **Prompt Enhancement**: Automatically improves user prompts using Leonardo's API
- **Reference Image Support**: Generate images based on existing images
- **Interactive Process**: Step-by-step guidance through image generation
- **Multiple Generation Options**: Create variations or modify prompts based on results
- **High-Quality Output**: Uses Leonardo.ai's advanced image generation models

## How It Works 🔄

1. **Start**: Send `/start` to begin the conversation
2. **Initial Prompt**: Describe what you want to generate
3. **Prompt Enhancement**: Choose between enhanced or original prompt
4. **Reference Image**: Option to upload a reference image
5. **Generation**: Bot generates the image using Leonardo.ai
6. **Iteration**: Option to generate variations or modify prompt

## Setup 🛠️

1. Clone the repository:

```
git clone https://github.com/yourusername/telegram-ai-image-bot.git
cd telegram-ai-image-bot
```

2. Install dependencies:
```
pip install -r requirements.txt
```
4. Create a `.env` file with your API keys:
TELEGRAM_TOKEN=your_telegram_bot_token
LEO_API_KEY=your_leonardo_ai_api_key

5. Run the bot:
```
python bot.py
```
   
## Requirements 📋

- Python 3.7+
- python-telegram-bot
- requests
- python-dotenv
- Leonardo.ai API key
- Telegram Bot token

## Environment Variables 🔑

- `TELEGRAM_TOKEN`: Your Telegram Bot API token
- `LEO_API_KEY`: Your Leonardo.ai API key

## Contributing 🤝

Feel free to submit issues and enhancement requests!
