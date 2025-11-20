import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import us

# --- 1. CONFIGURATION & BRANDING ---
st.set_page_config(page_title="Bonterra | Territory Master", page_icon="🇺🇸", layout="wide")
COLOR_PRIMARY = "#381360"   # Scarlet Gum
COLOR_SECONDARY = "#84EA9F" # Pastel Green
COLOR_BG = "#F4F6F8"

st.markdown(f"""
    <style>
    .stApp {{ background-color: {COLOR_BG}; }}
    h1, h2, h3 {{ color: {COLOR_PRIMARY} !important; font-family: 'Segoe UI', sans-serif; }}
    div[data-testid="stMetric"] {{
        background-color: white; border-left: 5px solid {COLOR_SECONDARY}; padding: 15px; border-radius: 8px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }}
    div.stButton > button {{
        background-color: {COLOR_PRIMARY}; color: white; border-radius: 6px; width: 100%; font-weight: 600;
    }}
    div.stButton > button:hover {{ background-color: #5D2E86; color: white; }}
    .stDataFrame {{ background-color: white; border-radius: 10px; padding: 10px; }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. REAL-DATA FETCHERS (HIFLD API) ---

@st.cache_data
def fetch_hospitals_hifld(state_abbr):
    # Source: HIFLD (Homeland Infrastructure Foundation-Level Data)
    # We explicitly fetch the 'WEBSITE' field to give you DIRECT links.
    url = "https://services1.arcgis.com/Hp6G80Pky0NbqED5/arcgis/rest/services/Hospitals/FeatureServer/0/query"
    params = {
        "where": f"STATE = '{state_abbr}' AND STATUS = 'OPEN'",
        "outFields": "NAME,CITY,TYPE,BEDS,WEBSITE", # Fetching Real Website
        "f": "json",
        "returnGeometry": "false"
    }
    try:
        data = requests.get(url, params=params).json()
        rows = []
        for f in data.get('features', []):
            attr = f['attributes']
            # Validate URL
            site = attr.get('WEBSITE', '')
            if site and 'http' not in site: site = 'http://' + site
            
            rows.append({
                "Name": attr['NAME'].title(),
                "Type": f"Healthcare - {attr['TYPE']}",
                "City": attr['CITY'].title(),
                "Vertical": "Healthcare",
                "Size": f"{attr['BEDS']} Beds" if attr['BEDS'] > 0 else "N/A",
                "Website": site,
                "Link Type": "Direct" if site else "Search"
            })
        return pd.DataFrame(rows)
    except:
        return pd.DataFrame()

@st.cache_data
def fetch_universities_hifld(state_abbr):
    # Source: HIFLD Colleges
    url = "https://services1.arcgis.com/Hp6G80Pky0NbqED5/arcgis/rest/services/Colleges_and_Universities/FeatureServer/0/query"
    params = {
        "where": f"STATE = '{state_abbr}'",
        "outFields": "NAME,CITY,WEBSITE,TOT_ENROLL", # Fetching Real Website + Enrollment
        "f": "json",
        "returnGeometry": "false"
    }
    try:
        data = requests.get(url, params=params).json()
        rows = []
        for f in data.get('features', []):
            attr = f['attributes']
            site = attr.get('WEBSITE', '')
            if site and 'http' not in site: site = 'http://' + site
            
            rows.append({
                "Name": attr['NAME'].title(),
                "Type": "Higher Ed",
                "City": attr['CITY'].title(),
                "Vertical": "Education",
                "Size": f"{attr['TOT_ENROLL']} Students" if attr['TOT_ENROLL'] > 0 else "N/A",
                "Website": site,
                "Link Type": "Direct" if site else "Search"
            })
        return pd.DataFrame(rows)
    except:
        return pd.DataFrame()

@st.cache_data
def fetch_military_hifld(state_name):
    # Source: HIFLD Military Bases
    # Military bases rarely publish a single 'WEBSITE' field in open data for OPSEC reasons.
    # We default to a "Smart Search Link" for these.
    url = "https://services1.arcgis.com/Hp6G80Pky0NbqED5/arcgis/rest/services/Military_Bases/FeatureServer/0/query"
    # Note: HIFLD stores state names in various formats, we try fuzzy matching via where clause if needed, 
    # but usually full name works for 'STATE_TERR'
    params = {
        "where": f"upper(STATE_TERR) = '{state_name.upper()}'",
        "outFields": "SITE_NAME,COMPONENT,OPER_STAT",
        "f": "json",
        "returnGeometry": "false"
    }
    try:
        data = requests.get(url, params=params).json()
        rows = []
        for f in data.get('features', []):
            attr = f['attributes']
            if attr['OPER_STAT'] == 'Active':
                name = attr['SITE_NAME'].title()
                rows.append({
                    "Name": name,
                    "Type": f"Defense - {attr['COMPONENT']}",
                    "City": "Federal Installation",
                    "Vertical": "Defense",
                    "Size": "Active Duty",
                    "Website": f"https://www.google.com/search?q={name.replace(' ', '+')}+Official+Site",
                    "Link Type": "Search (Security)"
                })
        return pd.DataFrame(rows)
    except:
        return pd.DataFrame()

# --- 3. LOCAL GOVT & SCHOOLS ENGINE ---
@st.cache_data
def fetch_census_counties(state_name):
    # We fetch the Census Pop data to prioritize the counties
    url = "https://www2.census.gov/programs-surveys/popest/datasets/2020-2023/counties/totals/co-est2023-alldata.csv"
    try:
        df = pd.read_csv(url, encoding='latin-1')
        # Filter for County Level (050) and State
        df = df[(df['SUMLEV'] == 50) & (df['STNAME'] == state_name)]
        return df[['CTYNAME', 'POPESTIMATE2023']]
    except:
        return pd.DataFrame()

def generate_smart_link(org_name, state):
    # This generates a guaranteed working Google Search link
    query = f"{org_name} {state} Official Website"
    return f"https://www.google.com/search?q={query.replace(' ', '+')}"

# --- 4. DASHBOARD UI ---
with st.sidebar:
    try:
        st.image("https://logo.clearbit.com/bonterratech.com", width=60)
    except:
        st.header("Bonterra")
    st.title("Territory Master")
    st.caption("Strategic Prospecting Tool")
    
    # State Selector
    state_names = [s.name for s in us.states.STATES]
    selected_state = st.selectbox("Select Region", state_names, index=state_names.index("Arkansas"))
    state_abbr = us.states.lookup(selected_state).abbr
    
    st.subheader("Select Verticals")
    show_local = st.checkbox("🏛️ Local Govt (Sheriff/Health)", value=True)
    show_edu = st.checkbox("🎓 Education (K-12 & Uni)", value=True)
    show_health = st.checkbox("🏥 Healthcare", value=True)
    show_mil = st.checkbox("🪖 Military", value=True)
    
    st.markdown("---")
    build_btn = st.button("🚀 Generate Master Sheet")

# MAIN AREA
st.title(f"Territory Plan: {selected_state}")

if build_btn:
    with st.spinner("Fetching real-time data from Federal & Census APIs..."):
        master_dfs = []
        
        # A. HEALTHCARE (Direct Links)
        if show_health:
            df_health = fetch_hospitals_hifld(state_abbr)
            if not df_health.empty:
                master_dfs.append(df_health)

        # B. HIGHER ED (Direct Links)
        if show_edu:
            df_uni = fetch_universities_hifld(state_abbr)
            if not df_uni.empty:
                master_dfs.append(df_uni)

        # C. MILITARY (Search Links)
        if show_mil:
            df_mil = fetch_military_hifld(selected_state)
            if not df_mil.empty:
                master_dfs.append(df_mil)
                
        # D. LOCAL GOVT & K-12 (Smart Links + Census Priority)
        if show_local or show_edu:
            census_df = fetch_census_counties(selected_state)
            local_rows = []
            
            for _, row in census_df.iterrows():
                county = row['CTYNAME']
                pop = row['POPESTIMATE2023']
                
                # Determine Priority based on Population
                priority_label = "🔥 High Priority" if pop > 100000 else "Standard"
                
                # 1. Sheriff / Law Enforcement
                if show_local:
                    org_name = f"{county} Sheriff's Office"
                    local_rows.append({
                        "Name": org_name,
                        "Type": "Law Enforcement",
                        "City": county,
                        "Vertical": "Local Govt",
                        "Size": f"Pop: {pop:,.0f}",
                        "Website": generate_smart_link(org_name, selected_state),
                        "Link Type": "Smart Search",
                        "Priority": priority_label
                    })
                    
                    org_name = f"{county} Health Department"
                    local_rows.append({
                        "Name": org_name,
                        "Type": "Public Health",
                        "City": county,
                        "Vertical": "Local Govt",
                        "Size": f"Pop: {pop:,.0f}",
                        "Website": generate_smart_link(org_name, selected_state),
                        "Link Type": "Smart Search",
                        "Priority": priority_label
                    })

                # 2. K-12 School Districts (Generated from County)
                if show_edu:
                    # Note: We create the 'Likely' major district for the county.
                    # Real NCES API integration requires huge mapping, this is the 'Vibecoding' strategic proxy.
                    org_name = f"{county} School District"
                    local_rows.append({
                        "Name": org_name,
                        "Type": "K-12 District",
                        "City": county,
                        "Vertical": "Education",
                        "Size": f"Pop: {pop:,.0f}",
                        "Website": generate_smart_link(org_name, selected_state),
                        "Link Type": "Smart Search",
                        "Priority": priority_label
                    })
            
            if local_rows:
                master_dfs.append(pd.DataFrame(local_rows))

        # MERGE AND DISPLAY
        if master_dfs:
            final_df = pd.concat(master_dfs, ignore_index=True)
            
            # Fill Priority for Non-Census Rows (Hospitals/Unis)
            # We assume Hospitals > 100 beds are High Priority
            def calc_priority(row):
                if pd.notnull(row.get('Priority')): return row['Priority']
                if 'Beds' in str(row['Size']):
                    try:
                        return "🔥 High Priority" if int(row['Size'].split()[0]) > 100 else "Standard"
                    except: return "Standard"
                if 'Students' in str(row['Size']):
                     try:
                        return "🔥 High Priority" if int(row['Size'].split()[0]) > 5000 else "Standard"
                     except: return "Standard"
                return "Standard"

            final_df['Priority'] = final_df.apply(calc_priority, axis=1)
            
            # Reorder Columns
            final_df = final_df[['Priority', 'Vertical', 'Name', 'Type', 'City', 'Size', 'Website', 'Link Type']]
            
            # SORT: High Priority First
            final_df = final_df.sort_values(by=['Priority', 'Vertical'], ascending=[True, True]) # '🔥' sorts before 'S'

            # --- METRICS ---
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Prospects", len(final_df))
            col2.metric("🔥 High Priority", len(final_df[final_df['Priority'].str.contains("High")]))
            col3.metric("Hospitals Found", len(final_df[final_df['Vertical']=="Healthcare"]))
            col4.metric("Schools/Unis", len(final_df[final_df['Vertical']=="Education"]))
            
            # --- VISUALS ---
            c1, c2 = st.columns([1, 2])
            with c1:
                fig_pie = px.pie(final_df, names='Vertical', title="Prospect Mix", color_discrete_sequence=px.colors.sequential.Viridis)
                st.plotly_chart(fig_pie, use_container_width=True)
            with c2:
                fig_bar = px.histogram(final_df, x='Vertical', color='Priority', barmode='group', title="High Priority Targets by Vertical", color_discrete_map={"🔥 High Priority": COLOR_PRIMARY, "Standard": COLOR_SECONDARY})
                st.plotly_chart(fig_bar, use_container_width=True)

            # --- THE MASTER SHEET ---
            st.subheader(f"📋 {selected_state} Master Prospecting List")
            st.caption("Use 'Direct' links for immediate access. Use 'Smart Search' links to find local government homepages.")
            
            st.dataframe(
                final_df,
                column_config={
                    "Website": st.column_config.LinkColumn("Official Link", display_text="Open Website 🔗"),
                    "Priority": st.column_config.TextColumn("Tier", width="small"),
                },
                use_container_width=True
            )
            
            # CSV DOWNLOAD
            csv = final_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 Download as CSV (for Salesforce/Hubspot)",
                csv,
                f"Bonterra_{selected_state}_TerritoryPlan.csv",
                "text/csv"
            )

        else:
            st.error("No data returned. Please select at least one vertical.")
else:
    st.info("👈 Select options in the sidebar to generate your territory plan.")
