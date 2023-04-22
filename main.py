import csv
import datetime
import schedule
import logging
import numpy as np

from telebot import TeleBot
import matplotlib.pyplot as plt
import matplotlib.dates as m_dates
from matplotlib.ticker import MaxNLocator
from steammarket import get_csgo_item
from os.path import isfile
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, SENDING_TIME, tracked_items

bot = TeleBot(TELEGRAM_TOKEN)

fields = ['timestamp', 'price']

# Create and configure logger
logging.basicConfig(filename="cs_log.log",
                    format='%(asctime)s %(message)s',
                    filemode='a')
# Creating an object
logger = logging.getLogger()

# Setting the threshold of logger to DEBUG
logger.setLevel(logging.DEBUG)


def get_price(item_name):
    logger.debug("Getting price for " + item_name)
    try:
        price = get_csgo_item(item_name, "RUB")["lowest_price"].split(" ")[0].replace(",", ".")
        logger.debug(price)
    except:
        logger.critical("Steam Market API Error!")
        price = -1
    logger.debug("Got price for " + item_name)

    return price


def write_to_csv(item_name, price_data):
    logger.debug(f"Writing {price_data} to {item_name}")
    path = f"./{item_name}.csv"

    # If file doesn't exist, create it and put in headers
    if not isfile(path):
        with open(path, mode='a', newline='') as f:
            f.write("timestamp,price\n")

    # Write the latest timestamp and price
    with open(path, mode='a', newline='') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fields)
        writer.writerow(price_data)

    logger.debug("Wrote to csv successfully")


def send_graph(item_name):
    logger.debug("Sending message")
    # Read csv with data on given item
    with open(f"./{item_name}.csv", mode='r') as csv_file:
        reader = csv.DictReader(csv_file)
        data = []
        for row in reader:
            data.append(row)

    # Format the data
    for row in data:
        row['timestamp'] = datetime.datetime.strptime(row['timestamp'], '%Y-%m-%d %H:%M:%S')
        row['price'] = float(row['price'])

    # Get the last week of data
    last_week_data = [row for row in data if row['timestamp'] >= datetime.datetime.now() - datetime.timedelta(days=7)]

    # Get the prices and timestamps for the last week of data
    prices = [row['price'] for row in last_week_data]
    timestamps = [row['timestamp'] for row in last_week_data]
    today_price = prices[-1]

    # Load the previous day's price from a file
    prev_day_path = "prev_day_" + item_name + ".txt"
    try:
        with open(prev_day_path, mode='r') as f:
            previous_day_price = float(f.read())
    except FileNotFoundError:
        logger.warning("No prev day price file for " + item_name + " found! Creating one.")
        previous_day_price = today_price

    # Calculate the price difference in RUB and percents from the previous day and week
    day_price_difference = ("+" + f"{((today_price / previous_day_price - 1) * 100):.2f}%").replace("+-", "-")
    week_price_difference = ("+" + f"{((today_price / prices[0] - 1) * 100):.2f}%").replace("+-", "-")

    day_price_diff_str = ("+" + f"{(today_price - previous_day_price):.2f}").replace("+-", "-") + "₽"
    week_price_diff_str = ("+" + f"{(today_price - prices[0]):.2f}").replace("+-", "-") + "₽"

    # Write new previous price for given item
    # with open(prev_day_path, mode='w') as f:
    #     f.write(str(today_price))

    # Construct image with price plotted over last week
    make_plot(data, timestamps, prices, week_price_diff_str, week_price_difference, item_name)

    # Construct message with quick access data
    message = f"{item_name}: {day_price_diff_str} {day_price_difference} " \
              f"({previous_day_price} -> {today_price})\n "
    # Example:
    # Glove Case: -0.22₽ -0.04% (506.26 -> 506.04)
    # From 2023-04-20 00:04:56 to 2023-04-20 00:18:37

    # Send a telegram message
    send_message(message, timestamps)


def send_message(message, timestamps):
    try:
        with open('price_graph.png', 'rb') as f:
            graph = f.read()
            try:
                bot.send_photo(
                    TELEGRAM_CHAT_ID,
                    photo=graph,
                    caption=message + f'From {timestamps[0]} to {timestamps[-1]}')
            except Exception as e:
                logger.critical("Error while sending a telegram message:", e)

        logger.debug("Sent message")

    except Exception as e:
        logger.critical("Error while opening image:", e)


def make_plot(data, timestamps, prices, week_price_diff_str, week_price_difference, item_name):
    fig, ax = plt.subplots()
    ax.plot([row['timestamp'] for row in data], [float(row['price']) for row in data])

    # Set x-axis locator and formatter to display ticks at daily intervals
    # ax.xaxis.set_major_locator(MaxNLocator(nbins=10, integer=True))
    # ax.xaxis.set_major_formatter(m_dates.DateFormatter('%I%p'))

    ax.xaxis.set_major_locator(m_dates.DayLocator())
    ax.xaxis.set_major_formatter(m_dates.DateFormatter('%Y-%m-%d'))
    
    # ax.xaxis.set_major_locator(m_dates.HourLocator())
    # ax.xaxis.set_major_formatter(m_dates.DateFormatter('%I%p'))

    # Add labels and title to image
    ax.set_xlabel('Date')
    ax.set_ylabel('Price')
    ax.set_title(f'{item_name} price over last week')

    # Set Y Ticks every 0.5 rubles
    # ax.yaxis.set_major_locator(MaxNLocator(nbins=10, integer=True))
    ticks = 15

    y_ticks = np.arange(min(prices) - 1, max(prices) + 1, (max(prices) - min(prices)) / ticks)
    ax.set_yticks(y_ticks)

    # Add week's price change in right top corner
    ax.annotate(f'Week Price Change: {week_price_diff_str} {week_price_difference}', xy=(0.6, 1.1),
                xycoords='axes fraction')

    # Add week ago price and current price on edges of graph
    ax.annotate(f'{prices[0]:.2f}', xy=(timestamps[0], prices[0]), xytext=(20, -10),
                textcoords='offset points', ha='right', va='top', fontsize=8,
                bbox=dict(boxstyle='round,pad=0.2', fc='yellow', alpha=0.3))

    ax.annotate(f'{prices[-1]:.2f}', xy=(timestamps[-1], prices[-1]), xytext=(0, 10),
                textcoords='offset points', ha='right', va='bottom', fontsize=8,
                bbox=dict(boxstyle='round,pad=0.2', fc='yellow', alpha=0.3))

    fig.autofmt_xdate(rotation=45)
    plt.savefig('price_graph.png')


def collect_price_data():
    # Collect current datetime and price for each item and write them to csv
    for item in tracked_items:
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        price = get_price(item)

        price_data = {'timestamp': timestamp, 'price': float(price)}
        write_to_csv(item, price_data)


# Send messages for every item in tracked items list
def send_graphs():
    for item in tracked_items:
        send_graph(item)

send_graphs()
exit()
# Schedule running data collection every hour and sending data at set time
schedule.every().hour.do(collect_price_data)
schedule.every().day.at(SENDING_TIME).do(send_graphs)

# Check the scheduler
while True:
    schedule.run_pending()
