import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import datetime

# --- 1. BONTERRA ENTERPRISE THEME ---
st.set_page_config(
    page_title="Bonterra Intelligence",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Brand Palette
COLOR_PRIMARY = "#381360"   # Scarlet Gum
COLOR_SECONDARY = "#84EA9F" # Pastel Green
COLOR_ACCENT = "#6B3A91"    # Highlight Purple
COLOR_BG = "#F4F6F8"        # Enterprise Gray

st.markdown(f"""
    <style>
    .stApp {{ background-color: {COLOR_BG}; }}
    h1, h2, h3 {{ color: {COLOR_PRIMARY} !important; font-family: 'Segoe UI', sans-serif; }}
    div[data-testid="stMetric"] {{
        background-color: #FFFFFF; border: 1px solid #ddd; padding: 15px;
        border-top: 5px solid {COLOR_SECONDARY}; border-radius: 8px;
    }}
    div.stButton > button {{
        background-color: {COLOR_PRIMARY}; color: white; border-radius: 6px; border: none; padding: 10px;
    }}
    div.stButton > button:hover {{ background-color: {COLOR_ACCENT}; color: white; }}
    thead tr th {{ background-color: {COLOR_PRIMARY} !important; color: white !important; }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. INTELLIGENCE DATA MAP ---
US_STATES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California",
    "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "DC": "District of Columbia",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois",
    "IN": "Indiana", "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana",
    "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
    "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont",
    "VA": "Virginia", "WA": "Washington", "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming"
}

VERTICALS = {
    "School Districts (K-12)": {
        # KEY CHANGE: Removed specific school district keywords.
        # Now targeting the Funding STREAMS (Title I, IDEA, ESSER) which go to the State.
        "cfda": ["84.010", "84.027", "84.425", "84.287", "84.367", "84.424"],
        "keywords": ["Education", "School", "Elementary", "Secondary", "Instruction"],
        "desc": "Title I (Disadvantaged), IDEA (Special Ed), ESSER (Relief)"
    },
    "Workforce Development": {
        "cfda": ["17.258", "17.259", "17.278", "17.207", "17.225"],
        "keywords": ["Workforce", "Labor", "Employment", "Training"],
        "desc": "WIOA & Employment Services"
    },
    "Violence Prevention": {
        "cfda": ["16.575", "16.045", "16.738"],
        "keywords": ["Victim", "Violence", "Justice", "Safety"],
        "desc": "VOCA & CVI"
    },
     "Aging & Seniors": {
        "cfda": ["93.044", "93.045", "93.052"], 
        "keywords": ["Aging", "Elder", "Senior", "Community Living"],
        "desc": "OAA Title III"
    }
}

# --- 3. "NUCLEAR" DATA FETCHING (3-Stage Fallback) ---
@st.cache_data
def fetch_usaspending_data(state_code, vertical_config, days_back):
    url = "https://api.usaspending.gov/api/v2/search/spending_by_award/"
    start_date = (datetime.date.today() - datetime.timedelta(days=days_back)).strftime("%Y-%m-%d")
    end_date = datetime.date.today().strftime("%Y-%m-%d")
    
    fields = ["Generated Unique Award ID", "Recipient Name", "Award Amount", "Description", "Action Date", "Awarding Agency"]
    
    base_filters = {
        "time_period": [{"start_date": start_date, "end_date": end_date}],
        "award_type_codes": ["A", "B", "C", "D"]
    }

    # --- ATTEMPT 1: The "Perfect" Search (CFDA + Recipient in State) ---
    # This looks for money sent TO an Arkansas address with the right Program ID.
    try:
        payload = {"filters": base_filters.copy(), "fields": fields, "limit": 100}
        payload["filters"]["recipient_locations"] = [{"country": "USA", "state": state_code}]
        payload["filters"]["program_numbers"] = vertical_config["cfda"]
        
        resp = requests.post(url, json=payload).json()
        df = pd.DataFrame(resp.get('results', []))
        
        # --- ATTEMPT 2: The "Broad" Search (CFDA Only + Place of Performance) ---
        # If Attempt 1 fails, maybe the recipient address is DC, but money is spent in AR.
        if df.empty:
            payload["filters"].pop("recipient_locations") # Remove recipient constraint
            payload["filters"]["place_of_performance_locations"] = [{"country": "USA", "state": state_code}]
            
            resp = requests.post(url, json=payload).json()
            df = pd.DataFrame(resp.get('results', []))

        # --- ATTEMPT 3: The "Desperate" Search (Keywords Only) ---
        # If CFDA codes fail (data entry error by govt), search for "Education" in Arkansas.
        if df.empty:
            payload["filters"].pop("program_numbers") # Drop CFDA strictness
            payload["filters"]["keyword_search"] = vertical_config["keywords"]
            
            resp = requests.post(url, json=payload).json()
            df = pd.DataFrame(resp.get('results', []))
            
        return df

    except Exception as e:
        return pd.DataFrame()

# --- 4. DASHBOARD ---
with st.sidebar:
    try:
        st.image("https://logo.clearbit.com/bonterratech.com", width=60)
    except:
        st.header("Bonterra")
    
    st.markdown("### PubSec Intelligence")
    
    # Set default to Arkansas for you
    state_names = list(US_STATES.values())
    selected_state_name = st.selectbox("State", options=state_names, index=state_names.index("Arkansas"))
    selected_state_code = [k for k, v in US_STATES.items() if v == selected_state_name][0]

    selected_vertical = st.selectbox("Vertical", options=list(VERTICALS.keys()))
    days_lookback = st.slider("Fiscal Lookback (Days)", 90, 730, 730) # Default 2 years
    
    st.info(f"Target: **{VERTICALS[selected_vertical]['desc']}**")
    search_btn = st.button("🔍 Find Funding Flows")

if search_btn:
    with st.spinner(f"Deep scanning federal awards in {selected_state_name}..."):
        df = fetch_usaspending_data(selected_state_code, VERTICALS[selected_vertical], days_lookback)
        
        if not df.empty:
            df['Action Date'] = pd.to_datetime(df['Action Date'])
            df['Link'] = "https://www.usaspending.gov/award/" + df['Generated Unique Award ID'].astype(str).apply(requests.utils.quote)
            
            # HEADER
            st.title(f"Funding Report: {selected_state_name}")
            st.markdown(f"Showing active **{selected_vertical}** awards.")
            
            # METRICS
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Volume", f"${df['Award Amount'].sum():,.0f}")
            m2.metric("Awards Found", len(df))
            m3.metric("Avg. Size", f"${df['Award Amount'].mean():,.0f}")
            
            st.markdown("---")
            
            # CHARTS
            c1, c2 = st.columns(2)
            with c1:
                # Show WHO is getting the money (Recipient)
                # This solves the K-12 confusion (showing State Dept of Ed vs School District)
                recip_df = df.groupby("Recipient Name")["Award Amount"].sum().reset_index().sort_values("Award Amount", ascending=True).tail(10)
                fig = px.bar(recip_df, x="Award Amount", y="Recipient Name", orientation='h', title="Top Recipients (Who has the money?)", color_discrete_sequence=[COLOR_PRIMARY])
                st.plotly_chart(fig, use_container_width=True)
            
            with c2:
                df['Month'] = df['Action Date'].dt.to_period('M').astype(str)
                time_df = df.groupby('Month')['Award Amount'].sum().reset_index()
                fig2 = px.area(time_df, x='Month', y='Award Amount', title="Funding Timeline", color_discrete_sequence=[COLOR_SECONDARY])
                st.plotly_chart(fig2, use_container_width=True)

            # DATA TABLE
            st.subheader("📋 Master Award List")
            st.dataframe(
                df[["Action Date", "Recipient Name", "Award Amount", "Description", "Link"]].sort_values("Award Amount", ascending=False),
                column_config={
                    "Link": st.column_config.LinkColumn("Details", display_text="View 🔗"),
                    "Award Amount": st.column_config.NumberColumn("Value", format="$%.2f"),
                    "Action Date": st.column_config.DateColumn("Date", format="YYYY-MM-DD"),
                    "Description": st.column_config.TextColumn("Description", width="medium")
                },
                use_container_width=True,
                hide_index=True
            )
        else:
            st.error(f"No Primary Awards found for {selected_vertical} in {selected_state_name}.")
            st.markdown("""
            **Explanation:**
            We searched for **Direct Federal -> State** flows. If this is empty for K-12, it is highly unusual.
            
            **Troubleshooting:**
            1. Verify the lookback is set to **730 Days**.
            2. The API might be experiencing downtime for this specific CFDA cluster.
            """)
else:
    st.markdown(f"<div style='text-align:center; padding:50px;'><h2 style='color:{COLOR_PRIMARY}'>Bonterra Intelligence V5.0</h2><p>Select parameters to begin deep scan.</p></div>", unsafe_allow_html=True)
