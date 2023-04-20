# CS:GO Item Price Tracker
### by kepper104
\
This is a Python tool that tracks the price of CS:GO items on the Steam Community Market and every morning sends a Telegram message with the price change plotted.
## Installation

1. Clone or download the repository.
2. Install the required packages with pip install -r requirements.txt.
3. Create a Telegram bot and get the bot token (Message @BotFather on Telegram to register your bot and receive its authentication token).
4. Start a conversation with the bot and get the chat ID (see [here](https://stackoverflow.com/questions/32423837/telegram-bot-how-to-get-a-group-chat-id) for instructions).
5. Open the config.py file and replace <TELEGRAM_BOT_TOKEN> with your Telegram bot token and <TELEGRAM_CHAT_ID> with your Telegram chat ID. You can also change the sending time and the list of tracked items in this file.
6. Run the script with python main.py.

## Usage

The script will run indefinitely until you stop it manually. Every hour it collects prices for all tracked items and stores them into csv files. Every morning at set time it will send a summary of price changes since last day and a plot of prices over last week.

You can change the tracked items by modifying the tracked_items list in the config.py file. Make sure to use the exact name of the case as it appears on the Steam Community Market.
