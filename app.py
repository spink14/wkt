import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- 1. PAGE SETUP ---
st.set_page_config(page_title="Madcow Duo Pro", layout="wide", initial_sidebar_state="expanded")

# Replace this with your actual Google Sheet URL
SHEET_URL = "https://docs.google.com/spreadsheets/d/1-I9O0Gexxmvkb7zd-NzJqpm2MbYHIAVtAfeLkp-m0Vk/edit?gid=0#gid=0"

# --- 2. CONNECTION & DATA LOADING ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    # ttl=0 ensures we always pull the latest data from the cloud
    return conn.read(spreadsheet=SHEET_URL, ttl=0)

if 'df_all' not in st.session_state:
    st.session_state.df_all = load_data()

# --- 3. HELPER FUNCTIONS ---
def custom_round(x, base=5):
    """Rounds to the nearest plate increment."""
    return int(base * round(float(x)/base))

def get_madcow_ramps(top_weight, round_to=5):
    """Standard 12.5% intervals for the first 4 sets."""
    intervals = [0.50, 0.625, 0.75, 0.875]
    return [custom_round(top_weight * i, round_to) for i in intervals]

def get_plate_breakdown(target_weight, bar_weight):
    """Calculates plates needed per side."""
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
    return " + ".join(plates_needed) if plates_needed else "Bar Only"

# --- 4. SIDEBAR: USER SELECTION & SETTINGS ---
with st.sidebar:
    st.title("🏋️ Madcow Duo")
    current_user = st.radio("Lifter Selection:", ["Dylan", "Dane"], horizontal=True)
    
    st.divider()
    st.header("🧮 Plate Calculator")
    calc_target = st.number_input("Quick Check Weight", value=135, step=5)
    bar_wt = st.number_input("Barbell Weight", value=45, step=5)
    st.info(f"**Load per side:** {get_plate_breakdown(calc_target, bar_wt)}")
    
    st.divider()
    st.header("⚙️ Program Settings")
    week = st.number_input("Current Week", min_value=1, value=1)
    round_val = st.radio("Rounding", [5, 2.5, 1], index=0)
    
    st.divider()
    st.header(f"📈 {current_user}'s 5RMs")
    st.caption("Target reached on Week 4")
    
    # Filter rows for the current lifter for editing
    user_mask = st.session_state.df_all['User'] == current_user
    temp_df = st.session_state.df_all.copy()
    
    for index in st.session_state.df_all[user_mask].index:
        row = st.session_state.df_all.loc[index]
        with st.expander(f"Edit {row['Lift']}"):
            new_max = st.number_input(f"5RM", value=float(row['Max']), key=f"max_{index}")
            new_inc = st.number_input(f"Inc %", value=float(row['Increment']), key=f"inc_{index}")
            temp_df.at[index, 'Max'] = new_max
            temp_df.at[index, 'Increment'] = new_inc

    if st.button("💾 Save All Changes to Cloud"):
        try:
            conn.update(spreadsheet=SHEET_URL, data=temp_df)
            st.session_state.df_all = temp_df
            st.cache_data.clear()
            st.success("Successfully synced with Google!")
            st.balloons()
        except Exception as e:
            st.error(f"Sync failed! Have you shared the sheet with your Service Account email? Error: {e}")

# --- 5. DATA RETRIEVAL ---
def get_stats(lift_name):
    try:
        row = st.session_state.df_all[
            (st.session_state.df_all['User'] == current_user) & 
            (st.session_state.df_all['Lift'] == lift_name)
        ].iloc[0]
        # Week 4 Peak Logic: Weight * (1 + inc)^(week-4)
        current_max = row['Max'] * ((1 + (row['Increment'] / 100)) ** (week - 4))
        return current_max, row['Increment']
    except IndexError:
        st.error(f"Missing '{lift_name}' for {current_user} in Google Sheets!")
        return 0, 0

# --- 6. MAIN INTERFACE ---
st.title(f"Workout: {current_user} (Week {week})")

if week < 4:
    st.warning(f"Build-up phase: {4-week} week(s) until you hit your starting maxes.")

tab1, tab2, tab3 = st.tabs(["Monday (Heavy)", "Wednesday (Light)", "Friday (Intensity)"])

# --- MONDAY ---
with tab1:
    for lift in ["Squat", "Bench", "Row"]:
        mon_max, _ = get_stats(lift)
        mon_top = custom_round(mon_max, round_val)
        ramps = get_madcow_ramps(mon_top, round_val)
        with st.container(border=True):
            st.subheader(lift)
            st.write(f"Sets 1-4 (x5): {' → '.join(map(str, ramps))}")
            st.markdown(f"**TOP SET: :green[{mon_top} lbs] x 5**")
            st.caption(f"Plates: {get_plate_breakdown(mon_top, bar_wt)}")

# --- WEDNESDAY ---
with tab2:
    sq_max, _ = get_stats("Squat")
    sq_wed_top = custom_round(sq_max * 0.75, round_val)
    
    wed_lifts = [
        ("Squat (Light)", sq_wed_top),
        ("Overhead Press", get_stats("Overhead Press")[0]),
        ("Deadlift", get_stats("Deadlift")[0])
    ]
    
    for name, weight in wed_lifts:
        top_set = custom_round(weight, round_val)
        intervals = [0.5, 0.625, 0.75, 1.0]
        sets = [custom_round(top_set * i, round_val) for i in intervals]
        with st.container(border=True):
            st.subheader(name)
            st.write(f"Sets 1-3 (x5): {' → '.join(map(str, sets[:-1]))}")
            st.markdown(f"**TOP SET: :green[{sets[-1]} lbs] x 5**")
            st.caption(f"Plates: {get_plate_breakdown(sets[-1], bar_wt)}")

# --- FRIDAY ---
with tab3:
    for lift in ["Squat", "Bench", "Row"]:
        mon_max, inc = get_stats(lift)
        mon_top = custom_round(mon_max, round_val)
        
        # Friday triple is next week's Monday weight
        friday_triple = custom_round(mon_max * (1 + (inc / 100)), round_val)
        
        # Ramps match Monday's exactly
        base_ramps = get_madcow_ramps(mon_top, round_val)
        back_off = base_ramps[2] # Set 3 for 8 reps
        
        with st.container(border=True):
            st.subheader(lift)
            c1, c2, c3 = st.columns(3)
            with c1:
                st.write("**Ramps (x5)**")
                st.write(f"{' , '.join(map(str, base_ramps))}")
            with c2:
                st.write("**Triple (x3)**")
                st.markdown(f"### :orange[{friday_triple}]")
                st.caption(f"Plates: {get_plate_breakdown(friday_triple, bar_wt)}")
            with c3:
                st.write("**Back-off (x8)**")
                st.markdown(f"### {back_off}")
                st.caption(f"Plates: {get_plate_breakdown(back_off, bar_wt)}")