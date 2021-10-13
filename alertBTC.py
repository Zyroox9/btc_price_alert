import requests
import smtplib
from twilio.rest import Client
from dotenv import load_dotenv
import os

load_dotenv()

# asset setup
ASSET_SYMBOL = "BTC"
ASSET_NAME = "bitcoin"
ALERT_PERCENT_THRESH = 2

# API setup 1) https://www.alphavantage.co   2) https://newsapi.org
AV_KEY = os.getenv("AV_KEY")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

# mail setup
MAIL_FROM = os.getenv("MAIL_FROM")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
MAIL_TO = os.getenv("MAIL_TO")
SMTP_HOST = os.getenv("SMTP_HOST")

# sms setup
TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
SMS_FROM = os.getenv("SMS_FROM")
SMS_TO = os.getenv("SMS_TO")


# STEP 1: API statystyki - https://www.alphavantage.co
AV_ENDPOINT = "https://www.alphavantage.co/query"

PRICE_PARAMS = {
    "function": "CRYPTO_INTRADAY",
    "symbol": ASSET_SYMBOL,
    "market": "USD",
    "interval": "15min",
    "apikey": AV_KEY
}

RSI_PARAMS = {
    "function": "RSI",
    "symbol": f"{ASSET_SYMBOL}USD",
    "interval": "weekly",
    "time_period": "14",
    "series_type": "close",
    "apikey": AV_KEY
}

SMA_PARAMS = {
    "function": "SMA",
    "symbol": f"{ASSET_SYMBOL}USD",
    "interval": "weekly",
    "time_period": "20",
    "series_type": "close",
    "apikey": AV_KEY
}


def get_biggest_move():
    response = requests.get(url=AV_ENDPOINT, params=PRICE_PARAMS)
    response.raise_for_status()
    stock_data = response.json()["Time Series Crypto (15min)"]
    close_prices = {timestamp: float(record["4. close"]) for (timestamp, record) in stock_data.items()}
    max_price_ts = max(close_prices, key=close_prices.get)
    min_price_ts = min(close_prices, key=close_prices.get)
    max_price = round(close_prices[max_price_ts])
    min_price = round(close_prices[min_price_ts])
    current_price = round(list(close_prices.values())[0])
    if max_price_ts > min_price_ts:
        max_diff = round((max_price / min_price - 1) * 100, 1)
    else:
        max_diff = round((min_price / max_price - 1) * 100, 1)
    return max_diff, current_price, min_price, max_price


def get_rsi():
    response = requests.get(url=AV_ENDPOINT, params=RSI_PARAMS)
    response.raise_for_status()
    rsi_data = [round(float(value['RSI']), 1) for (key, value) in response.json()['Technical Analysis: RSI'].items()]
    last_3_rsi = f"Trzy ostatnie RSI: {rsi_data[2]} -> {rsi_data[1]} -> {rsi_data[0]}"
    return last_3_rsi


def get_sma():
    response = requests.get(url=AV_ENDPOINT, params=SMA_PARAMS)
    response.raise_for_status()
    sma_data = [float(value['SMA']) for (key, value) in response.json()['Technical Analysis: SMA'].items()]
    current_sma = f"Aktualna SMA(20W): {round(sma_data[0])}$"
    return current_sma


# STEP 2: API newsy - https://newsapi.org
NEWS_ENDPOINT = "https://newsapi.org/v2/everything"

NEWS_PARAMS = {
    "qInTitle": ASSET_NAME,
    "sortBy": "publishedAt",
    "language": "en",
    "apiKey": NEWS_API_KEY
}


def get_news():
    response = requests.get(url=NEWS_ENDPOINT, params=NEWS_PARAMS)
    response.raise_for_status()
    articles = {article['title']: article['url'] for article in response.json()['articles']}
    first_articles = list(articles.items())[:5]
    return first_articles


# STEP 3: SETUP maili - https://www.gmail.com
def send_email(first_articles, max_diff, last_3_rsi, current_sma, current_price):
    news_txt = "".join([f"Title: {article[0]}\nLink: {article[1]}\n\n" for article in first_articles])
    symbol = "🔺" if max_diff > 0 else "🔻"

    msg = f"Subject: {ASSET_SYMBOL} {symbol}{abs(max_diff)}% -> {current_price}$\n\n{current_sma}\n{last_3_rsi}\n\nNewsy:\n\n{news_txt}"

    with smtplib.SMTP(SMTP_HOST) as connection:
        connection.starttls()
        connection.login(user=MAIL_FROM, password=MAIL_PASSWORD)
        connection.sendmail(from_addr=MAIL_FROM, to_addrs=MAIL_TO, msg=msg.encode("utf8"))


# STEP 4: SETUP SMS - https://www.twilio.com
def send_sms(first_articles, max_diff, last_3_rsi, current_sma, current_price):
    short_news_txt = "".join([f"{article[0]}\n\n" for article in first_articles[:3]])
    symbol = "🔺" if max_diff > 0 else "🔻"
    msg = f"\n{ASSET_SYMBOL} {symbol}{abs(max_diff)}% -> {current_price}$\n\n{current_sma}\n{last_3_rsi}\n\nNewsy:\n{short_news_txt}"

    client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)
    message = client.messages.create(
        body=msg.encode("utf8"),
        from_=SMS_FROM,
        to=SMS_TO
    )


# STEP 5: Program
max_diff, current_price, min_price, max_price = get_biggest_move()

if abs(max_diff) > ALERT_PERCENT_THRESH:
    last_3_rsi = get_rsi()
    current_sma = get_sma()
    first_articles = get_news()

    send_email(first_articles, max_diff, last_3_rsi, current_sma, current_price)
    # send_sms(first_articles, max_diff, last_3_rsi, current_sma, current_price)

