import asyncio
import pandas as pd
import yfinance as yf
from telegram import Bot
from datetime import datetime, timedelta, timezone

# ========= CONFIG =========
TOKEN = "8652056910:AAE4Z9E8Du6BiZoHPeugJvt7ksmhC9mlt0g"

CHAT_IDS = [
    "6725248203",
    "7189407746",
    "7012611005",
    "7507688010"
]

# Only strong, major currency pairs
SYMBOLS = [
    "EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", 
    "USDCAD=X", "USDCHF=X", "NZDUSD=X", 
    "EURJPY=X", "GBPJPY=X", "GBPAUD=X"
]

MAX_SIGNALS_PER_DAY = 10  # limit signals per day
bot = Bot(token=TOKEN)
signal_active = False
signals_sent_today = 0

# ========= TELEGRAM MESSAGE =========
async def send_message(text):
    for chat in CHAT_IDS:
        try:
            await bot.send_message(chat_id=chat, text=text)
        except Exception as e:
            print("Telegram error:", e)

# ========= GET MARKET DATA =========
def get_data(symbol):
    try:
        df = yf.download(symbol, interval="5m", period="1d")
        if df.empty or len(df) < 2:
            return None
        return df
    except Exception as e:
        print(f"Error fetching data for {symbol}: {e}")
        return None

# ========= RSI CALCULATION =========
def calculate_rsi(df, period=14):
    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=period, min_periods=1).mean()
    avg_loss = loss.rolling(window=period, min_periods=1).mean()
    rs = avg_gain / avg_loss.replace(0, 0.0001)
    df["RSI"] = 100 - (100 / (1 + rs))
    return df

# ========= CANDLE PATTERN SIGNAL =========
def check_pattern(df):
    """
    Detects strong bullish/bearish engulfing pattern.
    Returns signal type ("BUY"/"SELL") and strength ("strong"/"moderate")
    """
    last = df.iloc[-1]
    prev = df.iloc[-2]

    last_body = abs(last['Close'] - last['Open'])
    prev_body = abs(prev['Close'] - prev['Open'])
    candle_range = last['High'] - last['Low'] if last['High'] != last['Low'] else 0.0001

    # Strong bullish
    if last['Close'] > last['Open'] and last_body > 0.6 * candle_range:
        if prev['Close'] < prev['Open']:
            return "BUY", "strong"
        return "BUY", "moderate"

    # Strong bearish
    if last['Close'] < last['Open'] and last_body > 0.6 * candle_range:
        if prev['Close'] > prev['Open']:
            return "SELL", "strong"
        return "SELL", "moderate"

    return None, None

# ========= CHECK RESULT =========
async def check_result(symbol, direction, entry, expiry_minutes):
    await asyncio.sleep(expiry_minutes * 60)
    df = get_data(symbol)
    if df is None:
        return "UNKNOWN"
    close_price = float(df["Close"].iloc[-1])
    if direction == "BUY":
        return "WIN" if close_price > entry else "LOSS"
    if direction == "SELL":
        return "WIN" if close_price < entry else "LOSS"

# ========= WAIT UNTIL NEXT CANDLE =========
async def wait_for_next_candle():
    now = datetime.now(timezone(timedelta(hours=1)))  # UTC+1
    next_candle = (now + timedelta(minutes=5 - now.minute % 5)).replace(second=0, microsecond=0)
    wait_seconds = (next_candle - now).total_seconds() - 10  # send 10s before candle
    if wait_seconds > 0:
        await asyncio.sleep(wait_seconds)

# ========= MAIN BOT =========
async def run_bot():
    global signal_active, signals_sent_today
    print("🔥 TAPSCO ELITE BOT V4 STARTED 🔥")
    await send_message("🔥 TAPSCO BOT V4 IS ACTIVE 🔥")

    while True:
        if signals_sent_today >= MAX_SIGNALS_PER_DAY:
            print("Daily signal limit reached")
            await asyncio.sleep(300)  # wait 5 min
            continue

        if signal_active:
            await asyncio.sleep(5)
            continue

        await wait_for_next_candle()

        for symbol in SYMBOLS:
            try:
                print(f"Scanning {symbol}")
                df = get_data(symbol)
                if df is None:
                    continue

                df = calculate_rsi(df)
                signal, strength = check_pattern(df)

                # RSI filter
                last_rsi = df["RSI"].iloc[-1]
                if signal == "BUY" and last_rsi > 60:
                    signal = None
                if signal == "SELL" and last_rsi < 40:
                    signal = None

                if signal and not signal_active:
                    signal_active = True
                    signals_sent_today += 1
                    entry = float(df["Close"].iloc[-1])
                    expiry = 5 if strength == "strong" else 3

                    message = f"""
🔥 TAPSCO ELITE BOT V4

PAIR: {symbol}
SIGNAL: {signal} ({strength.upper()})
ENTRY: {entry}
TIME: {datetime.now(timezone(timedelta(hours=1))):%H:%M} (UTC+1)
EXPIRY: {expiry} MIN
"""
                    await send_message(message)

                    result = await check_result(symbol, signal, entry, expiry)
                    result_msg = f"""
📊 TRADE RESULT

PAIR: {symbol}
SIGNAL: {signal}
RESULT: {result}
"""
                    await send_message(result_msg)
                    signal_active = False
                    break

            except Exception as e:
                print("Error:", e)

        await asyncio.sleep(5)

# ========= START BOT =========
asyncio.run(run_bot())
