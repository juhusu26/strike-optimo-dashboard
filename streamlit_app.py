import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import date

st.set_page_config(
    page_title="Strike Óptimo Dashboard",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Strike Óptimo Dashboard")
st.caption("Ranking de contratos usando spread + volumen + open interest + cercanía ATM.")

# ----------------------------
# Helpers
# ----------------------------
def safe_int(value):
    if pd.isna(value):
        return 0
    try:
        return int(value)
    except Exception:
        return 0

def safe_float(value):
    if pd.isna(value):
        return 0.0
    try:
        return float(value)
    except Exception:
        return 0.0

def get_current_price(tk):
    try:
        price = tk.fast_info.get("last_price")
        if price:
            return float(price)
    except Exception:
        pass

    hist = tk.history(period="5d")
    if hist.empty or "Close" not in hist:
        raise RuntimeError("No se pudo obtener el precio actual desde Yahoo Finance.")
    return float(hist["Close"].dropna().iloc[-1])

def calc_score(row, current_price):
    strike = safe_float(row.get("strike"))
    bid = safe_float(row.get("bid"))
    ask = safe_float(row.get("ask"))
    volume = safe_int(row.get("volume"))
    oi = safe_int(row.get("openInterest"))

    mid = (bid + ask) / 2 if ask > 0 else 0
    spread = ask - bid if ask > 0 else 999
    spread_pct = (spread / mid * 100) if mid > 0 else 999
    distance = abs(strike - current_price)

    score = 0

    # Cercanía ATM
    if distance <= 2:
        score += 35
    elif distance <= 5:
        score += 25
    elif distance <= 10:
        score += 15

    # Spread
    if spread_pct <= 2:
        score += 35
    elif spread_pct <= 5:
        score += 20
    elif spread_pct <= 10:
        score += 10

    # Volumen
    if volume >= 10000:
        score += 15
    elif volume >= 1000:
        score += 10
    elif volume >= 100:
        score += 5

    # Open Interest
    if oi >= 10000:
        score += 15
    elif oi >= 1000:
        score += 10
    elif oi >= 100:
        score += 5

    return {
        "Strike": strike,
        "Bid": bid,
        "Ask": ask,
        "Mid": round(mid, 2),
        "Spread%": round(spread_pct, 2),
        "Vol": volume,
        "OI": oi,
        "Dist ATM": round(distance, 2),
        "Score": min(score, 100)
    }

def score_style(val):
    if val >= 90:
        return "background-color: #064e3b; color: #34d399; font-weight: bold"
    if val >= 75:
        return "background-color: #713f12; color: #facc15; font-weight: bold"
    return "background-color: #7f1d1d; color: #fca5a5; font-weight: bold"

# ----------------------------
# UI
# ----------------------------
col1, col2, col3 = st.columns([1, 1, 1])

with col1:
    ticker_symbol = st.text_input("Ticker", "SPY").upper().strip()

with col2:
    expiration_input = st.text_input("Expiration Date", "2026-05-29").strip()

with col3:
    top_n = st.number_input("Cantidad de contratos", min_value=5, max_value=25, value=10, step=5)

st.info("El score mide calidad del contrato: liquidez, spread, OI y cercanía ATM. No predice dirección.")

if st.button("CALCULAR", type="primary"):
    if not ticker_symbol:
        st.error("Escribe un ticker válido, miarma.")
        st.stop()

    try:
        tk = yf.Ticker(ticker_symbol)

        expirations = list(tk.options)
        if not expirations:
            st.error("Yahoo no devolvió expiraciones para ese ticker.")
            st.stop()

        if not expiration_input:
            expiration_input = expirations[0]

        if expiration_input not in expirations:
            st.warning("Esa expiración no aparece en Yahoo. Usando la primera disponible.")
            expiration_input = expirations[0]

        current_price = get_current_price(tk)
        chain = tk.option_chain(expiration_input)

        calls = [calc_score(row, current_price) for _, row in chain.calls.iterrows()]
        puts = [calc_score(row, current_price) for _, row in chain.puts.iterrows()]

        calls_df = pd.DataFrame(calls).sort_values(
            by=["Score", "Vol", "OI"], ascending=[False, False, False]
        ).head(top_n)

        puts_df = pd.DataFrame(puts).sort_values(
            by=["Score", "Vol", "OI"], ascending=[False, False, False]
        ).head(top_n)

        m1, m2, m3 = st.columns(3)
        m1.metric("Ticker", ticker_symbol)
        m2.metric("Precio actual aprox.", f"{current_price:.2f}")
        m3.metric("Expiración", expiration_input)

        st.subheader("Top CALLS")
        st.dataframe(
            calls_df,
            use_container_width=True,
            hide_index=True
        )

        st.subheader("Top PUTS")
        st.dataframe(
            puts_df,
            use_container_width=True,
            hide_index=True
        )

        total_call_vol = int(calls_df["Vol"].sum()) if not calls_df.empty else 0
        total_put_vol = int(puts_df["Vol"].sum()) if not puts_df.empty else 0

        if total_call_vol or total_put_vol:
            pcr = total_put_vol / total_call_vol if total_call_vol else None
            st.subheader("Lectura rápida")
            if pcr is not None:
                st.write(f"Put/Call Ratio aproximado de los Top {top_n}: **{pcr:.2f}**")
                if pcr < 0.7:
                    st.success("Más volumen relativo en CALLS: lectura rápida más alcista.")
                elif pcr > 1.3:
                    st.warning("Más volumen relativo en PUTS: lectura rápida más defensiva/bajista.")
                else:
                    st.info("Flujo bastante balanceado entre calls y puts.")

    except Exception as e:
        st.error("Yahoo Finance bloqueó o falló la consulta. Prueba de nuevo en unos minutos o usa otro ticker/fecha.")
        st.exception(e)
