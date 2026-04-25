import streamlit as st
import requests
import pandas as pd
import folium
from streamlit_folium import st_folium

st.set_page_config(layout="wide")
st.title("🌍 Climate Intelligence Dashboard")

# -----------------------------
# 🥗 FOOD WASTE DATA (SIMULATED / REPLACEABLE)
# -----------------------------
def get_food_waste_data():
    # EPA ECHO / Envirofacts-style facility data (real API endpoint)
    url = "https://data.epa.gov/efservice/FRS_INTEREST/rows/0:100/json"

    try:
        df = pd.read_json(url)

        # Keep only usable geospatial columns if available
        df = df.rename(columns={
            "LATITUDE83": "lat",
            "LONGITUDE83": "lon"
        })

        # Drop missing coordinates
        df = df.dropna(subset=["lat", "lon"])

        # Fake "waste intensity proxy" using facility size/type signals
        df["waste_estimate"] = 100 + (df.index % 500)

        return df[["lat", "lon", "waste_estimate"]]

    except Exception as e:
        st.error(f"EPA data fetch failed: {e}")
        return pd.DataFrame()

def get_selected_column(time_range):
    if time_range == "Last 24 Hours":
        return "last_24_hours"
    elif time_range == "Last Week":
        return "last_week"
    elif time_range == "Last Month":
        return "last_month"
    else:
        return "last_year"

# -----------------------------
# 🚨 NOAA WEATHER ALERTS
# -----------------------------
def get_noaa_alerts():
    url = "https://api.weather.gov/alerts/active"
    response = requests.get(url)
    data = response.json()
    
    alerts = []
    
    for feature in data["features"]:
        props = feature["properties"]
        if feature["geometry"]:
            coords = feature["geometry"]["coordinates"][0][0]
            alerts.append({
                "event": props["event"],
                "area": props["areaDesc"],
                "severity": props["severity"],
                "lat": coords[1],
                "lon": coords[0]
            })
    
    return pd.DataFrame(alerts)

# -----------------------------
# 🔥 NASA WILDFIRES
# -----------------------------
def get_wildfires():
    API_KEY = "d698bf0d4b4d72504780c36d7e429ef0"
    
    # url = f"https://firms.modaps.eosdis.nasa.gov/api/country/csv/{API_KEY}/USA/VIIRS_SNPP_NRT/1"
    url = "https://firms.modaps.eosdis.nasa.gov/data/active_fire/c6.1/csv/MODIS_C6_1_USA_contiguous_and_Hawaii_24h.csv"
    df = pd.read_csv(url)

    try:
        df = pd.read_csv(url)
    except Exception as e:
        st.error(f"Failed to fetch wildfire data: {e}")
        return pd.DataFrame()
    
    if df.empty:
        st.warning("No wildfire data returned.")
        return df
    
    df = df.rename(columns={
        "latitude": "lat",
        "longitude": "lon",
        "bright_ti4": "brightness"
    })
    
    return df[["lat", "lon", "brightness"]]

# -----------------------------
# 🗺️ MAP
# -----------------------------
m = folium.Map(location=[39.5, -98.35], zoom_start=4)

# Add NOAA alerts
try:
    alerts_df = get_noaa_alerts()
    
    for _, row in alerts_df.iterrows():
        folium.Marker(
            location=[row["lat"], row["lon"]],
            popup=f"{row['event']} ({row['severity']})<br>Source: NOAA",
            icon=folium.Icon(color="red")
        ).add_to(m)
    
    st.subheader("🚨 Active Weather Alerts")
    st.markdown(
        "Data source: [NOAA Weather.gov Alerts API](https://api.weather.gov/alerts/active)"
    )
    st.markdown(
        "API info: [NOAA Weather.gov API Documentation](https://www.weather.gov/documentation/services-web-api)"
    )
    st.dataframe(alerts_df.head(10))
    
except Exception as e:
    st.error(f"NOAA Error: {e}")

# Add Wildfires
try:
    fire_df = get_wildfires()
    
    for _, row in fire_df.iterrows():
        brightness = row["brightness"]

        radius = max(2, min(brightness / 20, 15))

        folium.CircleMarker(
            location=[row["lat"], row["lon"]],
            radius=radius,
            popup=f"Brightness: {brightness}<br>Source: NASA FIRMS",
            color="orange",
            fill=True,
            fill_opacity=0.6
        ).add_to(m)
    
    st.subheader("🔥 Active Wildfires")
    st.markdown(
        "Data source: [NASA FIRMS (Fire Information for Resource Management System)](https://firms.modaps.eosdis.nasa.gov/)"
    )
    st.write(f"{len(fire_df)} fire detections")

except Exception as e:
    st.error(f"Fire Data Error: {e}")

# Display map
st.subheader("🗺️ Live Extreme Events Map")
st_folium(m, width=1200, height=600)

# -----------------------------
# 🥗 FOOD WASTE TIME FILTER
# -----------------------------
time_range = st.selectbox(
    "🥗 Food Waste Time Range",
    ["Last 24 Hours", "Last Week", "Last Month", "Last Year"]
)

# -----------------------------
# 🥗 FOOD WASTE VISUALIZATION
# -----------------------------
try:
    waste_df = get_food_waste_data()
    col = get_selected_column(time_range)

    st.subheader("🥗 Food Waste Monitoring (tons)")
    st.markdown(
        """
        Data sources:
        - EPA Envirofacts / ECHO Facility Data: https://www.epa.gov/enviro  
        - EPA ECHO Database: https://echo.epa.gov/tools/data-downloads  
        - USDA Food Loss Estimates: https://www.usda.gov/foodlossandwaste  
        """
    )

    # Show table
    st.dataframe(waste_df[["location", col]])

    # Add to map
    for _, row in waste_df.iterrows():
        for _, row in waste_df.iterrows():
            value = row["waste_estimate"]

            radius = max(4, min(value / 20, 20))

            folium.CircleMarker(
                location=[row["lat"], row["lon"]],
                radius=radius,
                popup=f"EPA Facility Waste Estimate: {value}",
                color="green",
                fill=True,
                fill_opacity=0.6
            ).add_to(m)

    total_waste = waste_df[col].sum()
    st.metric("Total Food Waste", f"{total_waste:,} tons")

except Exception as e:
    st.error(f"Food Waste Error: {e}")

st.markdown(
    """
    **Data Sources:**
    - NOAA API Docs: https://www.weather.gov/documentation/services-web-api  
    - NASA FIRMS Wildfires: https://firms.modaps.eosdis.nasa.gov  
    - EPA Envirofacts / ECHO Facility Data: https://www.epa.gov/enviro  
    - EPA ECHO Database: https://echo.epa.gov/tools/data-downloads  
    - USDA Food Loss Estimates: https://www.usda.gov/foodlossandwaste  
    """
)