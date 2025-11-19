import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import datetime

# --- 1. BONTERRA BRANDING & CONFIG ---
# Official/Approximate Bonterra Brand Colors
COLOR_PRIMARY = "#381360"   # Scarlet Gum
COLOR_SECONDARY = "#84EA9F" # Pastel Green
COLOR_ACCENT = "#6B3A91"    # Lighter Purple for hover/charts
COLOR_BG = "#F4F5F7"        # Light Gray Background
COLOR_TEXT = "#2C0020"

st.set_page_config(
    page_title="Bonterra | PubSec Intelligence",
    page_icon="🏛️",
    layout="wide"
)

# Custom CSS for a "High-End" Enterprise Look
st.markdown(f"""
    <style>
    /* Global Background */
    .stApp {{
        background-color: {COLOR_BG};
    }}
    
    /* Headings */
    h1, h2, h3 {{
        color: {COLOR_PRIMARY} !important;
        font-family: 'Segoe UI', Helvetica, sans-serif;
        font-weight: 700;
    }}
    
    /* Metric Cards (Top Row) */
    div[data-testid="stMetric"] {{
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        border-left: 6px solid {COLOR_SECONDARY};
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }}
    
    /* Sidebar */
    section[data-testid="stSidebar"] {{
        background-color: white;
        border-right: 1px solid #ddd;
    }}
    
    /* Buttons */
    div.stButton > button {{
        background-color: {COLOR_PRIMARY};
        color: white;
        border-radius: 6px;
        padding: 0.5rem 1rem;
        font-weight: 600;
        border: none;
        width: 100%;
    }}
    div.stButton > button:hover {{
        background-color: {COLOR_ACCENT};
        color: white;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. REFERENCE DATA (The "Engine") ---
# Full US State List
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

# INTELLIGENCE MAPPING: This maps verticals to specific Federal Program Numbers (CFDA)
# This fixes the "No Data" error by searching for Program IDs, not just loose keywords.
VERTICALS = {
    "Workforce Development": {
        "cfda": ["17.258", "17.259", "17.278", "17.207", "17.225"], 
        "keywords": ["WIOA", "Workforce", "Dislocated Worker", "Apprenticeship"],
        "desc": "WIOA Adult, Youth, Dislocated Worker & Wagner-Peyser"
    },
    "Violence Prevention (CVI)": {
        "cfda": ["16.575", "16.045", "16.738", "16.590"],
        "keywords": ["VOCA", "Victim", "Violence", "Stop School Violence"],
        "desc": "VOCA, CVIPI, Byrne JAG"
    },
    "Aging & Senior Services": {
        "cfda": ["93.044", "93.045", "93.052", "93.041", "93.042"],
        "keywords": ["Aging", "Older Americans", "Geriatric", "Adult Protective"],
        "desc": "OAA Title III (Supportive Services, Nutrition), Title VII"
    },
    "Re-entry & Recidivism": {
        "cfda": ["16.812", "16.838", "16.738"],
        "keywords": ["Reentry", "Second Chance", "Recidivism", "Corrections"],
        "desc": "Second Chance Act, Comprehensive Opioid, Stimulant, and Substance Abuse"
    },
    "School Districts (K-12)": {
        "cfda": ["84.010", "84.425", "84.027"],
        "keywords": ["School District", "ISD", "Elementary", "Board of Education"],
        "desc": "Title I Grants, ESSER (Covid Relief), Special Ed (IDEA)"
    }
}

# --- 3. DATA FETCHING LOGIC ---
@st.cache_data
def fetch_usaspending_data(state_code, vertical_config, days_back):
    url = "https://api.usaspending.gov/api/v2/search/spending_by_award/"
    
    start_date = (datetime.date.today() - datetime.timedelta(days=days_back)).strftime("%Y-%m-%d")
    end_date = datetime.date.today().strftime("%Y-%m-%d")
    
    # We perform TWO searches:
    # 1. CFDA Search (Highly Accurate)
    # 2. Keyword Search (Catch-all)
    
    payload = {
        "filters": {
            "time_period": [{"start_date": start_date, "end_date": end_date}],
            # Search by Recipient Location to find money flowing TO the state
            "recipient_locations": [{"country": "USA", "state": state_code}],
            "award_type_codes": ["A", "B", "C", "D"], # Grants & Direct Payments
            # HYBRID SEARCH: We filter by specific Program Numbers OR Keywords
            "program_numbers": vertical_config["cfda"]
        },
        "fields": [
            "Generated Unique Award ID",
            "Recipient Name", 
            "Award Amount", 
            "Description", 
            "Action Date", 
            "Awarding Agency",
            "CFDA Number",
            "CFDA Title"
        ],
        "limit": 100,
        "page": 1
    }
    
    try:
        response = requests.post(url, json=payload)
        data = response.json()
        df = pd.DataFrame(data['results'])
        
        # If CFDA search returns few results, try broadening with keywords
        if len(df) < 5:
            payload["filters"].pop("program_numbers")
            payload["filters"]["keyword_search"] = vertical_config["keywords"]
            response_broad = requests.post(url, json=payload)
            data_broad = response_broad.json()
            df_broad = pd.DataFrame(data_broad['results'])
            df = pd.concat([df, df_broad]).drop_duplicates(subset=['Generated Unique Award ID'])
            
        return df
    except Exception as e:
        return pd.DataFrame()

# --- 4. UI LAYOUT ---

# Sidebar
with st.sidebar:
    st.image("https://brandfetch.com/bonterratech.com/icon", width=80)
    st.markdown("## Bonterra | PubSec")
    
    # State Selector with Default to AR (since you asked about it)
    selected_state_name = st.selectbox("Region / State", options=list(US_STATES.values()), index=3) # Defaults to Arkansas
    selected_state_code = [k for k, v in US_STATES.items() if v == selected_state_name][0]

    selected_vertical = st.selectbox("Target Vertical", options=list(VERTICALS.keys()))
    
    # Helper text showing what we are tracking
    st.caption(f"Tracking: {VERTICALS[selected_vertical]['desc']}")
    
    days_lookback = st.slider("Lookback (Days)", 30, 365, 365) # Default to full year
    
    st.markdown("---")
    search_btn = st.button("🚀 Generate Report")
    
    st.markdown("### Other Free Sources")
    st.info("""
    • **Grants.gov:** For open applications
    • **SAM.gov:** For contract RFPs
    • **USAC.org:** For E-Rate (Schools)
    """)

# Main Dashboard
if search_btn:
    with st.spinner(f"Connecting to Federal Database for {selected_state_name}..."):
        df = fetch_usaspending_data(selected_state_code, VERTICALS[selected_vertical], days_lookback)
        
        if not df.empty:
            # Pre-processing
            df['Action Date'] = pd.to_datetime(df['Action Date'])
            df['Link'] = "https://www.usaspending.gov/award/" + df['Generated Unique Award ID'].astype(str).apply(requests.utils.quote)
            
            # Header Stats
            total_val = df['Award Amount'].sum()
            avg_val = df['Award Amount'].mean()
            
            st.title(f"Funding Report: {selected_vertical}")
            st.markdown(f"Recent federal investments flowing into **{selected_state_name}**.")
            
            # Metrics Row
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Investment Identified", f"${total_val:,.0f}")
            col2.metric("Deal Volume (Awards)", len(df))
            col3.metric("Avg. Award Size", f"${avg_val:,.0f}")
            
            st.markdown("---")

            # Charts Row
            c1, c2 = st.columns([1, 1])
            
            with c1:
                # Funding by Agency (Who is buying?)
                agency_agg = df.groupby("Awarding Agency")["Award Amount"].sum().reset_index().sort_values("Award Amount", ascending=True)
                fig_agency = px.bar(
                    agency_agg, y="Awarding Agency", x="Award Amount", 
                    orientation='h', title="Top Funding Agencies",
                    color_discrete_sequence=[COLOR_PRIMARY]
                )
                st.plotly_chart(fig_agency, use_container_width=True)
            
            with c2:
                # Funding Over Time (Trend)
                time_agg = df.groupby("Action Date")["Award Amount"].sum().reset_index()
                fig_time = px.line(
                    time_agg, x="Action Date", y="Award Amount", 
                    title="Investment Timeline", markers=True,
                    color_discrete_sequence=[COLOR_SECONDARY]
                )
                # Add area fill
                fig_time.update_traces(fill='tozeroy')
                st.plotly_chart(fig_time, use_container_width=True)

            # The "Lead List" Table
            st.subheader("📋 Opportunity Lead List")
            
            st.dataframe(
                df[["Action Date", "Recipient Name", "Award Amount", "Description", "Link"]].sort_values("Action Date", ascending=False),
                column_config={
                    "Link": st.column_config.LinkColumn("View Details", display_text="Open Award 🔗"),
                    "Award Amount": st.column_config.NumberColumn("Value", format="$%.2f"),
                    "Action Date": st.column_config.DateColumn("Award Date", format="MMM DD, YYYY"),
                    "Description": st.column_config.TextColumn("Grant Description", width="large")
                },
                use_container_width=True,
                hide_index=True
            )
        
        else:
            st.error(f"No data found for {selected_vertical} in {selected_state_name}.")
            st.markdown("""
            **Why?**
            1. States often receive "Block Grants" at the start of the Fiscal Year (October).
            2. Try increasing the **Lookback slider** to 365 days.
            3. Try searching for a larger state (e.g., TX, CA) to verify the system is working.
            """)

else:
    # Empty State (Beautiful Landing Page)
    st.markdown(f"""
    <div style="text-align: center; padding: 60px; background-color: white; border-radius: 12px; border: 1px solid #eee;">
        <h2 style="color: {COLOR_PRIMARY};">Welcome to Bonterra Public Sector Intelligence</h2>
        <p style="font-size: 18px; color: #666;">
            Use the sidebar to uncover <b>Sales Leads</b> and <b>Funding Flows</b> from live government data.
        </p>
    </div>
    """, unsafe_allow_html=True)
