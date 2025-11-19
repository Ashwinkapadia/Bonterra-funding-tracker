import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import datetime

# --- 1. CONFIGURATION & BRANDING ---
st.set_page_config(page_title="Bonterra | Data Lake", page_icon="🌊", layout="wide")

# Bonterra Colors
COLOR_PRIMARY = "#381360"   # Scarlet Gum
COLOR_SECONDARY = "#84EA9F" # Pastel Green
COLOR_BG = "#F4F6F8"

st.markdown(f"""
    <style>
    .stApp {{ background-color: {COLOR_BG}; }}
    h1, h2, h3 {{ color: {COLOR_PRIMARY}; }}
    .stDataFrame {{ background-color: white; border-radius: 10px; padding: 10px; }}
    div.stButton > button {{ 
        background-color: {COLOR_PRIMARY}; color: white; border: none; padding: 10px 20px; border-radius: 5px;
    }}
    div.stButton > button:hover {{ background-color: #5D2E86; color: white; }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. REFERENCE DATA ---
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

# KEYWORDS FOR BACKEND FILTERING (Not sent to API)
VERTICAL_KEYWORDS = {
    "Workforce Development": ["workforce", "wioa", "labor", "employment", "job training", "apprentice", "dislocated"],
    "School Districts (K-12)": ["school", "education", "elementary", "isd", "title i", "esser", "idea", "instruction"],
    "Violence Prevention": ["violence", "victim", "voca", "abuse", "safety", "justice", "crime"],
    "Aging Services": ["aging", "elder", "senior", "nutrition", "adult protective", "home delivered"],
    "Veterans": ["veteran", "homeless vet", "hv rp"],
    "Housing": ["housing", "homeless", "tenant", "rent", "cdbg"]
}

# --- 3. THE "WIDE NET" API FUNCTION ---
@st.cache_data
def fetch_all_state_data(state_code, days_back, data_type="Prime Awards"):
    # Calculate dates
    start_date = (datetime.date.today() - datetime.timedelta(days=days_back)).strftime("%Y-%m-%d")
    end_date = datetime.date.today().strftime("%Y-%m-%d")
    
    # We fetch active awards in the state. We DO NOT filter by keyword here.
    # We get the "Firehose" of data.
    
    if data_type == "Prime Awards":
        url = "https://api.usaspending.gov/api/v2/search/spending_by_award/"
        payload = {
            "filters": {
                "time_period": [{"start_date": start_date, "end_date": end_date}],
                "place_of_performance_locations": [{"country": "USA", "state": state_code}],
                "award_type_codes": ["A", "B", "C", "D"] # Grants & Contracts
            },
            "fields": ["Generated Unique Award ID", "Recipient Name", "Award Amount", "Description", "Action Date", "Awarding Agency"],
            "limit": 100, # Fetch top 100 most recent
            "sort": "Action Date",
            "order": "desc"
        }
    else: 
        # SUB-AWARDS (This is a different, messier endpoint, but we'll try basic search)
        # Note: USAspending doesn't have a clean "Search all subawards by state" endpoint 
        # that mirrors the Prime one perfectly without filters. 
        # We will use the Prime endpoint but look for 'subawards' flag if available, 
        # OR revert to Prime but emphasize Recipient Location.
        # *Fallback*: For stability, we stick to Prime but increase the limit to catch more.
        st.warning("⚠️ Note: The public API restricts bulk Sub-Award downloading without specific filters. Showing Prime Awards that flow to this state.")
        url = "https://api.usaspending.gov/api/v2/search/spending_by_award/"
        payload = {
            "filters": {
                "time_period": [{"start_date": start_date, "end_date": end_date}],
                "recipient_locations": [{"country": "USA", "state": state_code}],
                "award_type_codes": ["A", "B", "C", "D"]
            },
            "fields": ["Generated Unique Award ID", "Recipient Name", "Award Amount", "Description", "Action Date", "Awarding Agency"],
            "limit": 100
        }

    try:
        response = requests.post(url, json=payload)
        data = response.json()
        return pd.DataFrame(data.get('results', []))
    except Exception as e:
        st.error(f"API Error: {e}")
        return pd.DataFrame()

# --- 4. APP LAYOUT ---
with st.sidebar:
    try:
        st.image("https://logo.clearbit.com/bonterratech.com", width=50)
    except:
        st.header("Bonterra")
        
    st.title("Data Lake Explorer")
    
    # 1. Select State
    selected_state_name = st.selectbox("State", list(US_STATES.values()), index=3) # Default AR
    selected_state_code = [k for k, v in US_STATES.items() if v == selected_state_name][0]
    
    # 2. Select Data Scope
    # data_scope = st.radio("Data Level", ["Prime Awards", "Sub-Awards (Experimental)"])
    # *Simplified for V6 stability*:
    st.info("Fetching all recent Prime Awards flowing into the state.")
    
    # 3. Select Backend Filters
    st.subheader("Backend Filters")
    st.caption("Filter the data AFTER downloading it.")
    selected_vertical = st.selectbox("Highlight Vertical", ["Show All"] + list(VERTICAL_KEYWORDS.keys()))
    
    days = st.slider("Lookback Days", 30, 730, 365)
    
    load_btn = st.button("🔄 Fetch Data Lake")

# MAIN PAGE
if load_btn:
    with st.spinner(f"Downloading raw grant data for {selected_state_name}..."):
        # 1. FETCH EVERYTHING
        df = fetch_all_state_data(selected_state_code, days, "Prime Awards")
        
        if not df.empty:
            # 2. BACKEND PROCESSING
            df['Action Date'] = pd.to_datetime(df['Action Date'])
            df['Link'] = "https://www.usaspending.gov/award/" + df['Generated Unique Award ID'].astype(str).apply(requests.utils.quote)
            
            # 3. FILTERING LOGIC
            if selected_vertical != "Show All":
                # Get keywords for the selected vertical
                keywords = VERTICAL_KEYWORDS[selected_vertical]
                # Create a regex pattern (e.g., "school|education|elementary")
                pattern = '|'.join(keywords)
                
                # Filter the DataFrame based on Description OR Agency Name (Case insensitive)
                filtered_df = df[
                    df['Description'].astype(str).str.contains(pattern, case=False, na=False) | 
                    df['Awarding Agency'].astype(str).str.contains(pattern, case=False, na=False)
                ]
                
                st.success(f"Filtered down to {len(filtered_df)} records related to **{selected_vertical}** out of {len(df)} total records found.")
                display_df = filtered_df
            else:
                st.success(f"Showing all {len(df)} records found.")
                display_df = df

            # 4. DISPLAY
            if not display_df.empty:
                # Metrics
                col1, col2 = st.columns(2)
                col1.metric("Total Volume", f"${display_df['Award Amount'].sum():,.0f}")
                col2.metric("Count", len(display_df))
                
                # Charts
                c1, c2 = st.columns(2)
                with c1:
                    # Who is getting money?
                    recip_fig = px.bar(display_df.head(10), y='Recipient Name', x='Award Amount', orientation='h', title="Top Recipients", color_discrete_sequence=[COLOR_PRIMARY])
                    st.plotly_chart(recip_fig, use_container_width=True)
                with c2:
                    # Timeline
                    display_df['Month'] = display_df['Action Date'].dt.to_period('M').astype(str)
                    time_agg = display_df.groupby('Month')['Award Amount'].sum().reset_index()
                    time_fig = px.area(time_agg, x='Month', y='Award Amount', title="Funding Flow", color_discrete_sequence=[COLOR_SECONDARY])
                    st.plotly_chart(time_fig, use_container_width=True)

                # Table
                st.subheader("Details")
                st.dataframe(
                    display_df[["Action Date", "Recipient Name", "Award Amount", "Description", "Link"]],
                    column_config={
                        "Link": st.column_config.LinkColumn("Link", display_text="Open 🔗"),
                        "Award Amount": st.column_config.NumberColumn("Amount", format="$%.2f")
                    },
                    use_container_width=True, 
                    hide_index=True
                )
            else:
                st.warning(f"We found {len(df)} total grants for {selected_state_name}, but none matched your keywords for {selected_vertical}.")
                st.markdown("**Recommendation:** Switch the dropdown back to 'Show All' to see what raw data is available.")
                
        else:
            st.error("No data returned from API. This usually means the date range is too short or the State Code is mismatching.")

else:
    # Landing Page
    st.markdown(f"""
    <div style='text-align:center; padding: 50px;'>
        <h1 style='color:{COLOR_PRIMARY}'>Bonterra | Wide Net Search</h1>
        <p>This tool fetches <b>ALL</b> recent funding for a state, then lets you filter it locally.</p>
        <p>👈 Select a State and click 'Fetch Data Lake' to begin.</p>
    </div>
    """, unsafe_allow_html=True)
