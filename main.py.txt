import streamlit as st
import requests
import pandas as pd
import datetime

# --- APP CONFIGURATION ---
st.set_page_config(page_title="Bonterra Funding Tracker", layout="wide")

st.title("🏛️ Public Sector Funding Tracker")
st.markdown("""
This tool fetches recent federal awards flowing to state agencies. 
Use this to identify agencies with fresh capital for **Workforce, Aging, and Violence Prevention** programs.
""")

# --- SIDEBAR FILTERS ---
st.sidebar.header("Filter Opportunities")

# 1. State Selection
state_mapping = {"CA": "California", "TX": "Texas", "NY": "New York", "IL": "Illinois", "FL": "Florida"}
selected_state_code = st.sidebar.selectbox("Select State", options=list(state_mapping.keys()))

# 2. Program Keywords (Mapping your verticals to search terms)
verticals = {
    "Workforce Development": ["WIOA", "Workforce", "Labor", "Apprenticeship"],
    "Violence Prevention (CVI)": ["Violence", "VOCA", "Victim", "Safety"],
    "Aging Services": ["Aging", "Elder", "Senior", "Geriatric"],
    "Re-entry & Recidivism": ["Reentry", "Recidivism", "Justice", "Corrections"],
    "Veterans": ["Veteran", "Homeless Veterans"]
}

selected_vertical = st.sidebar.selectbox("Target Vertical", options=list(verticals.keys()))
keywords = verticals[selected_vertical]

# 3. Timeframe
days_back = st.sidebar.slider("Look back (days)", 30, 365, 90)

# --- DATA FETCHING FUNCTION (USAspending API) ---
@st.cache_data
def fetch_awards(state_code, keywords, days):
    # USAspending API Endpoint for "Prime Awards"
    url = "https://api.usaspending.gov/api/v2/search/spending_by_award/"
    
    start_date = (datetime.date.today() - datetime.timedelta(days=days)).strftime("%Y-%m-%d")
    end_date = datetime.date.today().strftime("%Y-%m-%d")
    
    payload = {
        "filters": {
            "time_period": [{"start_date": start_date, "end_date": end_date}],
            "place_of_performance_locations": [{"country": "USA", "state": state_code}],
            "award_type_codes": ["A", "B", "C", "D"], # Grants and Contracts
            "keyword_search": keywords
        },
        "fields": [
            "Recipient Name", "Award Amount", "Description", "Action Date", "Awarding Agency"
        ],
        "limit": 50,
        "page": 1
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        return pd.DataFrame(data['results'])
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()

# --- MAIN EXECUTION ---
if st.sidebar.button("Find Funding"):
    with st.spinner(f"Searching federal data for {selected_vertical} in {state_mapping[selected_state_code]}..."):
        
        # Fetch Data
        df = fetch_awards(selected_state_code, keywords, days_back)
        
        if not df.empty:
            # Clean up columns
            df['Award Amount'] = df['Award Amount'].apply(lambda x: f"${x:,.2f}")
            
            # Metrics
            total_found = len(df)
            
            col1, col2 = st.columns(2)
            col1.metric("Opportunities Found", total_found)
            col1.write(f"**Keywords used:** {', '.join(keywords)}")
            
            # Display Data Table
            st.subheader(f"Recent {selected_vertical} Funding")
            st.dataframe(df, use_container_width=True)
            
            # CSV Download
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "Download Leads to CSV",
                csv,
                "bonterra_leads.csv",
                "text/csv",
                key='download-csv'
            )
        else:
            st.warning("No recent funding found matching these criteria. Try increasing the date range.")

else:
    st.info("👈 Select filters in the sidebar and click 'Find Funding'")