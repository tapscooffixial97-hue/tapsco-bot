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

PAIR = "XAUUSD=X"  # Gold
MAX_SIGNALS_PER_DAY = 5  # limit daily signals
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
def get_data(symbol, interval="5m", period="1d"):
    df = yf.download(symbol, interval=interval, period=period)
    if df.empty:
        return None
    return df

# ========= 4H TREND DETECTION =========
def detect_4h_trend(df_4h):
    highs = df_4h['High'].tail(10)
    lows = df_4h['Low'].tail(10)

    if highs.iloc[-1] > highs.iloc[-2] and lows.iloc[-1] > lows.iloc[-2]:
        return "UP"
    if highs.iloc[-1] < highs.iloc[-2] and lows.iloc[-1] < lows.iloc[-2]:
        return "DOWN"
    return "SIDEWAYS"

# ========= ORDER BLOCK DETECTION =========
def detect_order_block(df_5m):
    last = df_5m.iloc[-1]
    prev = df_5m.iloc[-2]

    body = abs(last['Close'] - last['Open'])
    prev_body = abs(prev['Close'] - prev['Open'])

    # Bullish order block
    if last['Close'] > last['Open'] and prev['Close'] < prev['Open'] and body > prev_body * 1.1:
        return "BUY", last['Low'], last['High']
    # Bearish order block
    if last['Close'] < last['Open'] and prev['Close'] > prev['Open'] and body > prev_body * 1.1:
        return "SELL", last['High'], last['Low']

    return None, None, None

# ========= CHECK RESULT PLACEHOLDER =========
async def check_result(entry, direction, sl, tp):
    # For demo, just wait 5 minutes
    await asyncio.sleep(300)
    return "UNKNOWN"  # manual checking for now

# ========= WAIT UNTIL NEXT 5-MIN CANDLE =========
async def wait_for_next_candle():
    now = datetime.now(timezone(timedelta(hours=1)))  # UTC+1
    next_candle = (now + timedelta(minutes=5 - now.minute % 5)).replace(second=0, microsecond=0)
    wait_seconds = (next_candle - now).total_seconds() - 5
    if wait_seconds > 0:
        await asyncio.sleep(wait_seconds)

# ========= MAIN BOT =========
async def run_bot():
    global signal_active, signals_sent_today
    print("🔥 GOLD PRICE ACTION BOT STARTED 🔥")
    await send_message("🔥 GOLD PRICE ACTION BOT ACTIVE 🔥")

    while True:
        if signals_sent_today >= MAX_SIGNALS_PER_DAY:
            print("Daily signal limit reached")
            await asyncio.sleep(300)
            continue

        if signal_active:
            await asyncio.sleep(5)
            continue

        await wait_for_next_candle()

        try:
            # Get 4H trend
            df_4h = get_data(PAIR, interval="4h", period="10d")
            if df_4h is None or len(df_4h) < 5:
                continue
            trend = detect_4h_trend(df_4h)
            if trend == "SIDEWAYS":
                continue

            # Get 5m candles
            df_5m = get_data(PAIR, interval="5m", period="1d")
            if df_5m is None or len(df_5m) < 15:
                continue

            # Detect order block
            signal, entry_low, entry_high = detect_order_block(df_5m)
            if signal is None:
                continue

            # Only trade in direction of trend
            if (trend == "UP" and signal != "BUY") or (trend == "DOWN" and signal != "SELL"):
                continue

            signal_active = True
            signals_sent_today += 1
            entry_price = (entry_low + entry_high) / 2
            sl = entry_low - 0.5 if signal == "BUY" else entry_high + 0.5
            tp = entry_high + 1 if signal == "BUY" else entry_low - 1

            message = f"""
🔥 GOLD SETUP ALERT

SIGNAL: {signal}
ENTRY: {entry_price:.2f}
SL: {sl:.2f}
TP: {tp:.2f}
TREND (4H): {trend}
TIME: {datetime.now(timezone(timedelta(hours=1))):%H:%M} (UTC+1)
"""
            await send_message(message)

            result = await check_result(entry_price, signal, sl, tp)
            result_msg = f"""
📊 TRADE RESULT

PAIR: {PAIR}
SIGNAL: {signal}
RESULT: {result}
"""
            await send_message(result_msg)
            signal_active = False

        except Exception as e:
            print("Error:", e)

        await asyncio.sleep(5)

# ========= START BOT =========
asyncio.run(run_bot())
