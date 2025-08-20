import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import difflib

# -------------------------
# Page Config
# -------------------------
st.set_page_config(
    page_title="Malnutrition Dashboard",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# -------------------------
# Load Data
# -------------------------
@st.cache_data
def load_data():
    return pd.read_csv("Child_data.csv")

df = load_data()

st.title("Malnutrition Dashboard")
st.markdown(
    "This dashboard provides an overview of child malnutrition across India, "
    "with breakdowns by **State**, **District**, and key demographic and program indicators."
)

# -------------------------
# Filter relevant growth categories
# -------------------------
mal_types = ["Stunted", "Wasted", "Underweight"]
df = df[df["Growth_status"].isin(mal_types + ["Normal"])]

# -------------------------
# Download GeoJSONs
# -------------------------
geojson_url_state = "https://raw.githubusercontent.com/geohacker/india/master/state/india_telengana.geojson"
geojson_data_state = requests.get(geojson_url_state).json()
state_property_key = "NAME_1"
geojson_states = {f["properties"][state_property_key] for f in geojson_data_state["features"]}

# Fix CSV state names
csv_states = set(df["State"].unique())
mismatches = csv_states - geojson_states
manual_fix = {"Odisha": "Orissa"}
state_fix_map = {}
for state in mismatches:
    if state in manual_fix:
        state_fix_map[state] = manual_fix[state]
    else:
        match = difflib.get_close_matches(state, geojson_states, n=1, cutoff=0.6)
        if match:
            state_fix_map[state] = match[0]
if state_fix_map:
    df["State"] = df["State"].replace(state_fix_map)

# -------------------------
# Tabs
# -------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Prevalence Maps & Charts",
    "Demographics",
    "Nutrition Indicators",
    "Program Reach",
    "Mother–Child Linkages"
])

# -------------------------
# Tab 1: Prevalence Maps & Charts
# -------------------------
with tab1:
    level = st.selectbox("Aggregate by:", ["State", "District"])
    agg = df.groupby([level, "Growth_status"]).size().reset_index(name="count")
    total = df.groupby(level).size().reset_index(name="total")
    agg = agg.merge(total, on=level)
    agg["percentage"] = 100 * agg["count"] / agg["total"]

    mal_type = st.selectbox("Select growth status:", mal_types + ["Normal"])
    subset = agg[agg["Growth_status"] == mal_type].sort_values("percentage", ascending=False)

    st.subheader(f"{mal_type} Prevalence by {level}")
    fig_bar = px.bar(
        subset.head(15),
        x=level,
        y="percentage",
        text="percentage",
        title=f"Top {level}s with highest {mal_type} prevalence"
    )
    fig_bar.update_traces(texttemplate='%{text:.1f}%', textposition="outside")
    st.plotly_chart(fig_bar, use_container_width=True)

    # Choropleth
    threshold = 20
    if level == "State":
        subset["highlight"] = subset["percentage"].apply(lambda x: x if x >= threshold else 0)
        fig_map = px.choropleth(
            subset,
            geojson=geojson_data_state,
            featureidkey=f"properties.{state_property_key}",
            locations="State",
            color="highlight",
            color_continuous_scale="Reds",
            range_color=(0, subset["percentage"].max()),
            labels={"highlight": f"{mal_type} %"}
        )
        fig_map.update_geos(visible=True, showcountries=True, showsubunits=True, fitbounds="locations")
        fig_map.update_traces(marker_line_width=0.5, marker_line_color="black")
        st.plotly_chart(fig_map, use_container_width=True)

    elif level == "District":
        geojson_url_district = "https://raw.githubusercontent.com/india-in-data/india_maps/master/india_district_administered.geojson"
        geojson_data_district = requests.get(geojson_url_district).json()
        feature_key = "properties.NAME_2"
        subset["highlight"] = subset["percentage"].apply(lambda x: x if x >= threshold else 0)
        fig_map = px.choropleth(
            subset,
            geojson=geojson_data_district,
            featureidkey=feature_key,
            locations="District",
            color="highlight",
            color_continuous_scale="Reds",
            range_color=(0, subset["percentage"].max()),
            labels={"highlight": f"{mal_type} %"}
        )
        fig_map.update_geos(visible=True, showcountries=True, showsubunits=True, fitbounds="locations")
        fig_map.update_traces(marker_line_width=0.3, marker_line_color="black")
        st.plotly_chart(fig_map, use_container_width=True)

# -------------------------
# Tab 2: Demographics
# -------------------------
with tab2:
    st.subheader("Age Distribution")
    fig_age = px.histogram(df, x="Age_in_months", nbins=20, title="Age distribution of surveyed children")
    st.plotly_chart(fig_age, use_container_width=True)

    st.subheader("Sex Distribution")
    fig_sex = px.pie(df, names="Sex", title="Male vs Female Distribution")
    st.plotly_chart(fig_sex, use_container_width=True)

# -------------------------
# Tab 3: Nutrition Indicators
# -------------------------
with tab3:
    st.subheader("Average Height and Weight by Age")
    avg_hw = df.groupby("Age_in_months")[["Height_cm", "Weight_kg"]].mean().reset_index()
    fig_hw = px.line(avg_hw, x="Age_in_months", y=["Height_cm", "Weight_kg"])
    st.plotly_chart(fig_hw, use_container_width=True)

    st.subheader("MUAC Distribution")
    fig_muac = px.histogram(df, x="MUAC_cm", nbins=20, title="MUAC Distribution (malnutrition severity)")
    st.plotly_chart(fig_muac, use_container_width=True)

# -------------------------
# Tab 4: Program Reach
# -------------------------
with tab4:
    st.subheader("Immunization Coverage by State")
    immun = df.groupby(["State", "Immunization_status"]).size().reset_index(name="count")
    fig_immun = px.bar(immun, x="State", y="count", color="Immunization_status", barmode="stack")
    st.plotly_chart(fig_immun, use_container_width=True)

    st.subheader("Supplementary Nutrition Coverage")
    sup = df.groupby(["State", "Supplementary_nutrition_received"]).size().reset_index(name="count")
    fig_sup = px.bar(sup, x="State", y="count", color="Supplementary_nutrition_received", barmode="stack")
    st.plotly_chart(fig_sup, use_container_width=True)

# -------------------------
# Tab 5: Mother–Child Linkages
# -------------------------
with tab5:
    st.subheader("Mother BMI vs Child Growth Status")
    if "Mothers_weight_kg" in df.columns and "Mothers_height_cm" in df.columns:
        df["Mother_BMI"] = df["Mothers_weight_kg"] / ((df["Mothers_height_cm"]/100) ** 2)
        fig_bmi = px.scatter(df, x="Mother_BMI", y="Age_in_months", color="Growth_status",
                             title="Mother BMI vs Child Growth Status")
        st.plotly_chart(fig_bmi, use_container_width=True)

    if "Maternal_anemia_status" in df.columns:
        st.subheader("Maternal Anemia vs Child Growth Status")
        fig_anemia = px.box(df, x="Maternal_anemia_status", y="Age_in_months", color="Growth_status")
        st.plotly_chart(fig_anemia, use_container_width=True)

# -------------------------
# Download & Footer
# -------------------------
st.download_button(
    "Download Data",
    df.to_csv(index=False).encode("utf-8"),
    "malnutrition_data.csv",
    "text/csv"
)

st.markdown("---")
st.caption("Data source: Child Nutrition Survey. This dashboard is for policy and planning purposes only.")
