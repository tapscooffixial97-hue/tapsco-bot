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

SYMBOLS = [
    "EURUSD=X",
    "GBPUSD=X",
    "USDJPY=X",
    "AUDUSD=X"
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
        df = yf.download(symbol, interval="1m", period="1d")
        if df.empty or len(df) < 15:
            return None
        return df
    except Exception as e:
        print(f"Error downloading {symbol}: {e}")
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

# ========= SUPPORT & RESISTANCE =========
def support_resistance(df, lookback=20):
    # Recent high/low levels
    recent_high = df["High"].rolling(lookback).max().iloc[-1]
    recent_low = df["Low"].rolling(lookback).min().iloc[-1]
    return recent_high, recent_low

# ========= CHECK CANDLE PATTERNS =========
def check_pattern(df):
    last = df.iloc[-1]
    prev = df.iloc[-2]

    body = abs(last['Close'] - last['Open'])
    prev_body = abs(prev['Close'] - prev['Open'])

    # Engulfing / strong candle detection
    if last['Close'] > last['Open'] and prev['Close'] < prev['Open'] and body > prev_body * 1.1:
        return "BUY", "strong"
    if last['Close'] < last['Open'] and prev['Close'] > prev['Open'] and body > prev_body * 1.1:
        return "SELL", "strong"
    return None, None

# ========= CHECK RESULT =========
async def check_result(symbol, direction, entry, expiry_minutes):
    await asyncio.sleep(expiry_minutes * 60)
    df = get_data(symbol)
    if df is None:
        return "UNKNOWN"
    close_price = float(df["Close"].iloc[-1].item())
    if direction == "BUY":
        return "WIN" if close_price > entry else "LOSS"
    if direction == "SELL":
        return "WIN" if close_price < entry else "LOSS"

# ========= WAIT UNTIL NEXT 1-MIN CANDLE =========
async def wait_for_next_candle():
    now = datetime.now(timezone(timedelta(hours=1)))  # UTC+1
    next_candle = (now + timedelta(minutes=1 - now.minute % 1)).replace(second=0, microsecond=0)
    wait_seconds = (next_candle - now).total_seconds() - 5  # 5s before candle
    if wait_seconds > 0:
        await asyncio.sleep(wait_seconds)

# ========= AI CONFIDENCE SCORE =========
def ai_confidence(df, signal):
    score = 0
    last_rsi = df["RSI"].iloc[-1]
    ema50 = df["Close"].ewm(span=50).mean().iloc[-1]
    price = df["Close"].iloc[-1]

    # Trend direction
    if signal == "BUY" and price > ema50:
        score += 30
    if signal == "SELL" and price < ema50:
        score += 30

    # RSI
    if signal == "BUY" and last_rsi < 70:
        score += 20
    if signal == "SELL" and last_rsi > 30:
        score += 20

    # Candle strength
    score += 25  # strong pattern already

    # Volatility
    recent_range = df["High"].iloc[-5:].max() - df["Low"].iloc[-5:].min()
    if recent_range > 0:
        score += 15

    return score

# ========= MAIN BOT =========
async def run_bot():
    global signal_active, signals_sent_today
    print("🔥 TAPSCO AI BOT V1 STARTED 🔥")
    await send_message("🔥 TAPSCO AI BOT V1 IS ACTIVE 🔥")

    while True:
        if signals_sent_today >= MAX_SIGNALS_PER_DAY:
            print("Daily signal limit reached")
            await asyncio.sleep(60)  # wait 1 min
            continue

        if signal_active:
            await asyncio.sleep(2)
            continue

        await wait_for_next_candle()

        for symbol in SYMBOLS:
            try:
                print("Scanning", symbol)
                df = get_data(symbol)
                if df is None:
                    continue

                df = calculate_rsi(df)
                signal, strength = check_pattern(df)
                if signal is None:
                    continue

                # Support & Resistance filter
                sr_high, sr_low = support_resistance(df)
                price = df["Close"].iloc[-1]

                if signal == "BUY" and price >= sr_high:
                    print(f"{symbol} BUY blocked by resistance")
                    continue
                if signal == "SELL" and price <= sr_low:
                    print(f"{symbol} SELL blocked by support")
                    continue

                # AI confidence check
                confidence = ai_confidence(df, signal)
                if confidence < 70:
                    print(f"{symbol} signal confidence {confidence}% too low")
                    continue

                if not signal_active:
                    signal_active = True
                    signals_sent_today += 1
                    entry = float(df["Close"].iloc[-1].item())
                    expiry = 2  # 2-min trade for 1-min signals

                    message = f"""
🔥 TAPSCO AI SIGNAL 🔥

PAIR: {symbol}
SIGNAL: {signal} ({strength.upper()})
CONFIDENCE: {confidence}%
ENTRY: {entry}
TIME: {datetime.now(timezone(timedelta(hours=1))):%H:%M} (UTC+1)
EXPIRY: {expiry} MIN
"""
                    await send_message(message)

                    # Check result
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

        await asyncio.sleep(2)  # short wait to loop

# ========= START BOT =========
asyncio.run(run_bot())
