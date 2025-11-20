import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import us

# --- CONFIGURATION ---
st.set_page_config(page_title="Bonterra | Territory Planner", page_icon="🗺️", layout="wide")
COLOR_PRIMARY = "#381360"
COLOR_SECONDARY = "#84EA9F"

st.markdown(f"""
    <style>
    .stApp {{ background-color: #F4F6F8; }}
    h1, h2, h3 {{ color: {COLOR_PRIMARY} !important; }}
    div[data-testid="stMetric"] {{ background-color: white; border-left: 5px solid {COLOR_SECONDARY}; padding: 15px; border-radius: 5px; }}
    </style>
    """, unsafe_allow_html=True)

# --- DATA SOURCE 1: CENSUS POPULATION ENGINE ---
@st.cache_data
def fetch_census_data():
    # We use the official US Census Bureau CSV for 2023 County Estimates
    # This avoids needing an API Key for now.
    url = "https://www2.census.gov/programs-surveys/popest/datasets/2020-2023/counties/totals/co-est2023-alldata.csv"
    try:
        df = pd.read_csv(url, encoding='latin-1')
        # Filter: SUMLEV 050 = County level
        df = df[df['SUMLEV'] == 50]
        
        # Select relevant columns: Region, State Name, County Name, 2023 Population
        df = df[['STNAME', 'CTYNAME', 'POPESTIMATE2023']]
        df.columns = ['State', 'County', 'Population']
        return df
    except Exception as e:
        st.error(f"Could not fetch Census Data: {e}")
        return pd.DataFrame()

# --- DATA SOURCE 2: EDUCATION ENTITIES (NCES) ---
# Since NCES API is complex, we simulate the directory generator based on County
def generate_education_targets(county_name, state_name):
    # Logic: Most counties have at least one major ISD/School District
    # In a real production app, we would hit the NCES CCD API here.
    return [
        f"{county_name} School District",
        f"{county_name} Office of Education"
    ]

# --- DATA SOURCE 3: COUNTY GOVT VERTICALS ---
def generate_county_targets(county_name):
    # These are standard verticals found in almost every US County
    return {
        "Law Enforcement": [f"{county_name} Sheriff's Office", f"{county_name} Jail/Corrections"],
        "Healthcare": [f"{county_name} Health Department", f"{county_name} Behavioral Health Svcs"],
        "Public Safety": [f"{county_name} Emergency Management (OEM)"],
        "Social Services": [f"{county_name} Dept of Human Services", f"{county_name} Child Welfare"],
        "Administration": [f"{county_name} County Clerk", f"{county_name} Board of Commissioners"],
        "Courts": [f"{county_name} District Attorney", f"{county_name} Juvenile Court"]
    }

# --- MAIN APP ---
with st.sidebar:
    st.image("https://logo.clearbit.com/bonterratech.com", width=60)
    st.title("Territory Planner")
    st.markdown("Generate a Master Sheet of targets by State.")
    
    # Select State
    state_list = [s.name for s in us.states.STATES]
    selected_state = st.selectbox("Select State", state_list, index=state_list.index("Arkansas"))
    
    st.markdown("---")
    st.caption("Sources: US Census Bureau (2023), NCES logic.")

# HEADER
st.title(f"📍 Master Sheet: {selected_state}")
st.markdown("Population data and Government Entity mapping for sales territory planning.")

# 1. LOAD DATA
with st.spinner("Fetching Census Data..."):
    census_df = fetch_census_data()
    
    # Filter for selected State
    state_df = census_df[census_df['State'] == selected_state].copy()
    
    if not state_df.empty:
        # Sort by Population (High to Low) - Best for Sales Prioritization
        state_df = state_df.sort_values("Population", ascending=False)
        
        # METRICS
        total_pop = state_df['Population'].sum()
        total_counties = len(state_df)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total State Population", f"{total_pop:,.0f}")
        c2.metric("Total Counties", total_counties)
        c3.metric("Avg. County Size", f"{int(total_pop/total_counties):,.0f}")
        
        # 2. GENERATE THE MASTER SHEET
        st.subheader("📋 Territory Generation")
        
        master_list = []
        
        # Iterate through every county to build the list
        for index, row in state_df.iterrows():
            county = row['County']
            pop = row['Population']
            
            # A. Generate Government Org Targets
            gov_targets = generate_county_targets(county)
            for vertical, orgs in gov_targets.items():
                for org in orgs:
                    master_list.append({
                        "County": county,
                        "Population": pop,
                        "Vertical": vertical,
                        "Organization Name": org,
                        "Type": "County Government",
                        "Priority": "High" if pop > 100000 else "Medium"
                    })
            
            # B. Generate Education Targets
            edu_targets = generate_education_targets(county, selected_state)
            for org in edu_targets:
                master_list.append({
                    "County": county,
                    "Population": pop,
                    "Vertical": "K-12 Education",
                    "Organization Name": org,
                    "Type": "School District / LEA",
                    "Priority": "High"
                })
                
        # Create Master DataFrame
        master_df = pd.DataFrame(master_list)
        
        # DISPLAY TABS
        tab1, tab2 = st.tabs(["📊 Population Map", "📥 Download Master Sheet"])
        
        with tab1:
            # Simple Bar Chart of Largest Counties
            fig = px.bar(state_df.head(15), x="Population", y="County", orientation='h', 
                         title=f"Top 15 Counties in {selected_state} by Population",
                         color_discrete_sequence=[COLOR_PRIMARY])
            fig.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig, use_container_width=True)
            
        with tab2:
            st.markdown("### Generated Prospecting List")
            st.markdown("This sheet expands every County into its constituent organizations (Sheriff, Health, Schools).")
            
            st.dataframe(
                master_df, 
                column_config={
                    "Population": st.column_config.NumberColumn("Local Pop.", format="%d"),
                },
                use_container_width=True
            )
            
            # DOWNLOAD BUTTON
            csv = master_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label=f"📥 Download {selected_state} Master Sheet.csv",
                data=csv,
                file_name=f"Bonterra_{selected_state}_MasterSheet.csv",
                mime='text/csv',
            )
            
    else:
        st.error("Could not load Census data. Please try again later.")
