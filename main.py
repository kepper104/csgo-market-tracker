import csv
import datetime
import numpy as np
import schedule as schedule
import telebot
import matplotlib.pyplot as plt
import matplotlib.dates as m_dates
import steammarket
from os.path import isfile
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, SENDING_TIME, tracked_cases

bot = telebot.TeleBot(TELEGRAM_TOKEN)

fields = ['timestamp', 'price']


def get_price(case_name):
    print("Getting price for " + case_name)
    try:
        price = steammarket.get_csgo_item(case_name, "RUB")["lowest_price"].split(" ")[0].replace(",", ".")
        print(price)
    except:
        print("Steam Market API Error!")
        price = -1
    print("Got price for " + case_name)

    return price


def write_to_csv(case_name, price_data):
    print(f"Writing {price_data} to {case_name}")
    path = f"./{case_name}.csv"

    if not isfile(path):
        with open(path, mode='a', newline='') as f:
            f.write("timestamp,price\n")

    with open(path, mode='a', newline='') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fields)
        writer.writerow(price_data)

    print("Wrote to csv successfully")


def send_graph(case_name):
    print("SENDING MESSAGE")

    with open(f"./{case_name}.csv", mode='r') as csv_file:
        reader = csv.DictReader(csv_file)
        data = []
        for row in reader:
            data.append(row)

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
    prev_day_path = "prev_day_" + case_name + ".txt"
    try:
        with open(prev_day_path, mode='r') as f:
            previous_day_price = float(f.read())
    except:
        print("No prev day price file for " + case_name + " found!")
        previous_day_price = today_price

    # Calculate the price difference from the previous day

    day_price_difference = ("+" + f"{((today_price / previous_day_price - 1) * 100):.2f}%").replace("+-", "-")
    week_price_difference = ("+" + f"{((today_price / prices[0] - 1) * 100):.2f}%").replace("+-", "-")

    day_price_diff_str = ("+" + f"{(today_price - previous_day_price):.2f}").replace("+-", "-") + "₽"
    week_price_diff_str = ("+" + f"{(today_price - prices[0]):.2f}").replace("+-", "-") + "₽"

    with open(prev_day_path, mode='w') as f:
        f.write(str(today_price))

    make_plot(data, timestamps, prices, week_price_diff_str, week_price_difference, case_name)

    message = f"{' '.join(case_name.split()[:-1])}: {day_price_diff_str} {day_price_difference} " \
              f"({previous_day_price} -> {today_price})\n "

    send_message(message, timestamps)


def send_message(message, timestamps):
    try:
        with open('price_graph.png', 'rb') as f:
            graph = f.read()
            bot.send_photo(
                TELEGRAM_CHAT_ID,
                photo=graph,
                caption=message + f'From {timestamps[0]} to {timestamps[-1]}')
        print("SENT MESSAGE")
    except:
        print("Error while sending telegram message or opening image!")


def make_plot(data, timestamps, prices, week_price_diff_str, week_price_difference, case_name):

    fig, ax = plt.subplots()
    ax.plot([row['timestamp'] for row in data], [float(row['price']) for row in data])

    # Set x-axis locator and formatter to display ticks at daily intervals
    ax.xaxis.set_major_locator(m_dates.DayLocator())
    ax.xaxis.set_major_formatter(m_dates.DateFormatter('%Y-%m-%d'))

    ax.set_xlabel('Date')
    ax.set_ylabel('Price')
    ax.set_title(f'{case_name} price over last week')

    y_ticks = np.arange(min(prices) - 1, max(prices) + 1, 0.5)
    ax.set_yticks(y_ticks)

    ax.annotate(f'Week Price Change: {week_price_diff_str} {week_price_difference}', xy=(0.6, 1.1),
                xycoords='axes fraction')

    ax.annotate(f'{prices[0]:.2f}', xy=(timestamps[0], prices[0]), xytext=(20, -10),
                textcoords='offset points', ha='right', va='top', fontsize=8,
                bbox=dict(boxstyle='round,pad=0.2', fc='yellow', alpha=0.3))

    ax.annotate(f'{prices[-1]:.2f}', xy=(timestamps[-1], prices[-1]), xytext=(0, 10),
                textcoords='offset points', ha='right', va='bottom', fontsize=8,
                bbox=dict(boxstyle='round,pad=0.2', fc='yellow', alpha=0.3))

    fig.autofmt_xdate(rotation=45)
    plt.savefig('price_graph.png')


def collect_price_data():
    for case in tracked_cases:
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        price = get_price(case)

        price_data = {'timestamp': timestamp, 'price': float(price)}
        write_to_csv(case, price_data)


def send_graphs():
    for case in tracked_cases:
        send_graph(case)


schedule.every().hour.do(collect_price_data)
schedule.every().day.at(SENDING_TIME).do(send_graphs)

while True:
    schedule.run_pending()
