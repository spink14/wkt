import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- 1. PAGE SETUP ---
st.set_page_config(page_title="Dylan & Dane Madcow Pro", layout="wide")

# Replace this with your actual Google Sheet ID
SHEET_URL = "https://docs.google.com/spreadsheets/d/1-I9O0Gexxmvkb7zd-NzJqpm2MbYHIAVtAfeLkp-m0Vk/edit?gid=0#gid=0"

# --- 2. CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    df = conn.read(spreadsheet=SHEET_URL, ttl=0)
    # SANITIZATION: Force values to clean floats rounded to 1 decimal
    df['Max'] = pd.to_numeric(df['Max'], errors='coerce').fillna(0).apply(lambda x: round(float(x), 1))
    df['Increment'] = pd.to_numeric(df['Increment'], errors='coerce').fillna(0).apply(lambda x: round(float(x), 1))
    return df

if 'df_all' not in st.session_state:
    st.session_state.df_all = load_data()

# --- 3. HELPER FUNCTIONS ---
def custom_round(x, base=5):
    """Rounds weights to the nearest plate increment (e.g., 5 or 2.5)."""
    return (base * round(float(x)/base))

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
    # Explicitly setting step=1 for the week
    week = st.number_input("Current Week", min_value=1, max_value=52, value=1, step=1)
    round_val = st.radio("Rounding (Plate Increments)", [5, 2.5, 1], index=0)
    bar_wt = st.number_input("Bar Weight", value=45, step=5)
    
    st.divider()
    st.header(f"📈 Edit {current_user}'s 5RMs at RPE 9")
    
    user_mask = st.session_state.df_all['User'] == current_user
    
    # We use a button-triggered update to avoid multiple cloud writes
    for index in st.session_state.df_all[user_mask].index:
        row = st.session_state.df_all.loc[index]
        with st.expander(f"Edit {row['Lift']}"):
            
            # FORCED FLOATS AND FORMATTING
            # If the buttons still do not work, we use the value directly from the state
            new_max = st.number_input(
                "Starting 5RM @ RPE 9",
                value=float(row['Max']),
                step=5.0,
                min_value=0.0,
                format="%.1f",
                key=f"max_in_{index}_{current_user}"
            )
            
            new_inc = st.number_input(
                "Weekly Increment %",
                value=float(row['Increment']),
                step=0.5,
                min_value=0.0,
                format="%.1f",
                key=f"inc_in_{index}_{current_user}"
            )
            
            # Instantly update the local state dataframe
            st.session_state.df_all.at[index, 'Max'] = new_max
            st.session_state.df_all.at[index, 'Increment'] = new_inc

    if st.button("💾 Sync to Google Sheets"):
        try:
            conn.update(spreadsheet=SHEET_URL, data=st.session_state.df_all)
            st.cache_data.clear()
            st.success("Cloud Sync Successful!")
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
        # Weight = Max * (1 + inc)^(week-4)
        current_max = row['Max'] * ((1 + (row['Increment'] / 100)) ** (week - 4))
        return current_max, row['Increment']
    except Exception:
        st.error(f"Missing '{lift_name}' data!")
        return 0, 0

# --- 6. MAIN WORKOUT UI ---
st.title(f"Workout: {current_user} (Week {week})")
tab1, tab2, tab3 = st.tabs(["Monday", "Wednesday", "Friday"])

with tab1: # Monday (Volume)
    for lift in ["Squat", "Bench", "Row"]:
        m_max, _ = get_stats(lift)
        m_top = custom_round(m_max, round_val)
        ramps = get_madcow_ramps(m_top, round_val)
        with st.container(border=True):
            st.subheader(lift)
            st.write(f"Ramps (x5): {' → '.join(map(str, ramps))}")
            st.markdown(f"**TOP SET: :green[{m_top} lbs] x 5**")
            st.caption(f"Plates per side: {get_plate_breakdown(m_top, bar_wt)}")

with tab2: # Wednesday (Recovery)
    sq_max, _ = get_stats("Squat")
    sq_wed_top = custom_round(sq_max * 0.75, round_val)
    
    wed_lifts = [
        ("Squat (Light)", sq_wed_top),
        ("Overhead Press", get_stats("Overhead Press")[0]),
        ("Deadlift", get_stats("Deadlift")[0])
    ]
    for name, weight in wed_lifts:
        top = custom_round(weight, round_val)
        sets = [custom_round(top * i, round_val) for i in [0.5, 0.625, 0.75, 1.0]]
        with st.container(border=True):
            st.subheader(name)
            st.write(f"Ramps: {' → '.join(map(str, sets[:-1]))} → **{sets[-1]} x 5**")
            st.caption(f"Plates: {get_plate_breakdown(sets[-1], bar_wt)}")

with tab3: # Friday (Intensity)
    for lift in ["Squat", "Bench", "Row"]:
        mon_max, inc = get_stats(lift)
        mon_top = custom_round(mon_max, round_val)
        friday_triple = custom_round(mon_max * (1 + (inc / 100)), round_val)
        base_ramps = get_madcow_ramps(mon_top, round_val)
        with st.container(border=True):
            st.subheader(lift)
            c1, c2, c3 = st.columns(3)
            with c1: 
                st.write("**Ramp (x5)**")
                st.write(f"{' , '.join(map(str, base_ramps))}")
            with c2: 
                st.write("**Triple (x3)**")
                st.markdown(f"### :orange[{friday_triple}]")
            with c3: 
                st.write("**Back (x8)**")
                st.markdown(f"### {base_ramps[2]}")