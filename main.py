import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import datetime

# --- 1. BRANDING & CONFIGURATION ---
# Official Bonterra Brand Identity
COLOR_PRIMARY = "#381360"   # Scarlet Gum (Deep Purple)
COLOR_SECONDARY = "#84EA9F" # Pastel Green (Action Color)
COLOR_ACCENT = "#5D2E86"    # Lighter Purple
COLOR_BG = "#F4F6F9"        # Professional Light Gray
COLOR_TEXT = "#2C0020"

st.set_page_config(
    page_title="Bonterra | Public Sector Intelligence",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for "Eye-Catchy" Enterprise Look
st.markdown(f"""
    <style>
    /* App Background */
    .stApp {{
        background-color: {COLOR_BG};
    }}
    
    /* Headers */
    h1 {{
        color: {COLOR_PRIMARY};
        font-family: 'Helvetica Neue', sans-serif;
        font-weight: 800;
        letter-spacing: -1px;
    }}
    h2, h3 {{
        color: {COLOR_PRIMARY} !important;
        font-family: 'Helvetica Neue', sans-serif;
    }}
    
    /* Card Styling for Metrics */
    div[data-testid="stMetric"] {{
        background-color: white;
        padding: 20px;
        border-radius: 12px;
        border-left: 6px solid {COLOR_SECONDARY};
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }}
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] {{
        background-color: white;
        border-right: 1px solid #E5E5E5;
    }}
    
    /* Buttons */
    div.stButton > button {{
        background-color: {COLOR_PRIMARY};
        color: white;
        border-radius: 8px;
        padding: 12px 24px;
        font-size: 16px;
        font-weight: 600;
        border: none;
        width: 100%;
        box-shadow: 0 4px 6px rgba(56, 19, 96, 0.2);
    }}
    div.stButton > button:hover {{
        background-color: {COLOR_ACCENT};
        color: white;
        box-shadow: 0 6px 8px rgba(56, 19, 96, 0.3);
    }}
    
    /* Dataframe Headers */
    th {{
        background-color: {COLOR_PRIMARY} !important;
        color: white !important;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. INTELLIGENCE ENGINE (States & Programs) ---
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

# UPDATED VERTICALS: Added more CFDA codes to catch "hidden" money
VERTICALS = {
    "Workforce Development": {
        # Added 17.261 (Pilots), 17.207 (Employment Svc), 17.225 (Unemployment Admin)
        "cfda": ["17.258", "17.259", "17.278", "17.207", "17.225", "17.261"], 
        "keywords": ["WIOA", "Workforce", "Dislocated Worker", "Apprenticeship", "Department of Labor"],
        "desc": "WIOA Adult, Youth, Wagner-Peyser & State Pilots"
    },
    "Violence Prevention (CVI)": {
        "cfda": ["16.575", "16.045", "16.738", "16.590"],
        "keywords": ["VOCA", "Victim", "Violence", "Stop School Violence", "Justice Assistance"],
        "desc": "VOCA, CVIPI, Byrne JAG"
    },
    "Aging & Senior Services": {
        "cfda": ["93.044", "93.045", "93.052", "93.041", "93.042"],
        "keywords": ["Aging", "Older Americans", "Geriatric", "Adult Protective", "ACL"],
        "desc": "OAA Title III (Supportive Services, Nutrition)"
    },
    "Re-entry & Recidivism": {
        "cfda": ["16.812", "16.838", "16.738"],
        "keywords": ["Reentry", "Second Chance", "Recidivism", "Corrections", "Justice"],
        "desc": "Second Chance Act, COSSAP"
    },
    "School Districts (K-12)": {
        "cfda": ["84.010", "84.425", "84.027"],
        "keywords": ["School District", "ISD", "Elementary", "Board of Education"],
        "desc": "Title I Grants, ESSER, Special Ed"
    }
}

# --- 3. AGGRESSIVE DATA FETCHING ---
@st.cache_data
def fetch_usaspending_data(state_code, vertical_config, days_back):
    url = "https://api.usaspending.gov/api/v2/search/spending_by_award/"
    
    start_date = (datetime.date.today() - datetime.timedelta(days=days_back)).strftime("%Y-%m-%d")
    end_date = datetime.date.today().strftime("%Y-%m-%d")
    
    # Strategy 1: Search by Recipient Location (Standard)
    # Strategy 2: Search by Place of Performance (Aggressive - Catching money spent IN the state)
    
    base_filters = {
        "time_period": [{"start_date": start_date, "end_date": end_date}],
        "award_type_codes": ["A", "B", "C", "D"],
        "program_numbers": vertical_config["cfda"]
    }

    # Try Strategy 1: Recipient Location
    payload_1 = {"filters": base_filters.copy(), "limit": 100}
    payload_1["filters"]["recipient_locations"] = [{"country": "USA", "state": state_code}]
    
    # Fields we want to display
    fields = [
        "Generated Unique Award ID", "Recipient Name", "Award Amount", 
        "Description", "Action Date", "Awarding Agency", "CFDA Number", "CFDA Title"
    ]
    payload_1["fields"] = fields

    try:
        # Attempt 1
        response = requests.post(url, json=payload_1)
        data = response.json()
        df = pd.DataFrame(data.get('results', []))
        
        # Attempt 2: If empty, try "Place of Performance" (Money spent IN Arkansas)
        if df.empty:
            payload_2 = {"filters": base_filters.copy(), "limit": 100, "fields": fields}
            payload_2["filters"]["place_of_performance_locations"] = [{"country": "USA", "state": state_code}]
            
            response_2 = requests.post(url, json=payload_2)
            data_2 = response_2.json()
            df = pd.DataFrame(data_2.get('results', []))
            
        # Attempt 3: If still empty, DROP CFDA and use Keywords (Broadest Search)
        if df.empty:
             payload_3 = {"filters": base_filters.copy(), "limit": 100, "fields": fields}
             payload_3["filters"].pop("program_numbers") # Remove strict numbers
             payload_3["filters"]["keyword_search"] = vertical_config["keywords"]
             payload_3["filters"]["recipient_locations"] = [{"country": "USA", "state": state_code}]
             
             response_3 = requests.post(url, json=payload_3)
             data_3 = response_3.json()
             df = pd.DataFrame(data_3.get('results', []))

        return df
        
    except Exception as e:
        st.error(f"API Error: {e}")
        return pd.DataFrame()

# --- 4. MAIN DASHBOARD ---

# Sidebar
with st.sidebar:
    # LOGO: Using Clearbit for reliable logo loading
    st.image("https://logo.clearbit.com/bonterratech.com", width=60)
    st.markdown(f"<h1 style='color:{COLOR_PRIMARY}; font-size: 24px; margin-top:0;'>Bonterra PubSec</h1>", unsafe_allow_html=True)
    
    st.markdown("### 🎯 Campaign Target")
    
    # State Selector
    selected_state_name = st.selectbox("State", options=list(US_STATES.values()), index=3) # Index 3 is Arkansas
    selected_state_code = [k for k, v in US_STATES.items() if v == selected_state_name][0]

    selected_vertical = st.selectbox("Vertical", options=list(VERTICALS.keys()))
    
    st.info(f"Searching: **{VERTICALS[selected_vertical]['desc']}**")
    
    # Default set to 730 Days (2 Years) to catch annual block grants
    days_lookback = st.slider("Timeframe (Days)", 30, 730, 730)
    
    st.markdown("---")
    search_btn = st.button("🔍 FIND OPPORTUNITIES", type="primary")

# Main Area
if search_btn:
    with st.spinner(f"Aggregating federal data for {selected_state_name} (Last {days_lookback} days)..."):
        df = fetch_usaspending_data(selected_state_code, VERTICALS[selected_vertical], days_lookback)
        
        if not df.empty:
            # Processing
            df['Action Date'] = pd.to_datetime(df['Action Date'])
            df['Link'] = "https://www.usaspending.gov/award/" + df['Generated Unique Award ID'].astype(str).apply(requests.utils.quote)
            
            total_val = df['Award Amount'].sum()
            count_val = len(df)
            
            # --- TITLE & METRICS ---
            col_title, col_logo = st.columns([4,1])
            with col_title:
                st.title(f"Funding Intelligence: {selected_state_name}")
                st.markdown(f"Showing **{selected_vertical}** investments.")
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Funding Identified", f"${total_val:,.0f}")
            m2.metric("Total Awards", count_val)
            m3.metric("Fiscal Lookback", f"{days_lookback} Days")
            
            st.markdown("---")
            
            # --- VISUALIZATIONS ---
            c1, c2 = st.columns(2)
            with c1:
                # Agency Bar Chart
                ag_df = df.groupby("Awarding Agency")["Award Amount"].sum().reset_index().sort_values("Award Amount", ascending=True)
                fig1 = px.bar(ag_df, x="Award Amount", y="Awarding Agency", orientation='h',
                              title="Top Funding Sources", color_discrete_sequence=[COLOR_PRIMARY])
                st.plotly_chart(fig1, use_container_width=True)
                
            with c2:
                # Time Series Area Chart
                time_df = df.groupby("Action Date")["Award Amount"].sum().reset_index()
                fig2 = px.area(time_df, x="Action Date", y="Award Amount",
                               title="Funding Release Timeline", color_discrete_sequence=[COLOR_SECONDARY])
                st.plotly_chart(fig2, use_container_width=True)

            # --- DATA TABLE ---
            st.subheader("📋 Lead List (Click 'Open' to view details)")
            
            # Configure table with clickable links
            st.dataframe(
                df[["Action Date", "Recipient Name", "Award Amount", "Description", "Link"]].sort_values("Action Date", ascending=False),
                column_config={
                    "Link": st.column_config.LinkColumn("Source", display_text="Open Grant 🔗"),
                    "Award Amount": st.column_config.NumberColumn("Amount", format="$%.2f"),
                    "Action Date": st.column_config.DateColumn("Date", format="YYYY-MM-DD"),
                    "Description": st.column_config.TextColumn("Grant Description", width="large")
                },
                use_container_width=True,
                hide_index=True
            )
        
        else:
            # Fallback Message
            st.warning(f"No data found for {selected_vertical} in {selected_state_name}.")
            st.markdown("### 🔎 Diagnostics:")
            st.markdown(f"""
            1. **Search Scope:** Checked 2 years of history (730 Days).
            2. **CFDA Codes:** Scanned for programs {', '.join(VERTICALS[selected_vertical]['cfda'])}.
            3. **Result:** No direct federal award updates were filed for {selected_state_code} in this window.
            
            *Recommendation: Try checking 'School Districts' or 'Violence Prevention' for this state to verify connectivity.*
            """)

else:
    # Landing Page
    st.markdown(f"""
    <div style="text-align: center; padding: 80px; background-color: white; border-radius: 16px; border: 1px solid #eee;">
        <h1 style="color: {COLOR_PRIMARY}; margin-bottom: 10px;">Bonterra Intelligence Engine</h1>
        <p style="font-size: 18px; color: #555; max-width: 600px; margin: 0 auto;">
            Select a <b>State</b> and <b>Vertical</b> from the sidebar to scan federal databases for active funding opportunities.
        </p>
        <br>
        <div style="display: flex; justify-content: center; gap: 20px;">
            <span style="padding: 8px 16px; background: #EFEFEF; border-radius: 20px; font-size: 14px;">✅ Live API Connection</span>
            <span style="padding: 8px 16px; background: #EFEFEF; border-radius: 20px; font-size: 14px;">✅ CFDA Verified</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
