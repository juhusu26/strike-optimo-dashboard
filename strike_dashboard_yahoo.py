#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import yfinance as yf
import pandas as pd
from flask import Flask, request, render_template_string

app = Flask(__name__)

HTML = """
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Strike Óptimo Yahoo</title>
<style>
body {
    background:#0b0f14;
    color:#e6edf3;
    font-family:Arial;
    padding:30px;
}
.container {max-width:1200px;margin:auto;}
.card {
    background:#121821;
    border:1px solid #243041;
    border-radius:14px;
    padding:20px;
    margin-bottom:20px;
}
input,button {
    padding:10px;
    border-radius:8px;
    border:none;
    margin-right:10px;
}
button {
    background:#00d084;
    font-weight:bold;
    cursor:pointer;
}
table {
    width:100%;
    border-collapse:collapse;
}
th,td {
    border-bottom:1px solid #263446;
    padding:10px;
    text-align:left;
}
.good {color:#00d084;font-weight:bold;}
.warn {color:#ffb020;font-weight:bold;}
.bad {color:#ff5f5f;font-weight:bold;}
</style>
</head>
<body>
<div class="container">

<div class="card">
<h1>Strike Óptimo Dashboard (Yahoo Finance)</h1>

<form method="POST">
<input name="symbol" value="{{symbol}}" placeholder="SPY">
<input name="expiration" value="{{expiration}}" placeholder="2026-05-29">
<button type="submit">CALCULAR</button>
</form>

<p>Ranking automático usando spread + volumen + open interest + cercanía ATM.</p>
</div>

{% if calls %}
<div class="card">
<h2>Top CALLS</h2>
<table>
<tr>
<th>Strike</th>
<th>Bid</th>
<th>Ask</th>
<th>Spread%</th>
<th>Vol</th>
<th>OI</th>
<th>Score</th>
</tr>

{% for r in calls %}
<tr>
<td>{{r['strike']}}</td>
<td>{{r['bid']}}</td>
<td>{{r['ask']}}</td>
<td>{{r['spread_pct']}}%</td>
<td>{{r['volume']}}</td>
<td>{{r['oi']}}</td>
<td class="{{r['class']}}">{{r['score']}}</td>
</tr>
{% endfor %}
</table>
</div>
{% endif %}

{% if puts %}
<div class="card">
<h2>Top PUTS</h2>
<table>
<tr>
<th>Strike</th>
<th>Bid</th>
<th>Ask</th>
<th>Spread%</th>
<th>Vol</th>
<th>OI</th>
<th>Score</th>
</tr>

{% for r in puts %}
<tr>
<td>{{r['strike']}}</td>
<td>{{r['bid']}}</td>
<td>{{r['ask']}}</td>
<td>{{r['spread_pct']}}%</td>
<td>{{r['volume']}}</td>
<td>{{r['oi']}}</td>
<td class="{{r['class']}}">{{r['score']}}</td>
</tr>
{% endfor %}
</table>
</div>
{% endif %}

</div>
</body>
</html>
"""

def calc_score(row, current_price):
    strike = float(row["strike"])
    bid = float(row["bid"] or 0)
    ask = float(row["ask"] or 0)
    volume = 0 if pd.isna(row["volume"]) else int(row["volume"])
    oi = int(row["openInterest"] or 0)

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

    if spread_pct <= 5:
        score += 25
    elif spread_pct <= 10:
        score += 15
    elif spread_pct <= 15:
        score += 8

    if volume >= 1000:
        score += 20
    elif volume >= 300:
        score += 12
    elif volume >= 100:
        score += 6

    if oi >= 1000:
        score += 20
    elif oi >= 300:
        score += 12
    elif oi >= 100:
        score += 6

    score = min(100, max(0, round(score)))

    if score >= 75:
        cls = "good"
    elif score >= 50:
        cls = "warn"
    else:
        cls = "bad"

    return {
        "strike": strike,
        "bid": round(bid,2),
        "ask": round(ask,2),
        "spread_pct": round(spread_pct,1),
        "volume": volume,
        "oi": oi,
        "score": score,
        "class": cls
    }

@app.route("/", methods=["GET", "POST"])
def home():
    calls = []
    puts = []
    symbol = "SPY"
    expiration = ""

    if request.method == "POST":
        symbol = request.form["symbol"].upper()
        expiration = request.form["expiration"]

        ticker = yf.Ticker(symbol)

        if not expiration:
            expiration = ticker.options[0]

        chain = ticker.option_chain(expiration)

        current_price = ticker.history(period="1d")["Close"].iloc[-1]

        for _, row in chain.calls.iterrows():
            calls.append(calc_score(row, current_price))

        for _, row in chain.puts.iterrows():
            puts.append(calc_score(row, current_price))

        calls = sorted(calls, key=lambda x: x["score"], reverse=True)[:5]
        puts = sorted(puts, key=lambda x: x["score"], reverse=True)[:5]

    return render_template_string(
        HTML,
        calls=calls,
        puts=puts,
        symbol=symbol,
        expiration=expiration
    )

if __name__ == "__main__":
    print("Dashboard corriendo en http://localhost:8787")
    app.run(host="0.0.0.0", port=8787)
