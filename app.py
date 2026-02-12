import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- 1. PAGE SETUP ---
st.set_page_config(page_title="Dylan & Dane Madcow Pro", layout="wide")

# Replace this with your actual Google Sheet ID
SHEET_URL = "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID_HERE/edit#gid=0"

# --- 2. CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    return conn.read(spreadsheet=SHEET_URL, ttl=0)

if 'df_all' not in st.session_state:
    st.session_state.df_all = load_data()

# --- 3. HELPER FUNCTIONS ---
def custom_round(x, base=5):
    return int(base * round(float(x)/base))

def get_madcow_ramps(top_weight, round_to=5):
    intervals = [0.50, 0.625, 0.75, 0.875]
    return [custom_round(top_weight * i, round_to) for i in intervals]

def get_plate_breakdown(target_weight, bar_weight):
    if target_weight <= bar_weight: return "Empty Bar"
    available_plates = [45, 35, 25, 10, 5, 2.5, 1, 0.5]
    weight_per_side = (target_weight - bar_weight) / 2
    plates_needed = []
    remaining = weight_per_side
    for plate in available_plates:
        count = int(remaining // plate)
        if count > 0:
            plates_needed.append(f"{count}x{plate}")
            remaining -= (count * plate)
    return " + ".join(plates_needed)

# --- 4. SIDEBAR ---
with st.sidebar:
    st.title("🏋️ Workout Settings")
    current_user = st.radio("Lifter Selection:", ["Dylan", "Dane"], horizontal=True)
    
    st.divider()
    week = st.number_input("Current Week", min_value=1, value=1, step=1)
    round_val = st.radio("Rounding", [5, 2.5, 1], index=0)
    bar_wt = st.number_input("Bar Weight", value=45, step=5)
    
    st.divider()
    st.header(f"📈 Edit {current_user}'s 5RMs")
    
    # We edit a copy so we can verify changes before syncing
    temp_df = st.session_state.df_all.copy()
    user_mask = temp_df['User'] == current_user
    
    for index in temp_df[user_mask].index:
        row = temp_df.loc[index]
        with st.expander(f"Edit {row['Lift']}"):
            # ADDED 'step' parameter here to fix the +/- button issue
            temp_df.at[index, 'Max'] = st.number_input(
                f"5RM", 
                value=float(row['Max']), 
                step=5.0,  # Increments by 5
                key=f"m_{index}"
            )
            temp_df.at[index, 'Increment'] = st.number_input(
                f"Inc %", 
                value=float(row['Increment']), 
                step=0.5,  # Increments by 0.5%
                key=f"i_{index}"
            )

    if st.button("💾 Save All Changes to Cloud"):
        try:
            conn.update(spreadsheet=SHEET_URL, data=temp_df)
            st.session_state.df_all = temp_df
            st.cache_data.clear()
            st.success("Successfully synced with Google Sheets!")
            st.balloons()
        except Exception as e:
            st.error(f"Sync failed! Error: {e}")

# --- 5. DATA RETRIEVAL ---
def get_stats(lift_name):
    try:
        row = st.session_state.df_all[
            (st.session_state.df_all['User'] == current_user) & 
            (st.session_state.df_all['Lift'] == lift_name)
        ].iloc[0]
        current_max = row['Max'] * ((1 + (row['Increment'] / 100)) ** (week - 4))
        return current_max, row['Increment']
    except:
        st.error(f"Missing '{lift_name}' for {current_user}!")
        return 0, 0

# --- 6. TABS ---
st.title(f"Workout: {current_user} (Week {week})")
tab1, tab2, tab3 = st.tabs(["Monday", "Wednesday", "Friday"])

with tab1: # Monday
    for lift in ["Squat", "Bench", "Row"]:
        m_max, _ = get_stats(lift)
        m_top = custom_round(m_max, round_val)
        ramps = get_madcow_ramps(m_top, round_val)
        with st.container(border=True):
            st.subheader(lift)
            st.write(f"Ramps: {' → '.join(map(str, ramps))} → **{m_top} x 5**")
            st.caption(f"Plates: {get_plate_breakdown(m_top, bar_wt)}")

with tab2: # Wednesday
    sq_max, _ = get_stats("Squat")
    sq_wed_top = custom_round(sq_max * 0.75, round_val)
    for name, weight in [("Squat (Light)", sq_wed_top), ("Overhead Press", get_stats("Overhead Press")[0]), ("Deadlift", get_stats("Deadlift")[0])]:
        top = custom_round(weight, round_val)
        sets = [custom_round(top * i, round_val) for i in [0.5, 0.625, 0.75, 1.0]]
        with st.container(border=True):
            st.subheader(name)
            st.write(f"Ramps: {' → '.join(map(str, sets[:-1]))} → **{sets[-1]} x 5**")

with tab3: # Friday
    for lift in ["Squat", "Bench", "Row"]:
        mon_max, inc = get_stats(lift)
        mon_top = custom_round(mon_max, round_val)
        friday_triple = custom_round(mon_max * (1 + (inc / 100)), round_val)
        base_ramps = get_madcow_ramps(mon_top, round_val)
        with st.container(border=True):
            st.subheader(lift)
            c1, c2, c3 = st.columns(3)
            with c1: st.write("**Ramp (x5)**"); st.write(f"{' , '.join(map(str, base_ramps))}")
            with c2: st.write("**Triple (x3)**"); st.markdown(f"### :orange[{friday_triple}]")
            with c3: st.write("**Back (x8)**"); st.markdown(f"### {base_ramps[2]}")