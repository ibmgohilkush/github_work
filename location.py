import streamlit as st
import requests
import pandas as pd
import pydeck as pdk

# You need to install this package first:
# pip install streamlit-geolocation
from streamlit_geolocation import streamlit_geolocation

st.set_page_config(page_title="Nearby Repair Shops", layout="wide")
st.title("🔧 Car Repair Shops Near Me (OpenStreetMap — No API Key)")

#using geoloation from streamlit_geolocation package to get the user's location
location = streamlit_geolocation()

if location and location['latitude'] and location['longitude']:
    lat, lon = location['latitude'], location['longitude']
    st.success(f"📍 Your location: {lat:.5f}, {lon:.5f}")

    radius = st.slider("Search radius (meters)", 500, 5000, 2000, 100)

    #find car repair shops, query can be changed
    query = f"""
    [out:json];
    (
      node["shop"="car_repair"](around:{radius},{lat},{lon});
      way["shop"="car_repair"](around:{radius},{lat},{lon});
      relation["shop"="car_repair"](around:{radius},{lat},{lon});
    );
    out center;
    """

    #overpass endpoint
    url = "https://overpass-api.de/api/interpreter"
    resp = requests.post(url, data={"data": query})
    data = resp.json()

    repair_shops = []
    for el in data.get("elements", []):
        tags = el.get("tags", {})
        name = tags.get("name", "Unnamed")
        loc = el.get("center", el)
        repair_shops.append({
            "name": name,
            "lat": loc["lat"],
            "lon": loc["lon"],
        })


    #displayiing them on a map, while displaying he number 
    if repair_shops:
        df = pd.DataFrame(repair_shops)
        st.subheader(f"Found {len(df)} car repair shop(s)")
        st.dataframe(df)

        st.pydeck_chart(pdk.Deck(
            initial_view_state=pdk.ViewState(latitude=lat, longitude=lon, zoom=13),
            layers=[
                pdk.Layer(
                    "ScatterplotLayer",
                    data=df,
                    get_position='[lon, lat]',
                    get_fill_color='[255, 0, 0, 200]',
                    get_radius=120,
                )
            ]
        ))
    else:
        st.warning("No car repair shops found nearby. Try increasing the search radius.")
else:
    st.info("Click the 'Get Location' button above to allow the app to find nearby car repair shops.")

