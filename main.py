import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import datetime

# --- 1. BRAND & PAGE CONFIGURATION ---
# Official Bonterra Hex Codes
COLOR_BG = "#F5F5FF"       # Titan White (Background)
COLOR_PRIMARY = "#381360"  # Scarlet Gum (Headers, Primary Buttons)
COLOR_ACCENT = "#84EA9F"   # Pastel Green (Highlights, Secondary Data)
COLOR_TEXT = "#2C0020"     # Dark Purple (Text)
COLOR_CARD = "#FFFFFF"     # White (Cards)

st.set_page_config(
    page_title="Bonterra | Public Sector Intelligence",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS for "Eye-Catchy" Dashboard feel
st.markdown(f"""
    <style>
    /* Global Background */
    .stApp {{
        background-color: {COLOR_BG};
    }}
    
    /* Headers */
    h1, h2, h3 {{
        color: {COLOR_PRIMARY} !important;
        font-family: 'Helvetica Neue', sans-serif;
        font-weight: 700;
    }}
    
    /* Metric Cards */
    div[data-testid="stMetric"] {{
        background-color: {COLOR_CARD};
        padding: 15px;
        border-radius: 8px;
        border-left: 5px solid {COLOR_ACCENT};
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }}
    
    /* Data Tables */
    div[data-testid="stDataFrame"] {{
        background-color: {COLOR_CARD};
        border-radius: 8px;
        padding: 10px;
    }}
    
    /* Sidebar styling */
    section[data-testid="stSidebar"] {{
        background-color: #FFFFFF;
        border-right: 1px solid #E0E0E0;
    }}
    
    /* Primary Button */
    div.stButton > button {{
        background-color: {COLOR_PRIMARY};
        color: white;
        border-radius: 6px;
        font-weight: bold;
        border: none;
        padding: 10px 20px;
    }}
    div.stButton > button:hover {{
        background-color: #5D2E86; /* Lighter Purple */
        color: white;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. REFERENCE DATA ---
# Full State Dictionary
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
    "Workforce Development": {
        "keywords": ["WIOA", "Workforce Innovation", "Apprenticeship", "Dislocated Worker", "Job Corps", "Wagner-Peyser"],
    },
    "Violence Prevention (CVI)": {
        "keywords": ["Violence Intervention", "VOCA", "Victim Assistance", "Stop School Violence", "CVIPI", "Gun Violence", "Sexual Assault"],
    },
    "Aging & Senior Services": {
        "keywords": ["Older Americans Act", "Area Agency on Aging", "Geriatric", "Nutrition Services", "ACL", "Adult Protective", "Meals on Wheels"],
    },
    "Re-entry & Recidivism": {
        "keywords": ["Reentry", "Recidivism", "Second Chance Act", "Justice Reinvestment", "Juvenile Justice", "Corrections"],
    },
    "Veterans Services": {
        "keywords": ["Veterans Affairs", "Homeless Veterans", "HVRP", "State Veterans Home", "SSVF"],
    },
    "Housing & Homelessness": {
        "keywords": ["Continuum of Care", "Emergency Solutions Grant", "CDBG", "Affordable Housing", "Homelessness Prevention"],
    },
    "School Districts (K-12)": {
        "keywords": ["School District", "ISD", "Board of Education", "Public Schools", "Elementary", "ESSER"],
    }
}

# --- 3. DATA FETCHING ---
@st.cache_data
def fetch_usaspending_data(state_code, vertical_data, days_back):
    url = "https://api.usaspending.gov/api/v2/search/spending_by_award/"
    start_date = (datetime.date.today() - datetime.timedelta(days=days_back)).strftime("%Y-%m-%d")
    end_date = datetime.date.today().strftime("%Y-%m-%d")
    
    payload = {
        "filters": {
            "time_period": [{"start_date": start_date, "end_date": end_date}],
            "place_of_performance_locations": [{"country": "USA", "state": state_code}],
            "award_type_codes": ["A", "B", "C", "D"], # Grants and Direct Payments
            "keyword_search": vertical_data["keywords"]
        },
        "fields": [
            "Generated Unique Award ID", # Critical for the link
            "PIID",
            "FAIN",
            "Recipient Name", 
            "Award Amount", 
            "Description", 
            "Action Date", 
            "Awarding Agency", 
            "Awarding Sub Agency"
        ],
        "limit": 100,
        "page": 1
    }
    
    try:
        response = requests.post(url, json=payload)
        data = response.json()
        df = pd.DataFrame(data['results'])
        return df
    except Exception as e:
        return pd.DataFrame()

# --- 4. DASHBOARD UI ---

# Sidebar with Logo
with st.sidebar:
    # Fetching Bonterra Icon dynamically
    st.image("https://brandfetch.com/bonterratech.com/icon", width=80)
    st.title("Bonterra | PubSec")
    st.markdown("### 🎯 Campaign Settings")
    
    # State Selector (Reversed map to get Code)
    selected_state_name = st.selectbox("Target State", options=list(US_STATES.values()), index=42) # Default TX
    selected_state_code = [k for k, v in US_STATES.items() if v == selected_state_name][0]

    selected_vertical = st.selectbox("Target Vertical", options=list(VERTICALS.keys()))
    days_lookback = st.slider("Lookback Period (Days)", 30, 365, 60)
    
    st.markdown("---")
    search_btn = st.button("🔍 Find Opportunities", type="primary")
    
    st.markdown("### ℹ️ Data Sources")
    st.caption("• **USAspending.gov** (Federal Flow-down)\n• **Real-time API** (No manual uploads)")

# Main Content
if search_btn:
    with st.spinner(f"Analyzing federal flows to {selected_state_name}..."):
        df = fetch_usaspending_data(selected_state_code, VERTICALS[selected_vertical], days_lookback)
        
        if not df.empty:
            # PRE-PROCESSING
            df['Action Date'] = pd.to_datetime(df['Action Date'])
            # Create Clickable Link
            # USAspending URL format: https://www.usaspending.gov/award/{Generated Unique Award ID}
            df['Link'] = "https://www.usaspending.gov/award/" + df['Generated Unique Award ID'].astype(str).apply(lambda x: requests.utils.quote(x))
            
            # --- HEADER METRICS ---
            total_val = df['Award Amount'].sum()
            count_val = len(df)
            top_recipient = df.groupby('Recipient Name')['Award Amount'].sum().idxmax()
            
            st.title(f"💰 {selected_vertical} in {selected_state_name}")
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Investment Identified", f"${total_val:,.0f}", help="Total federal obligations in this period")
            c2.metric("New Grant Awards", count_val, help="Number of distinct award actions")
            c3.metric("Top Recipient", top_recipient[:20]+"...", help=top_recipient)
            
            st.markdown("---")
            
            # --- CHARTS (Visuals for Management) ---
            chart1, chart2 = st.columns(2)
            
            with chart1:
                # Bar Chart: Funding by Sub-Agency
                ag_df = df.groupby("Awarding Sub Agency")["Award Amount"].sum().reset_index().sort_values("Award Amount", ascending=True).tail(7)
                fig1 = px.bar(ag_df, x="Award Amount", y="Awarding Sub Agency", orientation='h', 
                              title="Funding by Agency", text_auto='.2s',
                              color_discrete_sequence=[COLOR_PRIMARY])
                fig1.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig1, use_container_width=True)
            
            with chart2:
                # Line Chart: Funding over Time
                time_df = df.groupby("Action Date")["Award Amount"].sum().reset_index()
                fig2 = px.line(time_df, x="Action Date", y="Award Amount", 
                               title="Investment Timeline", markers=True,
                               color_discrete_sequence=[COLOR_ACCENT])
                fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                # Fill area under line
                fig2.update_traces(fill='tozeroy')
                st.plotly_chart(fig2, use_container_width=True)

            # --- DETAILED TABLE WITH LINKS ---
            st.subheader("📋 Detailed Opportunity List")
            
            # We use Streamlit's ColumnConfig to make the Link column clickable
            display_cols = ["Action Date", "Recipient Name", "Award Amount", "Description", "Link"]
            
            st.dataframe(
                df[display_cols].sort_values("Action Date", ascending=False),
                column_config={
                    "Link": st.column_config.LinkColumn(
                        "View Award",
                        help="Click to view full details on USAspending.gov",
                        validate="^https://www.usaspending.gov/award/.*",
                        display_text="Open 🔗"
                    ),
                    "Award Amount": st.column_config.NumberColumn(
                        "Amount",
                        format="$%.2f"
                    ),
                    "Action Date": st.column_config.DateColumn(
                        "Date",
                        format="MMM DD, YYYY"
                    ),
                    "Description": st.column_config.TextColumn(
                        "Description",
                        width="large"
                    )
                },
                use_container_width=True,
                hide_index=True
            )
            
        else:
            st.warning(f"No data found for **{selected_vertical}** in **{selected_state_name}** over the last {days_lookback} days.")
            st.info("Tip: Try increasing the 'Lookback Period' slider to 365 days.")

else:
    # Landing Page State
    st.markdown(f"""
    <div style="text-align: center; padding: 50px;">
        <h2 style="color:{COLOR_PRIMARY}">Welcome to Bonterra Public Sector Intelligence</h2>
        <p>Select a State and Vertical from the sidebar to begin tracking funding flows.</p>
    </div>
    """, unsafe_allow_html=True)
