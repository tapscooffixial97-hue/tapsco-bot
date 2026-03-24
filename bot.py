import asyncio
import pandas as pd
import yfinance as yf
from telegram import Bot
from datetime import datetime, timedelta

# ========= CONFIG =========
TOKEN = "8652056910:AAE4Z9E8Du6BiZoHPeugJvt7ksmhC9mlt0g"

CHAT_IDS = [
    "6725248203",
    "7189407746",
    "7012611005",
    "7507688010",
    "7514230390"
]

SYMBOLS = [
    "EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X",
    "USDCAD=X", "USDCHF=X", "NZDUSD=X"
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
    try:
        df = yf.download(symbol, interval="1m", period="1d")

        if df is None or df.empty or len(df) < 50:
            return None

        df = df.dropna()

        # 🔥 FIX: handle multi-index columns
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        if "Close" not in df.columns:
            return None

        return df

    except Exception as e:
        print("Data error:", e)
        return None

# ========= CALCULATE EMA =========
def calculate_ema(df):
    df["EMA20"] = df["Close"].ewm(span=20).mean()
    df["EMA50"] = df["Close"].ewm(span=50).mean()
    return df

# ========= SAFE FLOAT FUNCTION =========
def safe_float(value):
    try:
        if pd.isna(value):
            return None
        return float(value.item() if hasattr(value, "item") else value)
    except:
        return None

# ========= CHECK SIGNAL =========
def check_signal(df):
    try:
        last = df.iloc[-1]
        prev = df.iloc[-2]
        prev2 = df.iloc[-3]

        ema20_last = safe_float(last["EMA20"])
        ema50_last = safe_float(last["EMA50"])

        ema20_prev = safe_float(prev["EMA20"])
        ema50_prev = safe_float(prev["EMA50"])

        ema20_prev2 = safe_float(prev2["EMA20"])
        ema50_prev2 = safe_float(prev2["EMA50"])

        if None in [ema20_last, ema50_last, ema20_prev, ema50_prev, ema20_prev2, ema50_prev2]:
            return None

        # BUY
        if ema20_prev2 < ema50_prev2 and ema20_prev < ema50_prev and ema20_last > ema50_last:
            return "BUY"

        # SELL
        if ema20_prev2 > ema50_prev2 and ema20_prev > ema50_prev and ema20_last < ema50_last:
            return "SELL"

        return None

    except Exception as e:
        print("Signal error:", e)
        return None

# ========= CHECK RESULT =========
async def check_result(symbol, direction, entry):
    await asyncio.sleep(300)  # 5 minutes

    df = get_data(symbol)
    if df is None:
        return "UNKNOWN"

    close_price = safe_float(df["Close"].iloc[-1])
    if close_price is None:
        return "UNKNOWN"

    if direction == "BUY":
        return "WIN ✅" if close_price > entry else "LOSS ❌"
    if direction == "SELL":
        return "WIN ✅" if close_price < entry else "LOSS ❌"

# ========= WAIT FOR NEXT CANDLE =========
async def wait_for_next_candle():
    now = datetime.now()
    next_candle = (now + timedelta(minutes=1)).replace(second=0, microsecond=0)
    wait_seconds = (next_candle - now).total_seconds() - 5
    if wait_seconds > 0:
        await asyncio.sleep(wait_seconds)

# ========= MAIN BOT =========
async def run_bot():
    global signal_active

    print("🔥 TAPSCO BOT ACTIVE 🔥")
    await send_message("🔥 TAPSCO BOT IS ACTIVE 🔥")

    while True:
        if signal_active:
            await asyncio.sleep(5)
            continue

        await wait_for_next_candle()

        for symbol in SYMBOLS:
            try:
                print("Scanning", symbol)

                df = get_data(symbol)
                if df is None:
                    continue

                df = calculate_ema(df)
                signal = check_signal(df)

                if signal and not signal_active:
                    entry = safe_float(df["Close"].iloc[-1])
                    if entry is None:
                        continue

                    signal_active = True

                    message = f"""
🔥 TAPSCO BOT

PAIR: {symbol}
SIGNAL: {signal}
ENTRY: {entry}
TIME: {datetime.now().strftime("%H:%M")}
EXPIRY: 5 MIN
"""
                    await send_message(message)

                    result = await check_result(symbol, signal, entry)

                    result_msg = f"""
📊 RESULT

PAIR: {symbol}
SIGNAL: {signal}
ENTRY: {entry}
RESULT: {result}
"""
                    await send_message(result_msg)

                    signal_active = False
                    break

            except Exception as e:
                print("Error:", e)

        await asyncio.sleep(5)

# ========= START =========
asyncio.run(run_bot())
