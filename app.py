import streamlit as st
import pandas as pd
import requests
import base64
from datetime import datetime

st.set_page_config(
    page_title="Fruit Attraction 2026 | Nuveen Natural Capital",
    page_icon="🌱",
    layout="wide"
)

# ============================================================
# CONFIG
# ============================================================

CSV_FILE = "targets.csv"

GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")
GITHUB_OWNER = st.secrets.get("GITHUB_OWNER", "")
GITHUB_REPO = st.secrets.get("GITHUB_REPO", "")
EDIT_PASSWORD = st.secrets.get("EDIT_PASSWORD", "")

# ============================================================
# STYLE
# ============================================================

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
    border-left: 7px solid #999;
}

.company-name {
    font-size: 22px;
    font-weight: 700;
}

.small-label {
    color: #777;
    font-size: 14px;
}

.location {
    font-size: 16px;
    font-weight: 600;
    margin-top: 14px;
}

.reason {
    margin-top: 12px;
}

.event {
    margin-top: 12px;
    color: #555;
}

</style>
""", unsafe_allow_html=True)

# ============================================================
# FUNCTIONS
# ============================================================

@st.cache_data(ttl=30)
def load_data():
    return pd.read_csv(CSV_FILE, dtype=str).fillna("")


def save_to_github(dataframe):

    csv_content = dataframe.to_csv(index=False)

    api_url = (
        f"https://api.github.com/repos/"
        f"{GITHUB_OWNER}/{GITHUB_REPO}/contents/{CSV_FILE}"
    )

    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

    current = requests.get(
        api_url,
        headers=headers,
        timeout=20
    )

    if current.status_code != 200:
        return False, current.text

    sha = current.json()["sha"]

    encoded_content = base64.b64encode(
        csv_content.encode("utf-8")
    ).decode("utf-8")

    payload = {
        "message": "Update targets from Streamlit dashboard",
        "content": encoded_content,
        "sha": sha
    }

    response = requests.put(
        api_url,
        headers=headers,
        json=payload,
        timeout=20
    )

    if response.status_code in [200, 201]:
        load_data.clear()
        return True, "Saved"

    return False, response.text


# ============================================================
# DATA
# ============================================================

df = load_data()

# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="title">🌱 Fruit Attraction 2026</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Nuveen Natural Capital · IFEMA Madrid · 6–8 October 2026'
    '</div>',
    unsafe_allow_html=True
)

# ============================================================
# KPIs
# ============================================================

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
    "Visited",
    len(df[df["visited"] == "Yes"])
)

st.divider()

# ============================================================
# FILTERS
# ============================================================

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

# ============================================================
# TABS
# ============================================================

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "⭐ Priority",
    "📍 By Hall",
    "📅 Meetings",
    "🏢 All Companies",
    "✏️ Edit"
])

# ============================================================
# PRIORITY
# ============================================================

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

        css_class = row["priority"].lower()

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

        meeting_html = ""

        if row["meeting_date"] or row["meeting_time"]:
            meeting_html = (
                f'<div class="event">'
                f'🤝 Meeting: '
                f'{row["meeting_date"]} '
                f'{row["meeting_time"]}'
                f'</div>'
            )

        visited_html = ""

        if row["visited"] == "Yes":
            visited_html = (
                '<div class="event">'
                '✅ Visited'
                '</div>'
            )

        card = (
            f'<div class="company-card {css_class}">'
            f'<div class="company-name">{row["company"]}</div>'
            f'<div class="small-label">'
            f'{row["type"]} · {row["sector"]}'
            f'</div>'
            f'<div class="location">'
            f'📍 {hall} · {stand}'
            f'</div>'
            f'<div class="reason">'
            f'{row["why_interesting"]}'
            f'</div>'
            f'{event_html}'
            f'{meeting_html}'
            f'{visited_html}'
            f'</div>'
        )

        st.markdown(
            card,
            unsafe_allow_html=True
        )

# ============================================================
# BY HALL
# ============================================================

with tab2:

    located = df[
        df["confirmed_hall"] != ""
    ].copy()

    if located.empty:
        st.info("No confirmed stands yet.")

    else:
        for hall in sorted(
            located["confirmed_hall"].unique()
        ):

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

# ============================================================
# MEETINGS
# ============================================================

with tab3:

    meetings = df[
        (df["meeting_date"] != "")
        | (df["meeting_time"] != "")
    ]

    if meetings.empty:

        st.info(
            "No meetings scheduled yet."
        )

    else:

        for _, row in meetings.iterrows():

            st.markdown(
                f"### 🤝 {row['company']}"
            )

            st.write(
                f"{row['meeting_date']} · "
                f"{row['meeting_time']}"
            )

            if row["contact"]:
                st.write(
                    f"Contact: {row['contact']}"
                )

            if row["notes"]:
                st.write(
                    f"Notes: {row['notes']}"
                )

            st.divider()

# ============================================================
# ALL COMPANIES
# ============================================================

with tab4:

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )

# ============================================================
# EDIT
# ============================================================

with tab5:

    st.subheader("Edit visit plan")

    password = st.text_input(
        "Editing password",
        type="password"
    )

    if password == EDIT_PASSWORD and EDIT_PASSWORD:

        st.success("Editing enabled")

        editable_columns = [
            "company",
            "priority",
            "type",
            "sector",
            "why_interesting",
            "confirmed_hall",
            "confirmed_stand",
            "contact",
            "meeting_date",
            "meeting_time",
            "visited",
            "notes"
        ]

        edited_df = st.data_editor(
            df[editable_columns],
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            column_config={

                "priority": st.column_config.SelectboxColumn(
                    "Priority",
                    options=[
                        "High",
                        "Medium",
                        "Low"
                    ]
                ),

                "visited": st.column_config.SelectboxColumn(
                    "Visited",
                    options=[
                        "No",
                        "Yes"
                    ]
                ),

                "meeting_date": st.column_config.TextColumn(
                    "Meeting date"
                ),

                "meeting_time": st.column_config.TextColumn(
                    "Meeting time"
                ),

                "notes": st.column_config.TextColumn(
                    "Notes",
                    width="large"
                )
            }
        )

        if st.button(
            "💾 Save changes",
            type="primary"
        ):

            event_map = {}

            if "event_info" in df.columns:
                event_map = (
                    df.set_index("company")
                    ["event_info"]
                    .to_dict()
                )

            edited_df["event_info"] = (
                edited_df["company"]
                .map(event_map)
                .fillna("")
            )

            success, message = save_to_github(
                edited_df
            )

            if success:

                st.success(
                    "Changes saved successfully."
                )

                st.cache_data.clear()
                st.rerun()

            else:

                st.error(
                    f"Could not save: {message}"
                )

    elif password:

        st.error(
            "Incorrect password."
        )

st.divider()

st.caption(
    "Nuveen Natural Capital · "
    "Fruit Attraction 2026 · "
    f"{datetime.now().strftime('%d %b %Y %H:%M')}"
)
