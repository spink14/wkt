import streamlit as st
import pandas as pd
import os

# --- FILE SETTINGS ---
DB_FILE = "madcow_settings.csv"

# --- 1. DATA PERSISTENCE LOGIC ---
def load_data():
    """Loads settings from CSV or returns defaults if file doesn't exist."""
    defaults = {
        "Lift": ["Squat", "Bench", "Row", "Deadlift", "Overhead Press"],
        "Max": [200.0, 150.0, 100.0, 250.0, 90.0],
        "Increment": [2.5, 2.5, 2.5, 5.0, 2.0]
    }
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE)
    return pd.DataFrame(defaults)

def save_data(df):
    """Saves the current dataframe to CSV."""
    df.to_csv(DB_FILE, index=False)

# --- 2. INITIALIZATION ---
st.set_page_config(page_title="Madcow 5x5 Pro Tracker", layout="wide")

if 'df_settings' not in st.session_state:
    st.session_state.df_settings = load_data()

# --- 3. HELPER FUNCTIONS ---
def custom_round(x, base=5):
    return int(base * round(float(x)/base))

def get_madcow_ramps(top_weight, round_to=5):
    """Standard 12.5% intervals for sets 1-4."""
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
    return " + ".join(plates_needed) if plates_needed else "Bar Only"

# --- 4. SIDEBAR: PERSISTENT SETTINGS & TOOLS ---
with st.sidebar:
    st.header("🧮 Plate Calculator")
    calc_target = st.number_input("Quick Weight Check", value=135, step=5)
    bar_wt = st.number_input("Barbell Weight", value=45, step=5)
    st.info(f"**Load per side:** {get_plate_breakdown(calc_target, bar_wt)}")
    
    st.divider()
    st.header("⚙️ Program Settings")
    week = st.number_input("Current Week", min_value=1, value=1)
    round_val = st.radio("Rounding", [5, 2.5, 1], index=0)
    
    st.divider()
    st.header("📈 Edit Starting 5RMs")
    st.caption("Target reached on Week 4")
    
    changes_made = False
    for index, row in st.session_state.df_settings.iterrows():
        with st.expander(f"Edit {row['Lift']}"):
            new_max = st.number_input(f"{row['Lift']} 5RM", value=float(row['Max']), step=5.0, key=f"max_{index}")
            new_inc = st.number_input(f"{row['Lift']} %", value=float(row['Increment']), step=0.1, key=f"inc_{index}")
            
            if new_max != row['Max'] or new_inc != row['Increment']:
                st.session_state.df_settings.at[index, 'Max'] = new_max
                st.session_state.df_settings.at[index, 'Increment'] = new_inc
                changes_made = True

    if changes_made:
        save_data(st.session_state.df_settings)
        st.toast("Settings Saved to CSV!")

# --- 5. DATA RETRIEVAL ---
def get_stats(lift_name):
    row = st.session_state.df_settings[st.session_state.df_settings['Lift'] == lift_name].iloc[0]
    # Week 4 Peak Logic
    current_max = row['Max'] * ((1 + (row['Increment'] / 100)) ** (week - 4))
    return current_max, row['Increment']

# --- 6. MAIN UI ---
st.title(f"🏋️ Madcow 5x5: Week {week}")

if week < 4:
    st.info(f"Build-up Phase: {4-week} weeks until you hit your starting maxes.")

tab1, tab2, tab3 = st.tabs(["Monday (Heavy)", "Wednesday (Light)", "Friday (Intensity)"])

# --- MONDAY ---
with tab1:
    for lift in ["Squat", "Bench", "Row"]:
        monday_max, _ = get_stats(lift)
        monday_top = custom_round(monday_max, round_val)
        ramps = get_madcow_ramps(monday_top, round_val)
        with st.container(border=True):
            st.subheader(lift)
            st.write(f"Sets 1-4 (x5): {' → '.join(map(str, ramps))}")
            st.markdown(f"**TOP SET: :green[{monday_top} lbs] x 5**")

# --- WEDNESDAY ---
with tab2:
    # Squat is 25% lighter than Monday
    sq_max, _ = get_stats("Squat")
    sq_wed_top = custom_round(sq_max * 0.75, round_val)
    
    # Wednesday lifts (Squat, OHP, Deadlift)
    for lift_name, weight in [("Squat (Light)", sq_wed_top), ("Overhead Press", get_stats("Overhead Press")[0]), ("Deadlift", get_stats("Deadlift")[0])]:
        top_set = custom_round(weight, round_val)
        # 4-set ramp to top
        intervals = [0.5, 0.625, 0.75, 1.0]
        sets = [custom_round(top_set * i, round_val) for i in intervals]
        with st.container(border=True):
            st.subheader(lift_name)
            st.write(f"Sets 1-3 (x5): {' → '.join(map(str, sets[:-1]))}")
            st.markdown(f"**TOP SET: :green[{sets[-1]} lbs] x 5**")

# --- FRIDAY ---
with tab3:
    for lift in ["Squat", "Bench", "Row"]:
        monday_max, inc = get_stats(lift)
        monday_top = custom_round(monday_max, round_val)
        
        # Friday triple is Monday's weight + 1 increment
        friday_triple = custom_round(monday_max * (1 + (inc / 100)), round_val)
        
        # Friday ramps match Monday's first 4 sets
        base_ramps = get_madcow_ramps(monday_top, round_val)
        back_off = base_ramps[2] # Set 3
        
        with st.container(border=True):
            st.subheader(lift)
            c1, c2, c3 = st.columns(3)
            with c1:
                st.write("**Match Mon (x5)**")
                st.write(f"{' , '.join(map(str, base_ramps))}")
            with c2:
                st.write("**The Triple (x3)**")
                st.markdown(f"### :orange[{friday_triple}]")
                st.caption("New PR attempt")
            with c3:
                st.write("**Back-off (x8)**")
                st.markdown(f"### {back_off}")
                st.caption("Volume Flush")