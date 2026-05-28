import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Strike Óptimo", layout="wide")

st.title("📈 Strike Óptimo Dashboard")

ticker = st.text_input("Ticker", "SPY")
exp = st.text_input("Expiration Date", "2026-05-29")

def calc_score(row, current_price):
    strike = float(row["strike"])
    bid = float(row["bid"] or 0)
    ask = float(row["ask"] or 0)

    volume = 0 if pd.isna(row["volume"]) else int(row["volume"])
    oi = 0 if pd.isna(row["openInterest"]) else int(row["openInterest"])

    mid = (bid + ask) / 2 if ask else 0
    spread = ask - bid if ask else 999
    spread_pct = (spread / mid * 100) if mid else 999

    distance = abs(strike - current_price)

    score = 0

    if distance <= 2:
        score += 35
    elif distance <= 5:
        score += 25
    elif distance <= 10:
        score += 15

    if spread_pct <= 2:
        score += 35
    elif spread_pct <= 5:
        score += 20

    if volume >= 10000:
        score += 15
    elif volume >= 1000:
        score += 10

    if oi >= 10000:
        score += 15
    elif oi >= 1000:
        score += 10

    return {
        "Strike": strike,
        "Bid": bid,
        "Ask": ask,
        "Spread%": round(spread_pct, 2),
        "Vol": volume,
        "OI": oi,
        "Score": score
    }

if st.button("CALCULAR"):

    tk = yf.Ticker(ticker)
    current_price = tk.history(period="1d")["Close"].iloc[-1]

    chain = tk.option_chain(exp)

    calls = []
    puts = []

    for _, row in chain.calls.iterrows():
        calls.append(calc_score(row, current_price))

    for _, row in chain.puts.iterrows():
        puts.append(calc_score(row, current_price))

    calls_df = pd.DataFrame(calls).sort_values("Score", ascending=False).head(10)
    puts_df = pd.DataFrame(puts).sort_values("Score", ascending=False).head(10)

    st.subheader("Top CALLS")
    st.dataframe(calls_df, use_container_width=True)

    st.subheader("Top PUTS")
    st.dataframe(puts_df, use_container_width=True)