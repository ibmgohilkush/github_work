import streamlit as st
import pandas as pd
import altair as alt
import json
import os
from datetime import datetime

# Constants
K = 32
ELO_FILE = "elo_ratings.json"
MATCH_FILE = "match_history.json"

# Clear data function
def clear_all_data():
    st.session_state.ratings = {}
    st.session_state.matches = []
    st.session_state.initialized = False
    if os.path.exists(ELO_FILE):
        os.remove(ELO_FILE)
    if os.path.exists(MATCH_FILE):
        os.remove(MATCH_FILE)


# Functions for file I/O
def load_data():
    if os.path.exists(ELO_FILE):
        with open(ELO_FILE, "r") as f:
            st.session_state.ratings = json.load(f)
    else:
        st.session_state.ratings = {}

    if os.path.exists(MATCH_FILE):
        with open(MATCH_FILE, "r") as f:
            st.session_state.matches = json.load(f)
    else:
        st.session_state.matches = []

def save_data():
    with open(ELO_FILE, "w") as f:
        json.dump(st.session_state.ratings, f)
    with open(MATCH_FILE, "w") as f:
        json.dump(st.session_state.matches, f)

# Load data once
if "initialized" not in st.session_state:
    load_data()
    st.session_state.initialized = True

# ELO math
def expected_score(rating_a, rating_b):
    return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))

def update_elo(winner, loser):
    rating_winner = st.session_state.ratings.get(winner, 1500)
    rating_loser = st.session_state.ratings.get(loser, 1500)

    expected_win = expected_score(rating_winner, rating_loser)
    expected_lose = 1 - expected_win

    st.session_state.ratings[winner] = rating_winner + K * (1 - expected_win)
    st.session_state.ratings[loser] = rating_loser + K * (0 - expected_lose)

# UI - Title
st.title("🏓 Ping Pong ELO Ranking Dashboard")


# Match input form
with st.form("match_form"):
    st.subheader("Add a Match Result")
    col1, col2 = st.columns(2)
    with col1:
        player1 = st.text_input("Player 1 Name")
    with col2:
        player2 = st.text_input("Player 2 Name")

    if player1 and player2 and player1 != player2:
        winner = st.selectbox("Who won?", options=[player1, player2])
    else:
        winner = None

    match_date = st.date_input("Date", value=datetime.today())
    submitted = st.form_submit_button("Submit Match")

    if submitted and player1 and player2 and player1 != player2 and winner:
        match_record = {
            "date": str(pd.to_datetime(match_date).date()),
            "player1": player1,
            "player2": player2,
            "winner": winner
        }
        st.session_state.matches.append(match_record)
        loser = player2 if winner == player1 else player1
        update_elo(winner, loser)
        save_data()
        st.success(f"Recorded: {winner} defeated {loser}")

# Create DataFrames
match_df = pd.DataFrame(st.session_state.matches)
ratings_df = pd.DataFrame([
    {"Player": player, "ELO": round(rating, 1)}
    for player, rating in sorted(st.session_state.ratings.items(), key=lambda x: x[1], reverse=True)
])

# Show Ranking Table
st.subheader("🏆 Player Rankings")
st.dataframe(ratings_df.style.background_gradient(cmap='Blues'), use_container_width=True)

# ELO Over Time Visualization
if not match_df.empty:
    st.subheader("📈 ELO Over Time")

    elo_history = {}
    temp_ratings = {}

    history_records = []

    for _, row in match_df.sort_values("date").iterrows():
        p1, p2, winner = row["player1"], row["player2"], row["winner"]
        loser = p2 if winner == p1 else p1

        for player in [p1, p2]:
            temp_ratings.setdefault(player, 1500)

        expected_win = expected_score(temp_ratings[winner], temp_ratings[loser])
        expected_lose = 1 - expected_win

        temp_ratings[winner] += K * (1 - expected_win)
        temp_ratings[loser] += K * (0 - expected_lose)

        for player in [p1, p2]:
            history_records.append({
                "date": pd.to_datetime(row["date"]),
                "player": player,
                "elo": temp_ratings[player]
            })

    elo_df = pd.DataFrame(history_records)
    chart = alt.Chart(elo_df).mark_line().encode(
        x='date:T',
        y='elo:Q',
        color='player:N'
    ).properties(width=700, height=400)

    st.altair_chart(chart, use_container_width=True)

# Match History Table
if not match_df.empty:
    st.subheader("📜 Match History")
    st.dataframe(match_df.sort_values("date", ascending=False), use_container_width=True)

if st.button("Clear All", type="primary"):
    clear_all_data()
    st.success("All data cleared! Reloading...")
    st.rerun()