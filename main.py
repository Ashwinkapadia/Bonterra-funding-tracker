import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import datetime

# --- 1. BRANDING & CONFIGURATION ---
st.set_page_config(page_title="Bonterra Intelligence", page_icon="🏛️", layout="wide")

# Bonterra Brand Colors
COLOR_PRIMARY = "#381360"   # Scarlet Gum
COLOR_SECONDARY = "#84EA9F" # Pastel Green
COLOR_ACCENT = "#5D2E86"    # Deep Purple
COLOR_BG = "#F4F6F8"        # Enterprise Gray

# Custom CSS for SaaS-like Polish
st.markdown(f"""
    <style>
    .stApp {{ background-color: {COLOR_BG}; }}
    h1, h2, h3 {{ color: {COLOR_PRIMARY} !important; font-family: 'Segoe UI', sans-serif; font-weight: 600; }}
    div[data-testid="stMetric"] {{
        background-color: white; border: 1px solid #e0e0e0; padding: 15px;
        border-left: 5px solid {COLOR_SECONDARY}; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }}
    div.stButton > button {{
        background-color: {COLOR_PRIMARY}; color: white; border-radius: 6px; border: none; padding: 10px 20px; width: 100%;
    }}
    div.stButton > button:hover {{ background-color: {COLOR_ACCENT}; color: white; }}
    .stDataFrame {{ background-color: white; border-radius: 10px; padding: 10px; }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. INTELLIGENCE MAP ---
US_STATES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California",
    "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "FL": "Florida", "GA": "Georgia",
    "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa",
    "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi", "MO": "Missouri",
    "MT": "Montana", "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey",
    "NM": "New Mexico", "NY": "New York", "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio",
    "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont",
    "VA": "Virginia", "WA": "Washington", "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming"
}

# KEYWORDS FOR LOCAL FILTERING (Bypassing API strictness)
VERTICAL_KEYWORDS = {
    "School Districts (K-12)": ["school", "education", "elementary", "isd", "title i", "esser", "idea", "instruction"],
    "Workforce Development": ["workforce", "wioa", "labor", "employment", "job training", "apprentice", "dislocated"],
    "Violence Prevention": ["violence", "victim", "voca", "abuse", "safety", "justice", "crime", "prevention"],
    "Aging Services": ["aging", "elder", "senior", "nutrition", "adult protective", "home delivered"],
    "Veterans": ["veteran", "homeless vet", "hv rp", "ssvf"],
    "Housing & Homelessness": ["housing", "homeless", "tenant", "rent", "cdbg", "shelter"]
}

# --- 3. ROBUST API ENGINE ---
@st.cache_data
def fetch_state_data(state_code, days_back, mode):
    url = "https://api.usaspending.gov/api/v2/search/spending_by_award/"
    
    # Calculate Dates
    end_date = datetime.date.today().strftime("%Y-%m-%d")
    start_date = (datetime.date.today() - datetime.timedelta(days=days_back)).strftime("%Y-%m-%d")
    
    # DYNAMIC PAYLOAD BUILDER
    if mode == "Prime Awards (Direct Federal -> State)":
        # PRIME Config
        sort_key = "Action Date"  # Prime awards use 'Action Date'
        date_col = "Action Date"
        is_sub = False
        # We use 'Place of Performance' to catch money SPENT in AR even if Recipient is in DC
        location_filter = {"place_of_performance_locations": [{"country": "USA", "state": state_code}]}
    else:
        # SUB-AWARD Config
        sort_key = "Start Date"   # Sub-awards use 'Start Date' (Fixes Status 400)
        date_col = "Start Date"
        is_sub = True
        # Sub-awards usually require 'recipient_locations'
        location_filter = {"recipient_locations": [{"country": "USA", "state": state_code}]}

    payload = {
        "filters": {
            "time_period": [{"start_date": start_date, "end_date": end_date}],
            "award_type_codes": ["A", "B", "C", "D"]
        },
        "fields": [
            "Generated Unique Award ID", 
            "Recipient Name", 
            "Award Amount", 
            "Description", 
            "Awarding Agency",
            date_col # Requesting the correct date field
        ],
        "limit": 100,
        "sort": sort_key, # Using the correct sort key
        "order": "desc",
        "subawards": is_sub
    }
    
    # Merge location filter
    payload["filters"].update(location_filter)

    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            data = response.json()
            df = pd.DataFrame(data.get('results', []))
            
            # Normalize Date Column Name for consistency
            if not df.empty:
                df.rename(columns={date_col: "Date"}, inplace=True)
            return df
        else:
            st.error(f"API Error {response.status_code}: {response.text}")
            return pd.DataFrame()
            
    except Exception as e:
        st.error(f"Connection Error: {e}")
        return pd.DataFrame()

# --- 4. DASHBOARD UI ---
with st.sidebar:
    # Branding
    try:
        st.image("https://logo.clearbit.com/bonterratech.com", width=60)
    except:
        st.markdown(f"## Bonterra")
    
    st.markdown("### 🔎 Search Parameters")
    
    # State Selector
    selected_state_name = st.selectbox("Target State", list(US_STATES.values()), index=3) # Default AR
    selected_state_code = [k for k, v in US_STATES.items() if v == selected_state_name][0]
    
    # Mode Selector
    mode = st.radio("Funding Layer", ["Prime Awards (Direct Federal -> State)", "Sub-Awards (State -> Local)"])
    
    # Vertical Filter (Local)
    selected_vertical = st.selectbox("Filter by Vertical", ["Show Everything"] + list(VERTICAL_KEYWORDS.keys()))
    
    days = st.slider("Fiscal Lookback", 90, 730, 365)
    
    st.markdown("---")
    fetch_btn = st.button("🚀 Fetch Intelligence")
    
    st.info("**Tip:** If 'Sub-Awards' returns 0 results, it means the state hasn't reported their sub-grants yet. Use 'Prime Awards' to find the source money.")

# Main Content
if fetch_btn:
    with st.spinner(f"Querying Federal Database for {selected_state_name} ({mode})..."):
        df = fetch_state_data(selected_state_code, days, mode)
        
        if not df.empty:
            # 1. CREATE LINK
            # Sub-awards don't have nice pages on USAspending, so we only link Prime
            if "Prime" in mode:
                df['Link'] = "https://www.usaspending.gov/award/" + df['Generated Unique Award ID'].astype(str).apply(requests.utils.quote)
            else:
                df['Link'] = None 

            # 2. APPLY LOCAL FILTERS (The "Wide Net" Strategy)
            if selected_vertical != "Show Everything":
                keywords = VERTICAL_KEYWORDS[selected_vertical]
                pattern = '|'.join(keywords)
                
                # Filter by Description OR Agency OR Recipient
                filtered_df = df[
                    df['Description'].astype(str).str.contains(pattern, case=False, na=False) | 
                    df['Awarding Agency'].astype(str).str.contains(pattern, case=False, na=False) |
                    df['Recipient Name'].astype(str).str.contains(pattern, case=False, na=False)
                ]
                
                if filtered_df.empty:
                    st.warning(f"We found {len(df)} total awards, but none matched the keywords for **{selected_vertical}**.")
                    st.markdown("Showing all awards instead so you can explore.")
                    display_df = df
                else:
                    st.success(f"Filtered {len(df)} total awards down to **{len(filtered_df)}** relevant opportunities.")
                    display_df = filtered_df
            else:
                display_df = df

            # 3. METRICS
            total_vol = display_df['Award Amount'].sum()
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Volume", f"${total_vol:,.0f}")
            col2.metric("Opportunities", len(display_df))
            col3.metric("Data Source", "USAspending.gov API")

            # 4. CHARTS
            c1, c2 = st.columns(2)
            with c1:
                # Top Recipients
                recip_fig = px.bar(
                    display_df.head(10), 
                    y='Recipient Name', 
                    x='Award Amount', 
                    orientation='h', 
                    title="Who is getting the money?", 
                    color_discrete_sequence=[COLOR_PRIMARY]
                )
                recip_fig.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(recip_fig, use_container_width=True)
            
            with c2:
                # Funding Timeline
                # Ensure date is datetime
                display_df['Date'] = pd.to_datetime(display_df['Date'])
                display_df['Month'] = display_df['Date'].dt.to_period('M').astype(str)
                time_fig = px.area(
                    display_df.groupby('Month')['Award Amount'].sum().reset_index(), 
                    x='Month', 
                    y='Award Amount', 
                    title="Funding Trends", 
                    color_discrete_sequence=[COLOR_SECONDARY]
                )
                st.plotly_chart(time_fig, use_container_width=True)

            # 5. DATA TABLE
            st.subheader(f"📋 Detailed Lead List: {selected_vertical}")
            
            column_config = {
                "Award Amount": st.column_config.NumberColumn("Amount", format="$%.2f"),
                "Date": st.column_config.DateColumn("Award Date", format="YYYY-MM-DD"),
                "Description": st.column_config.TextColumn("Description", width="large")
            }
            
            # Only show link button if Prime
            if "Prime" in mode:
                column_config["Link"] = st.column_config.LinkColumn("Details", display_text="Open 🔗")
                cols_to_show = ["Date", "Recipient Name", "Award Amount", "Description", "Link"]
            else:
                cols_to_show = ["Date", "Recipient Name", "Award Amount", "Description"]

            st.dataframe(
                display_df[cols_to_show].sort_values("Award Amount", ascending=False),
                column_config=column_config,
                use_container_width=True,
                hide_index=True
            )
            
        else:
            st.warning(f"No results found for {mode} in {selected_state_name}.")
            st.markdown("""
            **Why?**
            * **Sub-Awards:** Many states do not report sub-awards in real-time. 
            * **Block Grants:** The money might be sitting in a 'Prime Award' to the State Dept.
            
            **Try this:** Switch the Funding Layer to **'Prime Awards'** and filter for 'School' or 'Workforce'.
            """)

else:
    # Landing Page
    st.markdown(f"""
    <div style='text-align:center; padding: 80px;'>
        <h1 style='color:{COLOR_PRIMARY}'>Bonterra Intelligence</h1>
        <p style='font-size: 18px;'>Live Federal Funding Tracker • Prime & Sub-Award Analysis</p>
        <br>
        <div style='display:inline-block; text-align:left; background:white; padding:20px; border-radius:10px; border:1px solid #eee;'>
            <b>🚀 How to use:</b><br>
            1. Select <b>State</b> (e.g., Arkansas)<br>
            2. Choose <b>Layer</b> (Prime Awards usually has the most data)<br>
            3. Click <b>Fetch Intelligence</b>
        </div>
    </div>
    """, unsafe_allow_html=True)
