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
COLOR_PRIMARY = "#381360"   # Scarlet Gum (Bonterra Purple)
COLOR_SECONDARY = "#84EA9F" # Pastel Green
COLOR_ACCENT = "#6B3A91"    # Highlight Purple
COLOR_BG = "#F4F6F8"        # Enterprise Gray

# CSS: Clean, Professional, "Eye-Catchy"
st.markdown(f"""
    <style>
    /* Main Background */
    .stApp {{
        background-color: {COLOR_BG};
    }}
    
    /* Header Styling */
    h1, h2, h3 {{
        color: {COLOR_PRIMARY} !important;
        font-family: 'Segoe UI', Helvetica, sans-serif;
        font-weight: 700;
    }}
    
    /* Card Styling for Metrics */
    div[data-testid="stMetric"] {{
        background-color: #FFFFFF;
        border: 1px solid #E0E0E0;
        padding: 15px;
        border-radius: 8px;
        border-top: 5px solid {COLOR_SECONDARY};
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }}
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] {{
        background-color: #FFFFFF;
        border-right: 1px solid #E0E0E0;
    }}
    
    /* Primary Action Button */
    div.stButton > button {{
        background-color: {COLOR_PRIMARY};
        color: white;
        font-weight: bold;
        border: none;
        padding: 0.6rem 1.2rem;
        border-radius: 6px;
        width: 100%;
        transition: all 0.3s ease;
    }}
    div.stButton > button:hover {{
        background-color: {COLOR_ACCENT};
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }}
    
    /* DataFrame Header */
    thead tr th {{
        background-color: {COLOR_PRIMARY} !important;
        color: white !important;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. INTELLIGENCE ENGINE (Data Map) ---
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

# EXPANDED VERTICALS (To fix "No Data")
# Added broad "Catch-All" codes like Medicaid and Unemployment to ensure connectivity check.
VERTICALS = {
    "Workforce Development": {
        "cfda": ["17.258", "17.259", "17.278", "17.207", "17.225", "17.261", "17.277"],
        "keywords": ["WIOA", "Workforce", "Dislocated Worker", "Apprenticeship", "Employment Service"],
        "desc": "WIOA Clusters, Wagner-Peyser, Unemployment Admin"
    },
    "Violence Prevention (CVI)": {
        "cfda": ["16.575", "16.045", "16.738", "16.590", "16.540"],
        "keywords": ["VOCA", "Victim", "Violence", "Stop School Violence", "Justice Assistance"],
        "desc": "VOCA, CVIPI, Byrne JAG, Juvenile Justice"
    },
    "Aging & Senior Services": {
        "cfda": ["93.044", "93.045", "93.052", "93.041", "93.042", "93.778"], 
        "keywords": ["Aging", "Older Americans", "Geriatric", "Adult Protective", "Medicaid"],
        "desc": "OAA Title III, Title VII, and Medicaid Waivers"
    },
    "Re-entry & Recidivism": {
        "cfda": ["16.812", "16.838", "16.738", "16.585"],
        "keywords": ["Reentry", "Second Chance", "Recidivism", "Corrections", "Drug Court"],
        "desc": "Second Chance Act, COSSAP, Drug Courts"
    },
    "School Districts (K-12)": {
        "cfda": ["84.010", "84.425", "84.027", "84.287"],
        "keywords": ["School District", "ISD", "Elementary", "Board of Education", "Public Schools"],
        "desc": "Title I, ESSER (Covid Relief), IDEA (Special Ed)"
    }
}

# --- 3. ROBUST DATA FETCHING ---
@st.cache_data
def fetch_usaspending_data(state_code, vertical_config, days_back):
    url = "https://api.usaspending.gov/api/v2/search/spending_by_award/"
    
    start_date = (datetime.date.today() - datetime.timedelta(days=days_back)).strftime("%Y-%m-%d")
    end_date = datetime.date.today().strftime("%Y-%m-%d")
    
    # SEARCH FIELDS: We request the 'Generated ID' to build the link
    fields = [
        "Generated Unique Award ID", "Recipient Name", "Award Amount", 
        "Description", "Action Date", "Awarding Agency", "CFDA Number", "CFDA Title"
    ]
    
    # BASE FILTERS
    base_filters = {
        "time_period": [{"start_date": start_date, "end_date": end_date}],
        "award_type_codes": ["A", "B", "C", "D"], # Covers Contracts AND Grants
    }

    # --- STRATEGY 1: PRECISION SEARCH (Place of Performance + CFDA) ---
    # This is the "Correct" way. We look for money SPENT in the state for specific programs.
    # "Place of Performance" is better than "Recipient Location" for state flows.
    try:
        payload_1 = {
            "filters": base_filters.copy(),
            "fields": fields,
            "limit": 100
        }
        payload_1["filters"]["place_of_performance_locations"] = [{"country": "USA", "state": state_code}]
        payload_1["filters"]["program_numbers"] = vertical_config["cfda"]
        
        response = requests.post(url, json=payload_1)
        data = response.json()
        df = pd.DataFrame(data.get('results', []))
        
        # --- STRATEGY 2: FALLBACK (Keyword + Place of Performance) ---
        # If CFDA codes are missing/wrong in the database, we search for text (e.g. "Workforce").
        if df.empty:
            payload_2 = {
                "filters": base_filters.copy(),
                "fields": fields,
                "limit": 100
            }
            payload_2["filters"]["place_of_performance_locations"] = [{"country": "USA", "state": state_code}]
            payload_2["filters"]["keyword_search"] = vertical_config["keywords"]
            
            response_2 = requests.post(url, json=payload_2)
            data_2 = response_2.json()
            df = pd.DataFrame(data_2.get('results', []))

        return df
        
    except Exception as e:
        st.error(f"Connection Error: {e}")
        return pd.DataFrame()

# --- 4. DASHBOARD UI ---

# Sidebar with Bonterra Branding
with st.sidebar:
    # Dynamic Logo or Text Fallback
    try:
        st.image("https://logo.clearbit.com/bonterratech.com", width=60)
    except:
        st.markdown(f"<h1 style='color:{COLOR_PRIMARY}'>Bonterra</h1>", unsafe_allow_html=True)
        
    st.markdown("### PubSec Intelligence")
    st.caption("Lead Generation & Funding Tracker")
    st.markdown("---")
    
    # Controls
    st.subheader("⚙️ Filters")
    
    # State Selector - Defaulting to AR to test your case
    state_names = list(US_STATES.values())
    selected_state_name = st.selectbox("Target State", options=state_names, index=state_names.index("Arkansas"))
    selected_state_code = [k for k, v in US_STATES.items() if v == selected_state_name][0]

    selected_vertical = st.selectbox("Target Vertical", options=list(VERTICALS.keys()))
    
    # Help text
    st.info(f"Tracking: **{VERTICALS[selected_vertical]['desc']}**")
    
    # Lookback Slider
    days_lookback = st.slider("Lookback Period", 90, 730, 365, help="Set to 365+ days to catch annual block grants.")
    
    st.markdown("---")
    search_btn = st.button("🔍 Find Opportunities", type="primary")

# Main Content Area
if search_btn:
    with st.spinner(f"Searching federal database for {selected_vertical} in {selected_state_name}..."):
        df = fetch_usaspending_data(selected_state_code, VERTICALS[selected_vertical], days_lookback)
        
        if not df.empty:
            # --- DATA PREP ---
            df['Action Date'] = pd.to_datetime(df['Action Date'])
            # Create the direct link to USAspending.gov
            df['Link'] = "https://www.usaspending.gov/award/" + df['Generated Unique Award ID'].astype(str).apply(requests.utils.quote)
            
            # --- METRICS SECTION ---
            total_funding = df['Award Amount'].sum()
            avg_award = df['Award Amount'].mean()
            
            col_header, col_logo = st.columns([4, 1])
            with col_header:
                st.title(f"{selected_state_name} Funding Report")
                st.markdown(f"**Vertical:** {selected_vertical} | **Window:** Last {days_lookback} Days")
            
            # Metric Cards
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Funding Identified", f"${total_funding:,.0f}")
            m2.metric("Opportunity Count", len(df))
            m3.metric("Avg. Deal Size", f"${avg_award:,.0f}")
            
            st.markdown("---")
            
            # --- CHARTS ---
            c1, c2 = st.columns(2)
            
            with c1:
                st.markdown("### 🏛️ Top Agencies")
                # Aggregate by Agency
                df_agency = df.groupby("Awarding Agency")["Award Amount"].sum().reset_index().sort_values("Award Amount", ascending=True).tail(8)
                fig_agency = px.bar(df_agency, x="Award Amount", y="Awarding Agency", orientation='h', 
                                    color_discrete_sequence=[COLOR_PRIMARY])
                fig_agency.update_layout(xaxis_title="Obligated Amount", yaxis_title=None, template="plotly_white")
                st.plotly_chart(fig_agency, use_container_width=True)
            
            with c2:
                st.markdown("### 📅 Funding Timeline")
                # Aggregate by Month
                df['Month'] = df['Action Date'].dt.to_period('M').astype(str)
                df_time = df.groupby('Month')['Award Amount'].sum().reset_index()
                fig_time = px.area(df_time, x='Month', y='Award Amount', 
                                   color_discrete_sequence=[COLOR_SECONDARY])
                fig_time.update_layout(xaxis_title="Date", yaxis_title="Amount", template="plotly_white")
                st.plotly_chart(fig_time, use_container_width=True)
                
            # --- LEAD LIST TABLE ---
            st.subheader("📋 Qualified Leads")
            st.markdown("Click **'Open Record'** to view the full contract details.")
            
            # Configurable Column Display
            st.dataframe(
                df[["Action Date", "Recipient Name", "Award Amount", "Description", "Link"]].sort_values("Action Date", ascending=False),
                column_config={
                    "Link": st.column_config.LinkColumn(
                        "Action",
                        display_text="Open Record 🔗",
                        width="small"
                    ),
                    "Award Amount": st.column_config.NumberColumn(
                        "Value",
                        format="$%d"
                    ),
                    "Action Date": st.column_config.DateColumn(
                        "Date",
                        format="YYYY-MM-DD"
                    ),
                    "Description": st.column_config.TextColumn(
                        "Description",
                        width="large"
                    )
                },
                use_container_width=True,
                hide_index=True
            )
            
            # CSV Download
            csv_data = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 Download Leads to CSV",
                csv_data,
                f"Bonterra_Leads_{selected_state_code}_{selected_vertical}.csv",
                "text/csv",
                type="secondary"
            )
            
        else:
            # ERROR HANDLING (No Data)
            st.warning(f"No active funding flows found for {selected_vertical} in {selected_state_name}.")
            st.markdown("### 🕵️‍♂️ Diagnostics")
            st.markdown(f"""
            We checked **Place of Performance: {selected_state_code}** for the last **{days_lookback} days**.
            
            **Possible Reasons:**
            1. **Block Grant Timing:** The state might receive its annual WIOA/HHS deposit in a month outside your selected window.
            2. **Data Lag:** Federal reporting can lag by 30-60 days.
            
            **Recommended Next Step:**
            * Slide the **'Lookback Period'** to **730 Days** (2 Years).
            * Switch the Vertical to **'School Districts'** or **'Aging'** to verify connectivity.
            """)

else:
    # LANDING PAGE
    st.markdown(f"""
    <div style="text-align: center; padding: 60px; background-color: #FFFFFF; border-radius: 12px; border: 1px solid #E0E0E0;">
        <h2 style="color: {COLOR_PRIMARY}; margin-bottom: 10px;">Bonterra Public Sector Intelligence</h2>
        <p style="font-size: 18px; color: #666; max-width: 600px; margin: 0 auto;">
            Select a <b>State</b> and <b>Vertical</b> to scan live federal grant databases.
        </p>
    </div>
    """, unsafe_allow_html=True)
