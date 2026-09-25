import streamlit as st
import pandas as pd
import requests
import base64
from datetime import datetime

# ============================================================
# PAGE
# ============================================================

st.set_page_config(
    page_title="Fruit Attraction 2026 | Nuveen Natural Capital",
    page_icon="🌱",
    layout="wide"
)

# ============================================================
# CONFIG
# ============================================================

CSV_FILE = "targets.csv"

IFEMA_API = (
    "https://lc-events-web-public.ifema.es/api/v1/"
    "tenants/3a88c5e5-a6e1-4898-b72b-103e4eed1731/"
    "editions/900c6c40-ac92-49ea-8ef6-08de63088e5d/"
    "exhibitors/search?language=es-ES"
)

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
    margin-top: 10px;
}

.reason {
    margin-top: 10px;
}

.confirmed {
    color: #17863c;
    font-weight: 600;
}

.pending {
    color: #b77900;
    font-weight: 600;
}

</style>
""", unsafe_allow_html=True)

# ============================================================
# HELPERS
# ============================================================

def clean_company_name(name):
    return str(name).strip()


def normalise_name(name):
    return (
        str(name)
        .strip()
        .lower()
        .replace("&", "and")
        .replace(".", "")
        .replace(",", "")
    )


def ensure_target_columns(df):

    defaults = {
        "company": "",
        "priority": "Medium",
        "type": "",
        "sector": "",
        "why_interesting": "",
        "confirmed_hall": "",
        "confirmed_stand": "",
        "event_info": "",
        "contact": "",
        "meeting_date": "",
        "meeting_time": "",
        "visited": "No",
        "notes": ""
    }

    for col, default in defaults.items():

        if col not in df.columns:
            df[col] = default

    return df[list(defaults.keys())]


# ============================================================
# IFEMA DATA
# ============================================================

@st.cache_data(ttl=3600)
def load_ifema():

    payload = {
        "page": 0,
        "pageSize": 10000,
        "search": "",
        "dynamicFields": [],
        "countryIds": [],
        "categoryIds": []
    }

    response = requests.post(
        IFEMA_API,
        json=payload,
        timeout=30
    )

    response.raise_for_status()

    raw = response.json()

    rows = []

    for exhibitor in raw.get("data", []):

        stands = exhibitor.get("standsInfo") or []

        if stands:

            for stand in stands:

                rows.append({
                    "company": clean_company_name(
                        exhibitor.get("name", "")
                    ),
                    "website": exhibitor.get("link", ""),
                    "pavilion": stand.get("location", ""),
                    "stand": stand.get("name", ""),
                    "ifema_status": "Confirmed by IFEMA",
                    "ifema_id": exhibitor.get("id", "")
                })

        else:

            rows.append({
                "company": clean_company_name(
                    exhibitor.get("name", "")
                ),
                "website": exhibitor.get("link", ""),
                "pavilion": "",
                "stand": "",
                "ifema_status": "Stand not yet published",
                "ifema_id": exhibitor.get("id", "")
            })

    df = pd.DataFrame(rows)

    if df.empty:
        return df

    df["company_key"] = (
        df["company"]
        .apply(normalise_name)
    )

    return df


# ============================================================
# TARGET DATA
# ============================================================

@st.cache_data(ttl=30)
def load_targets():

    df = pd.read_csv(
        CSV_FILE,
        dtype=str
    ).fillna("")

    return ensure_target_columns(df)


# ============================================================
# GITHUB SAVE
# ============================================================

def save_to_github(dataframe):

    dataframe = ensure_target_columns(
        dataframe.copy()
    )

    csv_content = dataframe.to_csv(
        index=False
    )

    api_url = (
        f"https://api.github.com/repos/"
        f"{GITHUB_OWNER}/{GITHUB_REPO}/"
        f"contents/{CSV_FILE}"
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
        "message": "Update Fruit Attraction shortlist",
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

        load_targets.clear()

        return True, "Saved"

    return False, response.text


# ============================================================
# RELEVANCE ENGINE
# ============================================================

def calculate_relevance(company, website=""):

    text = (
        str(company) + " " + str(website)
    ).lower()

    high_keywords = [
        "hortifrut",
        "citri",
        "agrimarba",
        "alcoaxarquia",
        "climate asset",
        "hsbc",
        "berries",
        "berry",
        "avocado",
        "aguacate",
        "citrus",
        "citricos"
    ]

    medium_keywords = [
        "agriculture",
        "agricola",
        "agrícola",
        "fruit",
        "frutas",
        "fresh",
        "produce",
        "irrigation",
        "riego",
        "water",
        "agua",
        "genetics",
        "genetica",
        "genética",
        "nursery",
        "vivero",
        "farm",
        "agro"
    ]

    score = 0

    for keyword in high_keywords:
        if keyword in text:
            score += 20

    for keyword in medium_keywords:
        if keyword in text:
            score += 5

    return score


# ============================================================
# LOAD
# ============================================================

try:

    ifema = load_ifema()

except Exception as e:

    st.error(
        f"Could not connect to IFEMA: {e}"
    )

    st.stop()


targets = load_targets()

targets["company_key"] = (
    targets["company"]
    .apply(normalise_name)
)

# ============================================================
# COMBINE IFEMA + NUVEN
# ============================================================

target_lookup = (
    targets
    .drop_duplicates("company_key")
    .set_index("company_key")
    .to_dict("index")
)

ifema["selected"] = (
    ifema["company_key"]
    .isin(target_lookup.keys())
)

ifema["priority"] = ifema["company_key"].apply(
    lambda x:
    target_lookup.get(x, {}).get(
        "priority",
        ""
    )
)

ifema["nuveen_score"] = ifema.apply(
    lambda row:
    calculate_relevance(
        row["company"],
        row["website"]
    ),
    axis=1
)

# Give selected companies a strong boost
ifema.loc[
    ifema["selected"],
    "nuveen_score"
] += 100

# High priority gets additional boost
ifema.loc[
    ifema["priority"] == "High",
    "nuveen_score"
] += 50

ifema = ifema.sort_values(
    ["nuveen_score", "company"],
    ascending=[False, True]
)

# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="title">'
    '🌱 Fruit Attraction 2026'
    '</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Nuveen Natural Capital · IFEMA Madrid · '
    '6–8 October 2026'
    '</div>',
    unsafe_allow_html=True
)

# ============================================================
# KPIs
# ============================================================

k1, k2, k3, k4 = st.columns(4)

k1.metric(
    "IFEMA exhibitors",
    ifema["company"].nunique()
)

k2.metric(
    "Nuveen shortlist",
    len(targets)
)

k3.metric(
    "High priority",
    len(
        targets[
            targets["priority"] == "High"
        ]
    )
)

k4.metric(
    "Stands published",
    len(
        ifema[
            ifema["stand"] != ""
        ]
    )
)

st.caption(
    "IFEMA data refreshes automatically every hour."
)

st.divider()

# ============================================================
# TABS
# ============================================================

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "⭐ Nuveen Shortlist",
    "🌍 All Exhibitors",
    "📍 By Pavilion",
    "📅 Meetings",
    "✏️ Manage Shortlist"
])

# ============================================================
# NUVEN SHORTLIST
# ============================================================

with tab1:

    st.subheader(
        "Nuveen priority companies"
    )

    target_view = targets.copy()

    priority_order = {
        "High": 1,
        "Medium": 2,
        "Low": 3
    }

    target_view["_priority_sort"] = (
        target_view["priority"]
        .map(priority_order)
        .fillna(99)
    )

    target_view = target_view.sort_values(
        "_priority_sort"
    )

    for _, target in target_view.iterrows():

        matches = ifema[
            ifema["company_key"]
            == target["company_key"]
        ]

        if not matches.empty:

            match = matches.iloc[0]

            pavilion = (
                match["pavilion"]
                if match["pavilion"]
                else "TBC"
            )

            stand = (
                match["stand"]
                if match["stand"]
                else "TBC"
            )

            status = match["ifema_status"]

        else:

            pavilion = "TBC"
            stand = "TBC"
            status = (
                "Not currently found "
                "in IFEMA catalogue"
            )

        css_class = (
            target["priority"].lower()
            if target["priority"]
            in ["High", "Medium", "Low"]
            else "medium"
        )

        status_class = (
            "confirmed"
            if "Confirmed" in status
            else "pending"
        )

        st.markdown(
            f"""
            <div class="company-card {css_class}">
                <div class="company-name">
                    {target["company"]}
                </div>

                <div class="small-label">
                    {target["sector"]}
                    · Priority {target["priority"]}
                </div>

                <div class="location">
                    📍 Pavilion {pavilion}
                    · Stand {stand}
                </div>

                <div class="{status_class}">
                    {status}
                </div>

                <div class="reason">
                    {target["why_interesting"]}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

# ============================================================
# ALL EXHIBITORS
# ============================================================

with tab2:

    st.subheader(
        f"All IFEMA exhibitors "
        f"({ifema['company'].nunique():,})"
    )

    search = st.text_input(
        "Search all exhibitors",
        placeholder=(
            "Hortifrut, Citri&Co, "
            "avocado, fruit..."
        )
    )

    col1, col2 = st.columns(2)

    pavilion_options = sorted(
        [
            x for x
            in ifema["pavilion"].unique()
            if x
        ]
    )

    pavilion_filter = col1.multiselect(
        "Pavilion",
        pavilion_options
    )

    shortlist_filter = col2.selectbox(
        "Shortlist status",
        [
            "All",
            "Selected only",
            "Not selected"
        ]
    )

    all_view = ifema.copy()

    if search:

        all_view = all_view[
            all_view["company"]
            .str.contains(
                search,
                case=False,
                na=False
            )
        ]

    if pavilion_filter:

        all_view = all_view[
            all_view["pavilion"]
            .isin(pavilion_filter)
        ]

    if shortlist_filter == "Selected only":

        all_view = all_view[
            all_view["selected"]
        ]

    elif shortlist_filter == "Not selected":

        all_view = all_view[
            ~all_view["selected"]
        ]

    display_df = all_view[
        [
            "company",
            "pavilion",
            "stand",
            "ifema_status",
            "selected",
            "priority",
            "website",
            "nuveen_score"
        ]
    ].copy()

    display_df.columns = [
        "Company",
        "Pavilion",
        "Stand",
        "IFEMA status",
        "Selected",
        "Priority",
        "Website",
        "Nuveen relevance"
    ]

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        height=600
    )

    st.caption(
        "Nuveen relevance is currently a "
        "keyword-based screening score. "
        "Selected companies are ranked first."
    )

# ============================================================
# BY PAVILION
# ============================================================

with tab3:

    selected_ifema = ifema[
        ifema["selected"]
    ].copy()

    if selected_ifema.empty:

        st.info(
            "No selected companies with "
            "IFEMA data yet."
        )

    else:

        for pavilion in sorted(
            selected_ifema[
                "pavilion"
            ].unique()
        ):

            pavilion_name = (
                pavilion
                if pavilion
                else "TBC"
            )

            st.subheader(
                f"📍 Pavilion {pavilion_name}"
            )

            pavilion_df = selected_ifema[
                selected_ifema["pavilion"]
                == pavilion
            ]

            for _, row in pavilion_df.iterrows():

                stand = (
                    row["stand"]
                    if row["stand"]
                    else "TBC"
                )

                st.write(
                    f"**{row['company']}** "
                    f"— Stand {stand}"
                )

            st.divider()

# ============================================================
# MEETINGS
# ============================================================

with tab4:

    meetings = targets[
        (targets["meeting_date"] != "")
        | (targets["meeting_time"] != "")
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
                f"{row['meeting_date']} "
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
# MANAGE SHORTLIST
# ============================================================

with tab5:

    st.subheader(
        "Manage Nuveen shortlist"
    )

    password = st.text_input(
        "Editing password",
        type="password"
    )

    if password == EDIT_PASSWORD and EDIT_PASSWORD:

        st.success(
            "Editing enabled"
        )

        # -------------------------------
        # ADD NEW EXHIBITOR
        # -------------------------------

        st.markdown(
            "### Add company from IFEMA"
        )

        available = ifema[
            ~ifema["selected"]
        ].copy()

        selected_company = st.selectbox(
            "Choose exhibitor",
            [""] +
            sorted(
                available["company"]
                .drop_duplicates()
                .tolist()
            )
        )

        new_priority = st.selectbox(
            "Priority",
            [
                "High",
                "Medium",
                "Low"
            ]
        )

        new_reason = st.text_input(
            "Why is it relevant?"
        )

        if st.button(
            "⭐ Add to Nuveen shortlist"
        ):

            if selected_company:

                new_row = {
                    "company": selected_company,
                    "priority": new_priority,
                    "type": "",
                    "sector": "",
                    "why_interesting": new_reason,
                    "confirmed_hall": "",
                    "confirmed_stand": "",
                    "event_info": "",
                    "contact": "",
                    "meeting_date": "",
                    "meeting_time": "",
                    "visited": "No",
                    "notes": ""
                }

                updated = pd.concat(
                    [
                        targets.drop(
                            columns=["company_key"],
                            errors="ignore"
                        ),
                        pd.DataFrame([new_row])
                    ],
                    ignore_index=True
                )

                success, message = (
                    save_to_github(updated)
                )

                if success:

                    st.success(
                        "Company added."
                    )

                    st.cache_data.clear()
                    st.rerun()

                else:

                    st.error(message)

        st.divider()

        # -------------------------------
        # EDIT EXISTING SHORTLIST
        # -------------------------------

        st.markdown(
            "### Edit current shortlist"
        )

        editable = targets.drop(
            columns=["company_key"],
            errors="ignore"
        ).copy()

        edited = st.data_editor(
            editable,
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            column_config={

                "priority":
                st.column_config.SelectboxColumn(
                    "Priority",
                    options=[
                        "High",
                        "Medium",
                        "Low"
                    ]
                ),

                "visited":
                st.column_config.SelectboxColumn(
                    "Visited",
                    options=[
                        "No",
                        "Yes"
                    ]
                )
            }
        )

        if st.button(
            "💾 Save shortlist changes",
            type="primary"
        ):

            success, message = (
                save_to_github(edited)
            )

            if success:

                st.success(
                    "Changes saved."
                )

                st.cache_data.clear()
                st.rerun()

            else:

                st.error(message)

    elif password:

        st.error(
            "Incorrect password."
        )

# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "IFEMA exhibitor data automatically "
    "checked hourly · "
    f"App refreshed "
    f"{datetime.now().strftime('%d %b %Y %H:%M')}"
)
