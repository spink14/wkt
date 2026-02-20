import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, date

# --- 1. PAGE SETUP ---
st.set_page_config(page_title="Dylan & Dane Madcow Pro", layout="wide")

SHEET_URL = "https://docs.google.com/spreadsheets/d/1-I9O0Gexxmvkb7zd-NzJqpm2MbYHIAVtAfeLkp-m0Vk/edit?gid=0#gid=0"

# --- 2. CONNECTION & DATA LOADING ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    # Load Workout Data (Main Sheet)
    df = conn.read(spreadsheet=SHEET_URL, ttl=0)
    df['Max'] = pd.to_numeric(df['Max'], errors='coerce').fillna(0).round(0).astype(float)
    df['Increment'] = pd.to_numeric(df['Increment'], errors='coerce').fillna(2.5).round(1).astype(float)
    
    # Load Settings Data (Settings tab)
    try:
        settings_df = conn.read(spreadsheet=SHEET_URL, worksheet="Settings", ttl=0)
        date_row = settings_df[settings_df['Attribute'] == 'start_date']
        
        if not date_row.empty:
            raw_val = date_row['Value'].values[0]
            stored_date = pd.to_datetime(raw_val).date()
        else:
            stored_date = date.today()
    except Exception:
        stored_date = date.today()
        
    return df, stored_date

if 'df_all' not in st.session_state:
    st.session_state.df_all, st.session_state.start_date = load_data()

# --- 3. HELPER FUNCTIONS ---
def custom_round(x, base=5):
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
            remaining = round(remaining, 2) 
    return " + ".join(plates_needed) if plates_needed else "Bar Only"

# --- 4. SIDEBAR ---
with st.sidebar:
    st.title("🐱Danylan Workout🐱")
    current_user = st.radio("Lifter Selection:", ["Dylan", "Dane"], horizontal=True)
    
    st.divider()
    # RESTORED PLATE CALCULATOR
    st.header("💅Plate Calculator")
    calc_target = st.number_input("Weight to Check", value=135, step=5)
    bar_wt = st.number_input("Barbell Weight", value=45, step=5)
    st.info(f"**Load per side:** {get_plate_breakdown(calc_target, bar_wt)}")
    
    st.divider()
    st.header("⚙️ Program Settings")
    
    picked_date = st.date_input(
        "Program Start Date", 
        value=st.session_state.start_date,
        key="date_picker"
    )
    
    st.session_state.start_date = picked_date
    
    days_elapsed = (date.today() - picked_date).days
    auto_week = max(1, (days_elapsed // 7) + 1)
    
    manual_week = st.checkbox("Manual Week Override", value=False)
    if manual_week:
        week = st.number_input("Select Week", min_value=1, max_value=52, value=auto_week, step=1)
    else:
        week = auto_week
        st.info(f"Currently in **Week {week}**")

    round_val = st.radio("Rounding", [5, 2.5, 1], index=0)
    
    st.divider()
    st.header(f"Edit {current_user}'s 5RMs")
    
    user_mask = st.session_state.df_all['User'] == current_user
    for index in st.session_state.df_all[user_mask].index:
        row = st.session_state.df_all.loc[index]
        with st.expander(f"Edit {row['Lift']}"):
            new_max = st.number_input("5RM", value=int(row['Max']), step=5, key=f"m_{index}_{current_user}")
            new_inc = st.number_input("Inc %", value=float(row['Increment']), step=0.5, format="%.1f", key=f"i_{index}_{current_user}")
            st.session_state.df_all.at[index, 'Max'] = float(new_max)
            st.session_state.df_all.at[index, 'Increment'] = float(new_inc)

    if st.button("💾 Sync to Cloud"):
        with st.status("Pushing data to Google Sheets...", expanded=False) as status:
            try:
                conn.update(spreadsheet=SHEET_URL, data=st.session_state.df_all)
                settings_to_save = pd.DataFrame([
                    {"Attribute": "start_date", "Value": str(st.session_state.start_date)}
                ])
                conn.update(spreadsheet=SHEET_URL, worksheet="Settings", data=settings_to_save)
                st.cache_data.clear()
                st.toast("Sync Successful!", icon='✅')
                status.update(label="Cloud Sync Complete!", state="complete", expanded=False)
                st.session_state.sync_success = True
            except Exception as e:
                st.error(f"Sync failed: {e}")

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
        return 0, 0

# --- 6. MAIN WORKOUT UI ---
st.title(f"Workout: {current_user} (Week {week})")
tab1, tab2, tab3 = st.tabs(["Monday", "Wednesday", "Friday"])

with tab1: # Monday
    for lift in ["Squat", "Bench", "Row"]:
        m_max, _ = get_stats(lift)
        m_top = custom_round(m_max, round_val)
        ramps = get_madcow_ramps(m_top, round_val)
        with st.container(border=True):
            st.subheader(lift)
            st.write(f"Ramps (x5): {' → '.join(map(str, ramps))}")
            st.markdown(f"**TOP SET: :green[{m_top} lbs] x 5**")

with tab2: # Wednesday
    sq_max, _ = get_stats("Squat")
    wed_lifts = [("Squat (Light)", sq_max), ("Overhead Press", get_stats("Overhead Press")[0]), ("Deadlift", get_stats("Deadlift")[0])]
    for name, weight in wed_lifts:
        top = custom_round(weight, round_val)
        if name == "Squat (Light)":
            sets = [custom_round(top * i, round_val) for i in [0.5, 0.625, 0.75, .75]]
        else:
            sets = [custom_round(top * i, round_val) for i in [0.5, 0.625, 0.75, 1.0]]
        with st.container(border=True):
            st.subheader(name)
            st.write(f"Ramps (x5): {' → '.join(map(str, sets[:-1]))} → **{sets[-1]}**")

with tab3: # Friday
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
                st.write("**The Triple (x3)**")
                st.markdown(f"### :orange[{friday_triple}]")
            with c3:
                st.write("**Back-off (x8)**")
                st.markdown(f"### {base_ramps[2]}")