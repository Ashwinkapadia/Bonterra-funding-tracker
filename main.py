import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import datetime

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Bonterra Intelligence", page_icon="🏛️", layout="wide")
COLOR_PRIMARY = "#381360"
COLOR_SECONDARY = "#84EA9F"
COLOR_BG = "#F4F6F8"

st.markdown(f"""
    <style>
    .stApp {{ background-color: {COLOR_BG}; }}
    h1, h2, h3 {{ color: {COLOR_PRIMARY} !important; font-family: 'Segoe UI', sans-serif; }}
    div.stButton > button {{ background-color: {COLOR_PRIMARY}; color: white; border: none; border-radius: 6px; padding: 10px 20px; width: 100%; }}
    div.stButton > button:hover {{ background-color: #5D2E86; color: white; }}
    div[data-testid="stMetric"] {{ background-color: white; border-left: 5px solid {COLOR_SECONDARY}; border-radius: 8px; padding: 15px; }}
    .stDataFrame {{ background-color: white; padding: 10px; border-radius: 10px; }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA MAPS ---
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

VERTICAL_KEYWORDS = {
    "School Districts (K-12)": ["school", "education", "elementary", "isd", "title i", "esser", "idea", "instruction"],
    "Workforce Development": ["workforce", "wioa", "labor", "employment", "job training", "apprentice"],
    "Violence Prevention": ["violence", "victim", "voca", "abuse", "safety", "justice"],
    "Aging Services": ["aging", "elder", "senior", "nutrition", "adult protective"],
    "Veterans": ["veteran", "homeless vet", "hv rp", "ssvf"],
    "Housing & Homelessness": ["housing", "homeless", "tenant", "rent", "cdbg"]
}

# --- 3. THE CORRECTED API ENGINE ---
@st.cache_data
def fetch_prime_awards(state_code, days_back):
    url = "https://api.usaspending.gov/api/v2/search/spending_by_award/"
    
    # Date Calculation
    end_date = datetime.date.today().strftime("%Y-%m-%d")
    start_date = (datetime.date.today() - datetime.timedelta(days=days_back)).strftime("%Y-%m-%d")
    
    # FIX 1: Include GRANTS (02-05) not just Contracts (A-D)
    # 02: Block Grant, 03: Formula Grant, 04: Project Grant, 05: Cooperative Agreement
    award_types = ["A", "B", "C", "D", "02", "03", "04", "05"]
    
    # FIX 2: Use "Award Amount" for sorting. It works for BOTH Grants and Contracts.
    # "Action Date" crashes Contracts; "Start Date" crashes Grants. "Award Amount" is universal.
    
    payload = {
        "filters": {
            "time_period": [{"start_date": start_date, "end_date": end_date}],
            "award_type_codes": award_types,
            "place_of_performance_locations": [{"country": "USA", "state": state_code}]
        },
        "fields": [
            "Generated Unique Award ID", 
            "Recipient Name", 
            "Award Amount", 
            "Description", 
            "Awarding Agency",
            "Date Signed" # We request a generic date field
        ],
        "limit": 100,
        "sort": "Award Amount",
        "order": "desc"
    }

    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            return pd.DataFrame(response.json().get('results', []))
        else:
            st.error(f"API Error: {response.text}")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Connection Error: {e}")
        return pd.DataFrame()

# --- 4. DASHBOARD ---
with st.sidebar:
    st.image("https://logo.clearbit.com/bonterratech.com", width=60)
    st.title("Bonterra Intelligence")
    
    selected_state_name = st.selectbox("Target State", list(US_STATES.values()), index=3) # Default AR
    selected_state_code = [k for k, v in US_STATES.items() if v == selected_state_name][0]
    
    selected_vertical = st.selectbox("Filter Results", ["Show Everything"] + list(VERTICAL_KEYWORDS.keys()))
    days = st.slider("Lookback Days", 90, 730, 365)
    
    fetch_btn = st.button("🚀 Find Funding")

if fetch_btn:
    with st.spinner(f"Scanning Grants & Contracts for {selected_state_name}..."):
        df = fetch_prime_awards(selected_state_code, days)
        
        if not df.empty:
            # Normalize Date
            # The API might return 'Date Signed', 'Start Date', or 'Action Date' depending on type
            # We coerce whatever date column came back
            date_cols = [c for c in df.columns if 'Date' in c]
            if date_cols:
                df['Date'] = pd.to_datetime(df[date_cols[0]])
            
            # Create Link
            df['Link'] = "https://www.usaspending.gov/award/" + df['Generated Unique Award ID'].astype(str).apply(requests.utils.quote)
            
            # Local Filter
            if selected_vertical != "Show Everything":
                keywords = VERTICAL_KEYWORDS[selected_vertical]
                pattern = '|'.join(keywords)
                filtered_df = df[
                    df['Description'].astype(str).str.contains(pattern, case=False, na=False) | 
                    df['Awarding Agency'].astype(str).str.contains(pattern, case=False, na=False) |
                    df['Recipient Name'].astype(str).str.contains(pattern, case=False, na=False)
                ]
                display_df = filtered_df
                st.success(f"Found {len(df)} total awards. Filtered down to **{len(display_df)} {selected_vertical}** opportunities.")
            else:
                display_df = df
                st.info(f"Showing top {len(display_df)} largest awards by value.")

            if not display_df.empty:
                # Metrics
                m1, m2 = st.columns(2)
                m1.metric("Total Value", f"${display_df['Award Amount'].sum():,.0f}")
                m2.metric("Count", len(display_df))
                
                # Charts
                c1, c2 = st.columns(2)
                with c1:
                    fig = px.bar(display_df.head(10), y='Recipient Name', x='Award Amount', orientation='h', title="Top Recipients", color_discrete_sequence=[COLOR_PRIMARY])
                    fig.update_layout(yaxis={'categoryorder':'total ascending'})
                    st.plotly_chart(fig, use_container_width=True)
                with c2:
                    if 'Date' in display_df.columns:
                        display_df['Month'] = display_df['Date'].dt.to_period('M').astype(str)
                        fig2 = px.area(display_df.groupby('Month')['Award Amount'].sum().reset_index(), x='Month', y='Award Amount', title="Funding Timeline", color_discrete_sequence=[COLOR_SECONDARY])
                        st.plotly_chart(fig2, use_container_width=True)

                # Table
                st.subheader("📋 Opportunity List")
                st.dataframe(
                    display_df[["Date", "Recipient Name", "Award Amount", "Description", "Link"]],
                    column_config={
                        "Link": st.column_config.LinkColumn("Link", display_text="Open 🔗"),
                        "Award Amount": st.column_config.NumberColumn("Amount", format="$%.2f"),
                        "Date": st.column_config.DateColumn("Date", format="YYYY-MM-DD")
                    },
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.warning(f"No {selected_vertical} matches found in the top 100 results. Try 'Show Everything' to check raw data.")
        
        else:
            st.error("No data found. Check if the State Code matches the Place of Performance.")
