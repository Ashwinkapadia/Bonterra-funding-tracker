import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import datetime

# --- 1. BONTERRA BRAND CONFIGURATION ---
# Primary Colors based on Bonterra Brand
COLOR_PRIMARY = "#381360"  # Scarlet Gum
COLOR_SECONDARY = "#84EA9F"  # Pastel Green
COLOR_ACCENT = "#8A61B5"  # Wisteria
COLOR_TEXT = "#2C0020"

st.set_page_config(
    page_title="Bonterra | PubSec Funding Intelligence",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS to enforce Bonterra branding
st.markdown(f"""
    <style>
    .stApp {{
        background-color: #F5F5FF; /* Titan White */
    }}
    h1, h2, h3 {{
        color: {COLOR_PRIMARY} !important;
    }}
    div.stButton > button {{
        background-color: {COLOR_PRIMARY};
        color: white;
        border-radius: 8px;
        border: none;
    }}
    div.stButton > button:hover {{
        background-color: {COLOR_ACCENT};
        color: white;
    }}
    .metric-card {{
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. REFERENCE DATA (States & Verticals) ---
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

VERTICALS = {
    "Workforce Development": {
        "keywords": ["WIOA", "Workforce Innovation", "Apprenticeship", "Dislocated Worker", "Job Training"],
        "cfda": ["17.258", "17.259", "17.278"] # WIOA Clusters
    },
    "Violence Prevention (CVI)": {
        "keywords": ["Violence Intervention", "VOCA", "Victim Assistance", "Stop School Violence", "CVIPI", "Gun Violence"],
        "cfda": ["16.045", "16.575"] # CVIPI and VOCA
    },
    "Aging & Senior Services": {
        "keywords": ["Older Americans Act", "Area Agency on Aging", "Geriatric", "Nutrition Services", "ACL", "Adult Protective"],
        "cfda": ["93.044", "93.045"] # Title III
    },
    "Re-entry & Recidivism": {
        "keywords": ["Reentry", "Recidivism", "Second Chance Act", "Justice Reinvestment", "Corrections"],
        "cfda": ["16.812"]
    },
    "Veterans Services": {
        "keywords": ["Veterans Affairs", "Homeless Veterans", "HVRP", "State Veterans Home"],
        "cfda": []
    },
    "Home Visiting & Early Childhood": {
        "keywords": ["MIECHV", "Home Visiting", "Early Head Start", "Maternal Health"],
        "cfda": ["93.870"]
    },
    "School Districts (K-12)": {
        "keywords": ["School District", "ISD", "Board of Education", "Public Schools", "Elementary"],
        "cfda": ["84.010", "84.425"] # Title I, ESSER
    }
}

# --- 3. DATA ENGINE ---
@st.cache_data
def fetch_usaspending_data(state_code, vertical_data, days_back):
    url = "https://api.usaspending.gov/api/v2/search/spending_by_award/"
    start_date = (datetime.date.today() - datetime.timedelta(days=days_back)).strftime("%Y-%m-%d")
    end_date = datetime.date.today().strftime("%Y-%m-%d")
    
    # Combined keyword search
    search_terms = vertical_data["keywords"]
    
    payload = {
        "filters": {
            "time_period": [{"start_date": start_date, "end_date": end_date}],
            "place_of_performance_locations": [{"country": "USA", "state": state_code}],
            "award_type_codes": ["A", "B", "C", "D"], # Grants and Contracts
            "keyword_search": search_terms
        },
        "fields": [
            "Recipient Name", "Award Amount", "Description", "Action Date", 
            "Awarding Agency", "Awarding Sub Agency", "Funding Agency"
        ],
        "limit": 100,
        "page": 1
    }
    
    try:
        response = requests.post(url, json=payload)
        data = response.json()
        df = pd.DataFrame(data['results'])
        return df
    except Exception:
        return pd.DataFrame()

# --- 4. MAIN DASHBOARD UI ---

# Sidebar
st.sidebar.image("https://brandfetch.com/bonterratech.com/icon", width=60) # Using generic fetch or placeholder
st.sidebar.title("Bonterra Intelligence")
st.sidebar.markdown("---")
selected_state_name = st.sidebar.selectbox("Select Target State", options=list(US_STATES.values()))
# Reverse lookup state code
selected_state_code = [k for k, v in US_STATES.items() if v == selected_state_name][0]

selected_vertical = st.sidebar.selectbox("Target Vertical", options=list(VERTICALS.keys()))
days_lookback = st.sidebar.slider("Timeframe (Days)", 30, 365, 90)
st.sidebar.markdown("---")
st.sidebar.info("💡 **Data Source:** Live feed from USAspending.gov (Federal flow-down to States/Locals).")

# Header
col_logo, col_title = st.columns([1, 5])
with col_title:
    st.title(f"Funding Outlook: {selected_state_name}")
    st.markdown(f"Tracking **{selected_vertical}** investments flowing into {selected_state_name}.")

# Fetch Data
if st.sidebar.button("Analyze Funding", type="primary"):
    with st.spinner("Querying Federal Database..."):
        df = fetch_usaspending_data(selected_state_code, VERTICALS[selected_vertical], days_lookback)
        
        if not df.empty:
            # Data Processing
            df['Action Date'] = pd.to_datetime(df['Action Date'])
            df['Award Amount'] = pd.to_numeric(df['Award Amount'], errors='coerce')
            total_funding = df['Award Amount'].sum()
            avg_grant = df['Award Amount'].mean()
            
            # --- KPI METRICS ---
            st.markdown("### 📊 Executive Summary")
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Funding Identified", f"${total_funding:,.0f}")
            m2.metric("Number of Awards", len(df))
            m3.metric("Avg. Award Size", f"${avg_grant:,.0f}")
            
            st.markdown("---")
            
            # --- CHARTS ROW ---
            c1, c2 = st.columns(2)
            
            with c1:
                st.subheader("Top Funding Agencies")
                # Group by Awarding Agency
                agency_counts = df['Awarding Agency'].value_counts().head(5).reset_index()
                agency_counts.columns = ['Agency', 'Count']
                fig_agency = px.bar(
                    agency_counts, y='Agency', x='Count', orientation='h',
                    color_discrete_sequence=[COLOR_PRIMARY],
                    title="Who is giving the money?"
                )
                st.plotly_chart(fig_agency, use_container_width=True)
                
            with c2:
                st.subheader("Funding Timeline")
                # Group by Month
                df['Month'] = df['Action Date'].dt.to_period('M').astype(str)
                time_series = df.groupby('Month')['Award Amount'].sum().reset_index()
                fig_time = px.area(
                    time_series, x='Month', y='Award Amount',
                    color_discrete_sequence=[COLOR_SECONDARY],
                    title="Funding Trend (Last 90 Days)"
                )
                st.plotly_chart(fig_time, use_container_width=True)

            # --- DETAILED LEAD LIST ---
            st.subheader(f"📋 Lead List: {selected_vertical}")
            
            # Format for display
            display_df = df[['Recipient Name', 'Award Amount', 'Action Date', 'Description', 'Awarding Agency']]
            display_df = display_df.sort_values(by='Award Amount', ascending=False)
            
            st.dataframe(
                display_df.style.format({"Award Amount": "${:,.2f}"}),
                use_container_width=True,
                height=400
            )
            
            # CSV Download
            csv = display_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 Export Leads to CSV",
                csv,
                f"Bonterra_{selected_state_code}_{selected_vertical}_Leads.csv",
                "text/csv"
            )
            
        else:
            st.warning(f"No recent federal awards found for {selected_vertical} in {selected_state_name}. Try extending the date range.")

else:
    st.info("👈 Click 'Analyze Funding' in the sidebar to generate the report.")
