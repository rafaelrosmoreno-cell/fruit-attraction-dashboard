import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(
    page_title="Fruit Attraction 2026 | Nuveen Natural Capital",
    page_icon="🌱",
    layout="wide"
)

# ---------------- STYLE ----------------

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
    padding: 20px;
    margin-bottom: 14px;
    background-color: white;
}

.high {
    border-left: 7px solid #e53935;
}

.medium {
    border-left: 7px solid #f0a500;
}

.low {
    border-left: 7px solid #999999;
}

.company-name {
    font-size: 22px;
    font-weight: 700;
    margin-bottom: 4px;
}

.small-label {
    color: #777777;
    font-size: 14px;
}

.location {
    font-size: 16px;
    font-weight: 600;
    margin-top: 14px;
}

.reason {
    margin-top: 12px;
    font-size: 15px;
}

.event {
    margin-top: 12px;
    font-size: 14px;
    color: #555;
}

</style>
""", unsafe_allow_html=True)


# ---------------- HEADER ----------------

st.markdown(
    '<div class="title">🌱 Fruit Attraction 2026</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">Nuveen Natural Capital · IFEMA Madrid · 6–8 October 2026</div>',
    unsafe_allow_html=True
)


# ---------------- DATA ----------------

df = pd.read_csv(
    "targets.csv",
    dtype=str
).fillna("")


# ---------------- KPIs ----------------

c1, c2, c3, c4 = st.columns(4)

c1.metric("Target companies", len(df))

c2.metric(
    "High priority",
    len(df[df["priority"] == "High"])
)

c3.metric(
    "Confirmed stands",
    len(df[df["confirmed_stand"] != ""])
)

c4.metric(
    "Event dates",
    "6–8 Oct"
)

st.divider()


# ---------------- FILTERS ----------------

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

sector_options = sorted(
    [x for x in df["sector"].unique() if x]
)

sector_filter = col3.multiselect(
    "Sector",
    sector_options,
    default=sector_options
)

filtered = df[
    df["priority"].isin(priority_filter)
]

if sector_filter:
    filtered = filtered[
        filtered["sector"].isin(sector_filter)
    ]

if search:
    filtered = filtered[
        filtered["company"].str.contains(
            search,
            case=False,
            na=False
        )
    ]


# ---------------- TABS ----------------

tab1, tab2, tab3, tab4 = st.tabs(
    [
        "⭐ Priority",
        "📍 By Hall",
        "🏢 All Companies",
        "📅 Events"
    ]
)


# ---------------- PRIORITY ----------------

with tab1:

    order = {
        "High": 0,
        "Medium": 1,
        "Low": 2
    }

    filtered = filtered.copy()

    filtered["_sort"] = (
        filtered["priority"]
        .map(order)
        .fillna(99)
    )

    filtered = filtered.sort_values("_sort")

    for _, row in filtered.iterrows():

        if row["priority"] == "High":
            priority_class = "high"

        elif row["priority"] == "Medium":
            priority_class = "medium"

        else:
            priority_class = "low"

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

        event_html = ""

        if row["event_info"]:
            event_html = (
                f'<div class="event">'
                f'📅 {row["event_info"]}'
                f'</div>'
            )

        card = (
            f'<div class="company-card {priority_class}">'
            f'<div class="company-name">{row["company"]}</div>'
            f'<div class="small-label">{row["type"]} · {row["sector"]}</div>'
            f'<div class="location">📍 {hall} · {stand}</div>'
            f'<div class="reason">{row["why_interesting"]}</div>'
            f'{event_html}'
            f'</div>'
        )

        st.markdown(
            card,
            unsafe_allow_html=True
        )


# ---------------- BY HALL ----------------

with tab2:

    located = df[
        df["confirmed_hall"] != ""
    ].copy()

    if located.empty:

        st.info(
            "Stand locations will appear here as they are confirmed."
        )

    else:

        hall_list = sorted(
            located["confirmed_hall"].unique()
        )

        for hall in hall_list:

            st.subheader(
                f"📍 Hall {hall}"
            )

            hall_data = located[
                located["confirmed_hall"] == hall
            ]

            for _, row in hall_data.iterrows():

                st.markdown(
                    f"**{row['company']}** — "
                    f"Stand {row['confirmed_stand']} · "
                    f"{row['sector']}"
                )

            st.divider()


# ---------------- ALL COMPANIES ----------------

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


# ---------------- EVENTS ----------------

with tab4:

    events = df[
        df["event_info"] != ""
    ]

    if events.empty:

        st.info(
            "No relevant events identified yet."
        )

    else:

        for _, row in events.iterrows():

            st.markdown(
                f"### {row['company']}"
            )

            st.write(
                row["event_info"]
            )

            st.divider()


# ---------------- FOOTER ----------------

st.divider()

st.caption(
    "Nuveen Natural Capital · "
    "Fruit Attraction 2026 · "
    f"Updated {datetime.now().strftime('%d %b %Y %H:%M')}"
)
