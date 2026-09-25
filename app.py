import streamlit as st
import pandas as pd
import requests
import base64
import re
from datetime import datetime

# ============================================================
# PAGE CONFIG
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
# CSS
# ============================================================

st.markdown(
    """
    <style>
    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    .main-title {
        font-size: 42px;
        font-weight: 750;
        margin-bottom: 0px;
    }

    .subtitle {
        color: #6b7280;
        font-size: 16px;
        margin-top: 2px;
        margin-bottom: 25px;
    }

    div[data-testid="stMetric"] {
        border: 1px solid #e5e7eb;
        padding: 15px;
        border-radius: 12px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ============================================================
# HELPERS
# ============================================================

def normalise_name(value):
    value = str(value or "").strip().lower()

    replacements = {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "ü": "u",
        "ñ": "n",
        "&": "and",
    }

    for old, new in replacements.items():
        value = value.replace(old, new)

    value = re.sub(r"[^a-z0-9]+", " ", value)

    return " ".join(value.split())


def clean_text(value):
    if value is None:
        return ""
    return str(value).strip()


def pavilion_sort_key(value):
    value = clean_text(value).upper()

    if not value:
        return 999

    match = re.search(r"\d+", value)

    if match:
        return int(match.group())

    return 998


def ensure_target_columns(df):

    defaults = {
        "company": "",
        "rank": "",
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

    for column, default in defaults.items():
        if column not in df.columns:
            df[column] = default

    for column in defaults:
        df[column] = df[column].fillna("").astype(str)

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

    result = response.json()

    rows = []

    for exhibitor in result.get("data", []):

        company = clean_text(exhibitor.get("name"))
        website = clean_text(exhibitor.get("link"))
        exhibitor_id = clean_text(exhibitor.get("id"))

        stands = exhibitor.get("standsInfo") or []

        if stands:

            for stand in stands:

                pavilion = clean_text(
                    stand.get("location")
                )

                stand_name = clean_text(
                    stand.get("name")
                )

                rows.append({
                    "company": company,
                    "company_key": normalise_name(company),
                    "website": website,
                    "pavilion": pavilion,
                    "stand": stand_name,
                    "ifema_status": "Confirmed by IFEMA",
                    "ifema_id": exhibitor_id
                })

        else:

            rows.append({
                "company": company,
                "company_key": normalise_name(company),
                "website": website,
                "pavilion": "",
                "stand": "",
                "ifema_status": "Stand not yet published",
                "ifema_id": exhibitor_id
            })

    df = pd.DataFrame(rows)

    if df.empty:
        return pd.DataFrame(
            columns=[
                "company",
                "company_key",
                "website",
                "pavilion",
                "stand",
                "ifema_status",
                "ifema_id"
            ]
        )

    for column in df.columns:
        df[column] = df[column].fillna("").astype(str)

    return df


# ============================================================
# TARGETS
# ============================================================

@st.cache_data(ttl=30)
def load_targets():

    try:
        df = pd.read_csv(
            CSV_FILE,
            dtype=str
        ).fillna("")

    except Exception:
        df = pd.DataFrame()

    df = ensure_target_columns(df)

    # Initial ranking if rank has never been set.
    initial_ranking = {
        "hortifrut": 1,
        "citri and co": 2,
        "agrimarba": 3,
        "climate asset management": 4,
        "hsbc": 5,
        "alcoaxarquia": 6,
        "veolia agricultura": 7,
        "fall creek": 8,
        "planasa": 9,
        "agq labs": 10
    }

    def assign_rank(row):

        existing = clean_text(row["rank"])

        if existing:
            return existing

        key = normalise_name(row["company"])

        for target_name, rank in initial_ranking.items():

            if normalise_name(target_name) in key:
                return str(rank)

        return "99"

    df["rank"] = df.apply(
        assign_rank,
        axis=1
    )

    return df


# ============================================================
# SAVE TO GITHUB
# ============================================================

def save_to_github(dataframe):

    dataframe = ensure_target_columns(
        dataframe.copy()
    )

    csv_content = dataframe.to_csv(
        index=False
    )

    url = (
        f"https://api.github.com/repos/"
        f"{GITHUB_OWNER}/{GITHUB_REPO}/"
        f"contents/{CSV_FILE}"
    )

    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

    current = requests.get(
        url,
        headers=headers,
        timeout=20
    )

    if current.status_code != 200:
        return False, current.text

    sha = current.json()["sha"]

    encoded = base64.b64encode(
        csv_content.encode("utf-8")
    ).decode("utf-8")

    payload = {
        "message": "Update Fruit Attraction shortlist",
        "content": encoded,
        "sha": sha
    }

    response = requests.put(
        url,
        headers=headers,
        json=payload,
        timeout=20
    )

    if response.status_code in [200, 201]:

        load_targets.clear()

        return True, "Saved"

    return False, response.text


# ============================================================
# RELEVANCE
# ============================================================

def calculate_relevance(company, website=""):

    text = (
        clean_text(company)
        + " "
        + clean_text(website)
    ).lower()

    score = 0

    strategic = [
        "hortifrut",
        "citri",
        "agrimarba",
        "alcoaxarquia",
        "climate asset",
        "hsbc"
    ]

    crop_keywords = [
        "berry",
        "berries",
        "blueberry",
        "avocado",
        "aguacate",
        "citrus",
        "citric",
        "orange",
        "mandarin",
        "lemon",
        "almond",
        "walnut",
        "olive",
        "kiwi"
    ]

    ag_keywords = [
        "agri",
        "agro",
        "farm",
        "fruit",
        "produce",
        "grower",
        "irrigation",
        "water",
        "riego",
        "nursery",
        "genetic",
        "vivero"
    ]

    for keyword in strategic:
        if keyword in text:
            score += 50

    for keyword in crop_keywords:
        if keyword in text:
            score += 15

    for keyword in ag_keywords:
        if keyword in text:
            score += 5

    return score


# ============================================================
# LOAD
# ============================================================

try:
    ifema = load_ifema()

except Exception as error:

    st.error(
        "Could not connect to the IFEMA catalogue."
    )

    st.code(str(error))

    st.stop()


targets = load_targets()

targets["company_key"] = targets[
    "company"
].apply(normalise_name)

# ============================================================
# MERGE SHORTLIST INFORMATION
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

ifema["priority"] = ifema[
    "company_key"
].apply(
    lambda key:
    target_lookup.get(
        key, {}
    ).get(
        "priority", ""
    )
)

ifema["rank"] = ifema[
    "company_key"
].apply(
    lambda key:
    target_lookup.get(
        key, {}
    ).get(
        "rank", ""
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

# Selected companies appear first.
ifema.loc[
    ifema["selected"],
    "nuveen_score"
] += 100

ifema.loc[
    ifema["priority"] == "High",
    "nuveen_score"
] += 40

ifema = ifema.sort_values(
    ["nuveen_score", "company"],
    ascending=[False, True]
)

# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="main-title">🌱 Fruit Attraction 2026</div>',
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
    f"{ifema['company'].nunique():,}"
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
    ifema.loc[
        ifema["stand"] != "",
        "company"
    ].nunique()
)

st.caption(
    "IFEMA exhibitor data is refreshed automatically every hour."
)

st.divider()

# ============================================================
# TABS
# ============================================================

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "⭐ Nuveen Shortlist",
        "🌍 All Exhibitors",
        "📍 By Pavilion",
        "📅 Meetings",
        "✏️ Manage Shortlist"
    ]
)

# ============================================================
# SHORTLIST
# ============================================================

with tab1:

    st.subheader("Nuveen priority companies")

    view = targets.copy()

    view["_rank"] = pd.to_numeric(
        view["rank"],
        errors="coerce"
    ).fillna(999)

    view = view.sort_values(
        ["_rank", "company"]
    )

    for _, target in view.iterrows():

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

            confirmed = (
                bool(match["stand"])
            )

        else:

            pavilion = "TBC"
            stand = "TBC"
            confirmed = False

        with st.container(border=True):

            left, right = st.columns(
                [5, 1]
            )

            with left:

                st.markdown(
                    f"### #{target['rank']} · {target['company']}"
                )

                sector_text = (
                    target["sector"]
                    if target["sector"]
                    else "Sector TBC"
                )

                st.caption(
                    f"{sector_text} · "
                    f"Priority {target['priority']}"
                )

                st.markdown(
                    f"📍 **Pavilion {pavilion} · Stand {stand}**"
                )

                if confirmed:
                    st.success(
                        "Confirmed by IFEMA",
                        icon="✅"
                    )

                else:
                    st.warning(
                        "Location not yet published by IFEMA",
                        icon="⏳"
                    )

                if target["why_interesting"]:
                    st.write(
                        target["why_interesting"]
                    )

            with right:

                if target["visited"] == "Yes":
                    st.success("Visited")
                else:
                    st.write("")

# ============================================================
# ALL EXHIBITORS
# ============================================================

with tab2:

    st.subheader(
        f"All IFEMA exhibitors "
        f"({ifema['company'].nunique():,})"
    )

    search = st.text_input(
        "Search exhibitor",
        placeholder=(
            "Company, avocado, berry..."
        ),
        key="all_search"
    )

    f1, f2, f3 = st.columns(3)

    pavilion_options = sorted(
        {
            clean_text(x)
            for x in ifema["pavilion"]
            if clean_text(x)
        },
        key=pavilion_sort_key
    )

    pavilion_filter = f1.multiselect(
        "Pavilion",
        pavilion_options
    )

    selection_filter = f2.selectbox(
        "Shortlist",
        [
            "All",
            "Selected",
            "Not selected"
        ]
    )

    status_filter = f3.selectbox(
        "IFEMA location",
        [
            "All",
            "Stand confirmed",
            "Stand pending"
        ]
    )

    all_view = ifema.copy()

    if search:

        search_lower = search.lower()

        all_view = all_view[
            all_view["company"]
            .str.lower()
            .str.contains(
                search_lower,
                na=False,
                regex=False
            )
        ]

    if pavilion_filter:

        all_view = all_view[
            all_view["pavilion"]
            .isin(pavilion_filter)
        ]

    if selection_filter == "Selected":

        all_view = all_view[
            all_view["selected"]
        ]

    elif selection_filter == "Not selected":

        all_view = all_view[
            ~all_view["selected"]
        ]

    if status_filter == "Stand confirmed":

        all_view = all_view[
            all_view["stand"] != ""
        ]

    elif status_filter == "Stand pending":

        all_view = all_view[
            all_view["stand"] == ""
        ]

    display = all_view[
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

    display.columns = [
        "Company",
        "Pavilion",
        "Stand",
        "IFEMA status",
        "Shortlist",
        "Priority",
        "Website",
        "Nuveen relevance"
    ]

    st.dataframe(
        display,
        use_container_width=True,
        hide_index=True,
        height=650,
        column_config={
            "Website":
            st.column_config.LinkColumn(
                "Website"
            )
        }
    )

# ============================================================
# BY PAVILION
# ============================================================

with tab3:

    st.subheader(
        "Shortlist by pavilion"
    )

    selected_ifema = ifema[
        ifema["selected"]
    ].copy()

    if selected_ifema.empty:

        st.info(
            "No shortlist companies have been matched to IFEMA yet."
        )

    else:

        pavilion_values = {
            clean_text(x)
            for x in selected_ifema[
                "pavilion"
            ]
        }

        pavilion_options = sorted(
            pavilion_values,
            key=pavilion_sort_key
        )

        for pavilion in pavilion_options:

            pavilion_label = (
                pavilion
                if pavilion
                else "TBC"
            )

            st.markdown(
                f"## 📍 Pavilion {pavilion_label}"
            )

            pavilion_df = selected_ifema[
                selected_ifema[
                    "pavilion"
                ] == pavilion
            ].copy()

            pavilion_df["_rank"] = pd.to_numeric(
                pavilion_df["rank"],
                errors="coerce"
            ).fillna(999)

            pavilion_df = pavilion_df.sort_values(
                ["_rank", "company"]
            )

            for _, row in pavilion_df.iterrows():

                stand = (
                    row["stand"]
                    if row["stand"]
                    else "TBC"
                )

                st.markdown(
                    f"**#{row['rank']} · "
                    f"{row['company']}** "
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
    ].copy()

    if meetings.empty:

        st.info(
            "No meetings scheduled yet."
        )

    else:

        meetings["_rank"] = pd.to_numeric(
            meetings["rank"],
            errors="coerce"
        ).fillna(999)

        meetings = meetings.sort_values(
            ["meeting_date", "meeting_time", "_rank"]
        )

        for _, row in meetings.iterrows():

            with st.container(border=True):

                st.markdown(
                    f"### 🤝 {row['company']}"
                )

                st.write(
                    f"**{row['meeting_date']} "
                    f"{row['meeting_time']}**"
                )

                if row["contact"]:
                    st.write(
                        f"Contact: {row['contact']}"
                    )

                if row["notes"]:
                    st.write(
                        row["notes"]
                    )

# ============================================================
# MANAGE SHORTLIST
# ============================================================

with tab5:

    st.subheader(
        "Manage Nuveen shortlist"
    )

    password = st.text_input(
        "Editing password",
        type="password",
        key="edit_password"
    )

    if (
        password == EDIT_PASSWORD
        and EDIT_PASSWORD
    ):

        st.success(
            "Editing enabled"
        )

        # ----------------------------------------------------
        # ADD FROM IFEMA
        # ----------------------------------------------------

        st.markdown(
            "### Add an IFEMA exhibitor"
        )

        selected_keys = set(
            targets["company_key"]
        )

        available = (
            ifema[
                ~ifema["company_key"]
                .isin(selected_keys)
            ]
            .drop_duplicates("company_key")
            .sort_values(
                ["nuveen_score", "company"],
                ascending=[False, True]
            )
        )

        company_options = (
            [""]
            + available[
                "company"
            ].tolist()
        )

        new_company = st.selectbox(
            "Company",
            company_options
        )

        c1, c2 = st.columns(2)

        new_rank = c1.number_input(
            "Rank",
            min_value=1,
            max_value=999,
            value=len(targets) + 1,
            step=1
        )

        new_priority = c2.selectbox(
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
            "⭐ Add to shortlist"
        ):

            if not new_company:

                st.warning(
                    "Select a company first."
                )

            else:

                new_row = {
                    "company": new_company,
                    "rank": str(new_rank),
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
                            columns=[
                                "company_key"
                            ],
                            errors="ignore"
                        ),
                        pd.DataFrame(
                            [new_row]
                        )
                    ],
                    ignore_index=True
                )

                success, message = (
                    save_to_github(
                        updated
                    )
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

        # ----------------------------------------------------
        # EDIT EXISTING
        # ----------------------------------------------------

        st.markdown(
            "### Edit shortlist"
        )

        editable = targets.drop(
            columns=["company_key"],
            errors="ignore"
        ).copy()

        editable["_rank_num"] = pd.to_numeric(
            editable["rank"],
            errors="coerce"
        ).fillna(999)

        editable = (
            editable
            .sort_values(
                ["_rank_num", "company"]
            )
            .drop(
                columns=["_rank_num"]
            )
        )

        edited = st.data_editor(
            editable,
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            column_config={
                "rank":
                st.column_config.NumberColumn(
                    "Rank",
                    min_value=1,
                    step=1
                ),

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
                ),

                "notes":
                st.column_config.TextColumn(
                    "Notes",
                    width="large"
                )
            }
        )

        if st.button(
            "💾 Save shortlist changes",
            type="primary"
        ):

            success, message = (
                save_to_github(
                    edited
                )
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
    "IFEMA catalogue checked automatically every hour · "
    f"Session refreshed "
    f"{datetime.now().strftime('%d %b %Y %H:%M')}"
)
