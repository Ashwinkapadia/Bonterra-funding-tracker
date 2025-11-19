import streamlit as st
import requests
import pandas as pd
import datetime
import json

# --- CONFIGURATION ---
st.set_page_config(page_title="Bonterra Connectivity Test", layout="wide")

# --- DATA DICTIONARY ---
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

# --- API FUNCTION (SIMPLIFIED) ---
@st.cache_data
def fetch_debug_data(state_code, days_back, search_type):
    url = "https://api.usaspending.gov/api/v2/search/spending_by_award/"
    
    # Dates
    today = datetime.date.today()
    start_date = (today - datetime.timedelta(days=days_back)).strftime("%Y-%m-%d")
    end_date = today.strftime("%Y-%m-%d")
    
    # PAYLOAD: The "Safe" Version
    # We remove complex keyword logic to ensure connection first.
    payload = {
        "filters": {
            "time_period": [{"start_date": start_date, "end_date": end_date}],
            # We search for money SPENT in the state (Place of Performance)
            # This is safer than "Recipient Location" for Block Grants
            "place_of_performance_locations": [{"country": "USA", "state": state_code}],
            "award_type_codes": ["A", "B", "C", "D"] # Contracts and Grants
        },
        "fields": [
            "Generated Unique Award ID", 
            "Recipient Name", 
            "Award Amount", 
            "Description", 
            "Action Date", 
            "Awarding Agency",
            "Prime Award ID"
        ],
        "limit": 50,
        "sort": "Action Date",
        "order": "desc"
    }
    
    # TOGGLE: Prime vs Sub-Awards
    # Note: USAspending uses a 'subawards' boolean at the top level.
    if search_type == "Sub-Awards (Local Money)":
        payload["subawards"] = True
    else:
        payload["subawards"] = False

    try:
        # We use POST as required by this endpoint
        response = requests.post(url, json=payload)
        return response
    except Exception as e:
        return f"Error: {e}"

# --- DASHBOARD ---
st.title("🛠️ Bonterra Connection Diagnostic")

col1, col2, col3 = st.columns(3)
with col1:
    selected_state_name = st.selectbox("Target State", list(US_STATES.values()), index=3) # Arkansas
    selected_state_code = [k for k, v in US_STATES.items() if v == selected_state_name][0]

with col2:
    # CRITICAL: This toggle switches the API mode
    search_type = st.radio("Data Layer", ["Prime Awards (Federal -> State)", "Sub-Awards (Local Money)"])

with col3:
    days = st.slider("Lookback Days", 30, 730, 365)

if st.button("Run Diagnostic Scan"):
    with st.spinner("Pinging Federal Server..."):
        # 1. Get Raw Response
        response = fetch_debug_data(selected_state_code, days, search_type)
        
        if isinstance(response, str):
            st.error(response)
        else:
            # 2. Check Status Code
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                
                # 3. Success State
                if len(results) > 0:
                    st.success(f"✅ CONNECTION SUCCESSFUL! Found {len(results)} records.")
                    df = pd.DataFrame(results)
                    
                    # Display Data
                    st.dataframe(
                        df[["Action Date", "Recipient Name", "Award Amount", "Description"]],
                        use_container_width=True
                    )
                    
                    # Chart
                    try:
                        import plotly.express as px
                        st.subheader("Spending Breakdown")
                        fig = px.bar(df.head(10), x="Award Amount", y="Recipient Name", orientation='h')
                        st.plotly_chart(fig)
                    except:
                        pass
                        
                # 4. Empty State (The error you are seeing)
                else:
                    st.warning("⚠️ Server responded (200 OK), but returned 0 results.")
                    st.markdown(f"""
                    **Diagnostics:**
                    * **State:** {selected_state_name} ({selected_state_code})
                    * **Mode:** {search_type}
                    * **Date Range:** Last {days} days
                    
                    **Why is this happening?**
                    1.  **Sub-Awards are Sparse:** Reporting sub-awards is voluntary/laggy for many states. Try switching to **Prime Awards**.
                    2.  **Place of Performance:** We filtered by "Place of Performance". The money might be "Performed" in DC but "Recipient" is AR.
                    """)
                    
            else:
                st.error(f"❌ API Error: Status {response.status_code}")
                st.text(response.text)

            # --- DEBUGGER SECTION ---
            with st.expander("🕵️ RAW DATA DEBUGGER (Show this to Tech Team)"):
                st.markdown("### Sent Payload:")
                # Reconstruct payload to show user
                debug_payload = {
                    "filters": {
                        "time_period": [{"start_date": "...", "end_date": "..."}],
                        "place_of_performance_locations": [{"country": "USA", "state": selected_state_code}],
                        "award_type_codes": ["A", "B", "C", "D"]
                    },
                    "subawards": True if search_type == "Sub-Awards (Local Money)" else False
                }
                st.json(debug_payload)
                
                st.markdown("### Received Response:")
                st.json(response.json())
