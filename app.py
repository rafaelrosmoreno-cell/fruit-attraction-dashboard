import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(
    page_title="Fruit Attraction 2026 | Nuveen Natural Capital",
    page_icon="🌱",
    layout="wide"
)

# ---------- STYLE ----------
st.markdown("""
<style>
.block-container {
    padding-top: 2rem;
    padding-bottom: 3rem;
}
.title {
    font-size: 40px;
    font-weight: 700;
}
.subtitle {
    color: #666;
    font-size: 16px;
    margin-bottom: 25px;
}
.company-card {
    border: 1px solid #e6e6e6;
    border-radius: 14px;
    padding: 18px;
    margin-bottom: 12px;
    background-color: white;
}
.high {
    border-left: 7px solid #d33;
}
.medium {
    border-left: 7px solid #e7a61a;
}
.company-name {
    font-size: 21px;
    font-weight: 700;
}
.small-label {
    color: #777;
    font-size: 13px;
}
</style>
""", unsafe_allow_html=True)

# ---------- HEADER ----------
st.markdown(
    '<div class="title">🌱 Fruit Attraction 2026</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">Nuveen Natural Capital · IFEMA Madrid · 6–8 October 2026</div>',
    unsafe_allow_html=True
)

# ---------- LOAD DATA ----------
df = pd.read_csv("targets.csv").fillna("")

# ---------- KPIs ----------
c1, c2, c3, c4 = st.columns(4)

c1.metric("Target companies", len(df))
c2.metric("High priority", len(df[df["priority"] == "High"]))
c3.metric("Confirmed stands", len(df[df["confirmed_stand"] != ""]))
c4.metric("Event dates", "6–8 Oct")

st.divider()

# ---------- FILTERS ----------
col1, col2, col3 = st.columns(3)

search = col1.text_input(
    "Search company",
    placeholder="Hortifrut, Alcoaxarquia..."
)

priority_filter = col2.multiselect(
    "Priority",
    ["High", "Medium", "Low"],
    default=["High", "Medium"]
)

sector_options = sorted(df["sector"].dropna().unique())

sector_filter = col3.multiselect(
    "Sector",
    sector_options,
    default=sector_options
)

filtered = df[
    df["priority"].isin(priority_filter)
    & df["sector"].isin(sector_filter)
]

if search:
    filtered = filtered[
        filtered["company"].str.contains(
            search,
            case=False,
            na=False
        )
    ]

# ---------- TABS ----------
tab1, tab2, tab3, tab4 = st.tabs(
    [
        "⭐ Priority",
        "📍 By Hall",
        "🏢 All Companies",
        "📅 Events"
    ]
)

# ---------- PRIORITY ----------
with tab1:

    order = {"High": 0, "Medium": 1, "Low": 2}

    filtered = filtered.copy()

    filtered["_sort"] = filtered["priority"].map(order)

    filtered = filtered.sort_values("_sort")

    for _, row in filtered.iterrows():

        priority_class = (
            "high"
            if row["priority"] == "High"
            else "medium"
        )

        hall = (
            f"Hall {row['confirmed_hall']}"
            if row["confirmed_hall"]
            else "Hall TBC"
        )

        stand = (
            f"Stand {row['confirmed_stand']}"
            if row["confirmed_stand"]
            else "Stand TBC"
        )

        event = (
            f"<br><br>📅 {row['event_info']}"
            if row["event_info"]
            else ""
        )

        st.markdown(
            f"""
            <div class="company-card {priority_class}">
                <div class="company-name">
                    {row['company']}
                </div>

                <div class="small-label">
                    {row['type']} · {row['sector']}
                </div>

                <br>

                <b>📍 {hall} · {stand}</b>

                <br><br>

                {row['why_interesting']}

                {event}

            </div>
            """,
            unsafe_allow_html=True
        )

# ---------- BY HALL ----------
with tab2:

    located = df[
        df["confirmed_hall"] != ""
    ].copy()

    if located.empty:

        st.info(
            "Stand locations will appear here as they are confirmed."
        )

    else:

        for hall in sorted(located["confirmed_hall"].unique()):

            st.subheader(f"Hall {hall}")

            hall_data = located[
                located["confirmed_hall"] == hall
            ]

            for _, row in hall_data.iterrows():

                st.markdown(
                    f"**{row['company']}** — "
                    f"{row['confirmed_stand']} · "
                    f"{row['sector']}"
                )

            st.divider()

# ---------- ALL COMPANIES ----------
with tab3:

    st.dataframe(
        df[
            [
                "company",
                "priority",
                "type",
                "sector",
                "confirmed_hall",
                "confirmed_stand",
                "why_interesting"
            ]
        ],
        use_container_width=True,
        hide_index=True
    )

# ---------- EVENTS ----------
with tab4:

    events = df[
        df["event_info"] != ""
    ]

    if events.empty:

        st.info("No relevant events identified yet.")

    else:

        for _, row in events.iterrows():

            st.markdown(
                f"""
                ### {row['company']}
                {row['event_info']}
                """
            )

st.divider()

st.caption(
    f"Nuveen Natural Capital · "
    f"Updated {datetime.now().strftime('%d %b %Y %H:%M')}"
)
