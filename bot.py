import asyncio
import pandas as pd
import yfinance as yf
from telegram import Bot
from datetime import datetime

# ========= CONFIG =========

TOKEN = "8652056910:AAE4Z9E8Du6BiZoHPeugJvt7ksmhC9mlt0g"

CHAT_IDS = [
    "6725248203",
    "7189407746",
    "7012611005"
]

SYMBOLS = [

"EURUSD=X",
"GBPUSD=X",
"USDJPY=X",
"AUDUSD=X",
"USDCAD=X",
"USDCHF=X",
"NZDUSD=X",

"EURGBP=X",
"EURJPY=X",
"EURAUD=X",
"EURCAD=X",
"EURCHF=X",

"GBPJPY=X",
"GBPAUD=X",
"GBPCAD=X",
"GBPCHF=X",

"AUDJPY=X",
"AUDCAD=X",
"AUDCHF=X",

"CADJPY=X",
"CHFJPY=X",
"NZDJPY=X"

]

bot = Bot(token=TOKEN)

signal_active = False

# ========= TELEGRAM MESSAGE =========

async def send_message(text):
    for chat in CHAT_IDS:
        try:
            await bot.send_message(chat_id=chat, text=text)
        except Exception as e:
            print("Telegram error:", e)

# ========= GET MARKET DATA =========

def get_data(symbol):
    df = yf.download(symbol, interval="1m", period="1d")
    if df.empty:
        return None
    return df

# ========= CALCULATE EMA =========

def calculate_ema(df):
    df["EMA20"] = df["Close"].ewm(span=20).mean()
    df["EMA50"] = df["Close"].ewm(span=50).mean()
    return df

# ========= CHECK SIGNAL =========

def check_signal(df):
    last = df.iloc[-1]
    prev = df.iloc[-2]

    ema20_last = float(last["EMA20"].item())
    ema50_last = float(last["EMA50"].item())

    ema20_prev = float(prev["EMA20"].item())
    ema50_prev = float(prev["EMA50"].item())

    if ema20_prev < ema50_prev and ema20_last > ema50_last:
        return "BUY"

    if ema20_prev > ema50_prev and ema20_last < ema50_last:
        return "SELL"

    return None

# ========= CHECK RESULT =========

async def check_result(symbol, direction, entry):
    await asyncio.sleep(300)  # 5-min expiry
    df = get_data(symbol)
    if df is None:
        return "Unknown"
    close_price = float(df["Close"].iloc[-1].item())

    if direction == "BUY":
        return "WIN" if close_price > entry else "LOSS"

    if direction == "SELL":
        return "WIN" if close_price < entry else "LOSS"

# ========= MAIN BOT =========

async def run_bot():
    global signal_active
    print("🔥 TAPSCO ELITE BOT STARTED 🔥")

    while True:
        if signal_active:
            await asyncio.sleep(10)
            continue

        for symbol in SYMBOLS:
            try:
                print("Scanning", symbol)
                df = get_data(symbol)
                if df is None:
                    continue

                df = calculate_ema(df)
                signal = check_signal(df)

                if signal and not signal_active:
                    signal_active = True
                    entry = float(df["Close"].iloc[-1].item())

                    message = f"""
🔥 TAPSCO ELITE BOT

PAIR: {symbol}
SIGNAL: {signal}

ENTRY: {entry}

TIME: {datetime.now().strftime("%H:%M")}

EXPIRY: 5 MIN
"""
                    await send_message(message)

                    result = await check_result(symbol, signal, entry)

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

        await asyncio.sleep(40)

# ========= START BOT =========

asyncio.run(run_bot())