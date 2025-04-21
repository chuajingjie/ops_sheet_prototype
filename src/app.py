import streamlit as st
import pandas as pd
from datetime import datetime, date
import calendar
from pandas.tseries.offsets import MonthEnd, MonthBegin
import streamlit as st
import pandas as pd
import pydeck as pdk
import streamlit as st
import folium
from streamlit_folium import st_folium
from pathlib import Path

# Load the knowledge base
base_path = Path(__file__).parent
csv_path = base_path / "../data/sample/processed/knowledge_base.csv"
df = pd.read_csv(csv_path.resolve())
df["Date"] = pd.to_datetime(df["Date"], dayfirst=True)

min_date = df["Date"].min().replace(day=1).to_pydatetime()
max_date = (df["Date"].max() + MonthEnd(0)).to_pydatetime()

min_speed = float(df["Pedestrian Walking Speed"].min())
max_speed = float(df["Pedestrian Walking Speed"].max())

month_list = pd.date_range(
    start=df["Date"].min().replace(day=1),
    end=df["Date"].max().replace(day=1),
    freq="MS"  
).to_pydatetime().tolist()

# Part 1: Formatting options for the slider
hide_elements = """
        <style>
            div[data-testid="stSliderTickBarMin"],
            div[data-testid="stSliderTickBarMax"] {
                display: none;
            }
        </style>
"""
st.markdown(hide_elements, unsafe_allow_html=True)


def reset_filters():
    st.session_state["start_month"] = month_list[0]
    st.session_state["end_month"] = month_list[-1]
    st.session_state["Audio Tactile"] = "Any"
    st.session_state["GM+"] = "Any"
    st.session_state["Special Facility"] = "Any"
    st.session_state["Preemption"] = "Any"
    st.session_state["selected_phases"] = []
    st.session_state["walking_speed_range"] = (min_speed, max_speed)
    st.session_state["Right Turn Green Arrow"] = "Any"


if "start_month" not in st.session_state:
    reset_filters()

# Part 2: Create the sidebar with filter options
with st.sidebar:

    st.header("Filter Options")

    start_month, end_month = st.slider(
        "Date Range",
        min_value=month_list[0],
        max_value=month_list[-1],
        value=(st.session_state["start_month"], st.session_state["end_month"]),
        format="MMM YYYY",
    )

    # Save selected values back into session state
    st.session_state["start_month"] = start_month
    st.session_state["end_month"] = end_month

    # Other top-down filters
    audio_tactile = st.selectbox("Audio Tactile", options=["Any", "Yes", "No"], key="Audio Tactile")
    gmp = st.selectbox("GM+", options=["Any", "Yes", "No"], key="GM+")
    special_facility = st.selectbox("Special Facility", options=["Any", "Yes", "No"], key="Special Facility")
    preemption = st.selectbox("Preemption", options=["Any", "Yes", "No"], key="Preemption")
    right_turn_green_arrow = st.selectbox("Right Turn Green Arrow", options=["Any", "Yes", "No"], key="Right Turn Green Arrow")

    walking_speed_range = st.sidebar.slider(
        "Walking Speed Range (m/s)",
        min_value=min_speed,
        max_value=max_speed,
        value=st.session_state["walking_speed_range"],
        step=0.1,
        key="walking_speed_range"
    )
    # Flatten and deduplicate all components in the column
    phase_parts = sorted({
        part.strip()
        for seq in df["phase_sequence"].dropna()
        for part in seq.split(",")
    })

    selected_phases = st.sidebar.multiselect(
        "Phase Sequence (can select multiple)",
        options=phase_parts,
        key="selected_phases"
    )

    st.subheader("Controller Timesetting")
    
    red_yellow_range = st.slider(
        "RED/YELLOW",
        min_value=0.0,
        max_value=5.0,
        value=(0.0, 5.0),  
        step=0.1
    )

    red_yellow_range = st.slider(
        "LATE START",
        min_value=0.0,
        max_value=20.0,
        value=(0.0, 20.0),  
        step=0.1
    )

    minimum_green = st.slider(
        "MINIMUM GREEN",
        min_value=5.0,
        max_value=20.0,
        value=(5.0, 20.0), 
        step=0.1
    )

    increment = st.slider(
        "INCREMENT",
        min_value=0.0,
        max_value=5.0,
        value=(0.0, 5.0), 
        step=0.1
    )

    max_vig = st.slider(
        "MAX VIG",
        min_value=0.0,
        max_value=40.0,
        value=(0.0, 40.0), 
        step=0.1
    )

    max_ext_green = st.slider(
        "MAX EXT GREEN",
        min_value=0.0,
        max_value=150.0,
        value=(0.0, 150.0), 
        step=0.1
    )

    early_cut_off = st.slider(
        "Early Cut-Off",
        min_value=0.0,
        max_value=20.0,
        value=(0.0, 20.0), 
        step=0.1
    )

    amber = st.slider(
        "AMBER",
        min_value=3,
        max_value=7,
        value=(3, 7), 
        step=1
    )

    all_red = st.slider(
        "ALL RED",
        min_value=0,
        max_value=15,
        value=(0, 15), 
        step=1
    )

    special_all_red = st.slider(
        "SPECIAL ALL RED",
        min_value=0,
        max_value=15,
        value=(0, 15), 
        step=1
    )

    # Center the button using columns
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.button("Reset Filters", on_click=reset_filters)

# Part 2: Filter the dataframe based on selected options 
filtered_df = df.copy()

categorial_filter_options = {
    "Audio Tactile": audio_tactile,
    "GMP": gmp,
    "Special Facility": special_facility,
    "Preemption": preemption,
    "Right Turn Green Arrow": right_turn_green_arrow,
    }

for col, value in categorial_filter_options.items():
    if value != "Any":
        filtered_df = filtered_df[filtered_df[col] == value]

# Filter dataframe based on date range
filtered_df = filtered_df[
    (filtered_df["Date"] >= start_month) &
    (filtered_df["Date"] <= end_month + pd.offsets.MonthEnd(0))
]

if selected_phases:
    filtered_df = filtered_df[
        filtered_df["phase_sequence"].apply(
            lambda x: any(phase in x for phase in selected_phases)
        )
    ]
filtered_df = filtered_df[
    (filtered_df["Pedestrian Walking Speed"] >= walking_speed_range[0]) &
    (filtered_df["Pedestrian Walking Speed"] <= walking_speed_range[1])
]



def highlight_rows(val, lat_series, lon_series, col_name):
    return [
        'background-color: #FFEBEB' if lat == 0 and lon == 0 and col_name in ['Int. No', 'Location'] else ''
        for lat, lon in zip(lat_series, lon_series)
    ]

# Apply styling only to 'Int. No' and 'Location' columns
styled_df = filtered_df[['Int. No', 'Location']].style

for col in ['Int. No', 'Location']:
    styled_df = styled_df.apply(
        lambda col_values: highlight_rows(col_values, filtered_df['lat'], filtered_df['lon'], col),
        axis=0
    )

if filtered_df.empty:
    st.info("No Ops Sheets found based on given criteria")
else:
    st.dataframe(styled_df, use_container_width=True, hide_index=True)

    if ((filtered_df['lat'] == 0) & (filtered_df['lon'] == 0)).any():
        st.error("Highlighted Intersections have missing XY data")

    # Show the map
    # Part 1: Create a Folium map centered on Sg without default tiles
    m = folium.Map(
        location=[1.3278535311439326, 103.81599426269533],
        zoom_start=11,
        tiles=None
    )

    # Part 2: Add a background style to the map
    folium.TileLayer(
        tiles="https://tiles.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png",
        attr="&copy; <a href='https://carto.com/attributions'>CARTO</a>",
        name="CartoDB Light",
        control=False
    ).add_to(m)

    # Part 3: Add markers to the map using a Google-style pin icon
    for _, row in filtered_df.iterrows():
        
        lat = row["lat"]
        lon = row["lon"]
        int_no = row["Int. No"]
        location_name = row["Location"]

        popup_html = f"""
        <b>Int No:</b> {int_no}<br>
        <b>Location:</b> {location_name}<br>
        """

        # <a href="https://www.google.com/maps?q=&layer=c&cbll={lat},{lon}" target="_blank">
        #     🗺️ Street View
        # </a>

        popup = folium.Popup(popup_html, max_width=500)

        folium.Marker(
            location=[lat, lon],
            popup=popup,
            icon=folium.CustomIcon(
                icon_image="https://maps.gstatic.com/mapfiles/api-3/images/spotlight-poi2_hdpi.png",
                icon_size=(24, 36)
            )
        ).add_to(m)

    # Step 4: Display map in Streamlit
    map_data = st_folium(m, width=700, height=500)


