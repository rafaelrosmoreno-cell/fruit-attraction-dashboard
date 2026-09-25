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

IFEMA_PROGRAM_URL = (
    "https://www.ifema.es/fruit-attraction/horario-actividades"
)

GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")
GITHUB_OWNER = st.secrets.get("GITHUB_OWNER", "")
GITHUB_REPO = st.secrets.get("GITHUB_REPO", "")
EDIT_PASSWORD = st.secrets.get("EDIT_PASSWORD", "")

# ============================================================
# IMPORTANT EVENTS
# ============================================================

IMPORTANT_EVENTS = [
    {
        "date": "07 Oct 2026",
        "time": "16:30–19:30",
        "title": "Blueberry World Forum & Cocktail",
        "location": "Retiro Lounge · IFEMA Madrid",
        "category": "Berries",
        "relevance": "High",
        "description": (
            "International blueberry industry forum and networking event. "
            "Highly relevant for growers, operators, genetics and berry investment."
        ),
        "status": "Confirmed",
        "source": "International Blueberry Organization"
    },
    {
        "date": "6–8 Oct 2026",
        "time": "TBC",
        "title": "Factoría Chef",
        "location": "IFEMA Madrid · location TBC",
        "category": "Fresh Produce",
        "relevance": "Medium",
        "description": (
            "IFEMA's gastronomic and product-presentation stage for participating "
            "Fresh Produce companies."
        ),
        "status": "Confirmed · schedule pending",
        "source": "IFEMA"
    },
    {
        "date": "6–8 Oct 2026",
        "time": "TBC",
        "title": "Official Fruit Attraction conferences & technical sessions",
        "location": "IFEMA Madrid",
        "category": "Industry",
        "relevance": "High",
        "description": (
            "Congresses, forums, seminars and technical sessions. "
            "Detailed 2026 programme has not yet been published by IFEMA."
        ),
        "status": "Programme TBC",
        "source": "IFEMA"
    }
]

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

def clean_text(value):
    if value is None:
        return ""
    return str(value).strip()


def normalise_name(value):

    value = clean_text(value).lower()

    replacements = {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "ü": "u",
        "ñ": "n",
        "&": "and"
    }

    for old, new in replacements.items():
        value = value.replace(old, new)

    value = re.sub(r"[^a-z0-9]+", " ", value)

    return " ".join(value.split())


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

        df[column] = (
            df[column]
            .fillna("")
            .astype(str)
        )

    return df[list(defaults.keys())]


# ============================================================
# LOAD IFEMA
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

    total_elements = result.get(
        "totalElements",
        0
    )

    rows = []

    for exhibitor in result.get("data", []):

        company = clean_text(
            exhibitor.get("name")
        )

        website = clean_text(
            exhibitor.get("link")
        )

        exhibitor_id = clean_text(
            exhibitor.get("id")
        )

        stands = (
            exhibitor.get("standsInfo")
            or []
        )

        if stands:

            for stand in stands:

                rows.append({
                    "company": company,
                    "company_key": normalise_name(company),
                    "website": website,
                    "pavilion": clean_text(
                        stand.get("location")
                    ),
                    "stand": clean_text(
                        stand.get("name")
                    ),
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

        df = pd.DataFrame(
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

        df[column] = (
            df[column]
            .fillna("")
            .astype(str)
        )

    return df, total_elements


# ============================================================
# LOAD TARGETS
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

    # --------------------------------------------------------
    # INITIAL RANKING
    # Only applies if rank is blank
    # --------------------------------------------------------

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

        existing = clean_text(
            row["rank"]
        )

        if existing:
            return existing

        key = normalise_name(
            row["company"]
        )

        for name, rank in initial_ranking.items():

            if normalise_name(name) in key:
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

    dataframe = dataframe.copy()

    dataframe = dataframe.drop(
        columns=["company_key"],
        errors="ignore"
    )

    dataframe = ensure_target_columns(
        dataframe
    )

    csv_content = dataframe.to_csv(
        index=False
    )

    url = (
        f"https://api.github.com/repos/"
        f"{GITHUB_OWNER}/"
        f"{GITHUB_REPO}/"
        f"contents/{CSV_FILE}"
    )

    headers = {
        "Authorization": (
            f"Bearer {GITHUB_TOKEN}"
        ),
        "Accept": (
            "application/vnd.github+json"
        )
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
        "message": (
            "Update Fruit Attraction dashboard"
        ),
        "content": encoded,
        "sha": sha
    }

    response = requests.put(
        url,
        headers=headers,
        json=payload,
        timeout=20
    )

    if response.status_code in [
        200,
        201
    ]:

        load_targets.clear()

        return True, "Saved"

    return False, response.text


# ============================================================
# NUVEN RELEVANCE ENGINE
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
        "hsbc",
        "surexport"
    ]

    high_crop = [
        "berry",
        "berries",
        "blueberry",
        "raspberry",
        "strawberry",
        "avocado",
        "aguacate",
        "citrus",
        "citric",
        "orange",
        "mandarin",
        "lemon",
        "kiwi",
        "almond",
        "walnut",
        "olive"
    ]

    agriculture = [
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

    for keyword in high_crop:

        if keyword in text:
            score += 15

    for keyword in agriculture:

        if keyword in text:
            score += 5

    return score


# ============================================================
# LOAD DATA
# ============================================================

try:

    ifema, ifema_total = (
        load_ifema()
    )

except Exception as error:

    st.error(
        "Could not connect to the IFEMA catalogue."
    )

    st.code(
        str(error)
    )

    st.stop()


targets = load_targets()

targets["company_key"] = (
    targets["company"]
    .apply(normalise_name)
)

# ============================================================
# MERGE IFEMA + SHORTLIST
# ============================================================

target_lookup = (
    targets
    .drop_duplicates(
        "company_key"
    )
    .set_index(
        "company_key"
    )
    .to_dict(
        "index"
    )
)

ifema["selected"] = (
    ifema["company_key"]
    .isin(
        target_lookup.keys()
    )
)

ifema["priority"] = (
    ifema["company_key"]
    .apply(
        lambda key:
        target_lookup
        .get(key, {})
        .get("priority", "")
    )
)

ifema["rank"] = (
    ifema["company_key"]
    .apply(
        lambda key:
        target_lookup
        .get(key, {})
        .get("rank", "")
    )
)

ifema["nuveen_score"] = (
    ifema.apply(
        lambda row:
        calculate_relevance(
            row["company"],
            row["website"]
        ),
        axis=1
    )
)

# Selected companies first
ifema.loc[
    ifema["selected"],
    "nuveen_score"
] += 100

# High priority boost
ifema.loc[
    ifema["priority"] == "High",
    "nuveen_score"
] += 40

ifema = (
    ifema
    .sort_values(
        [
            "nuveen_score",
            "company"
        ],
        ascending=[
            False,
            True
        ]
    )
)

# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="main-title">'
    '🌱 Fruit Attraction 2026'
    '</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Nuveen Natural Capital · '
    'IFEMA Madrid · '
    '6–8 October 2026'
    '</div>',
    unsafe_allow_html=True
)

# ============================================================
# KPI CARDS
# ============================================================

k1, k2, k3, k4 = (
    st.columns(4)
)

k1.metric(
    "IFEMA exhibitors",
    f"{ifema_total:,}"
)

k2.metric(
    "Nuveen shortlist",
    len(targets)
)

k3.metric(
    "High priority",
    len(
        targets[
            targets["priority"]
            == "High"
        ]
    )
)

k4.metric(
    "Meetings",
    len(
        targets[
            (
                targets["meeting_date"]
                != ""
            )
            |
            (
                targets["meeting_time"]
                != ""
            )
        ]
    )
)

st.caption(
    "IFEMA exhibitor data is "
    "re-checked automatically every hour "
    "while the app is being used."
)

st.divider()

# ============================================================
# TABS
# ============================================================

(
    tab1,
    tab2,
    tab3,
    tab4,
    tab5,
    tab6
) = st.tabs(
    [
        "⭐ Nuveen Shortlist",
        "🌍 All Exhibitors",
        "📍 By Pavilion",
        "📅 Meetings",
        "🎤 Events & Talks",
        "✏️ Manage Shortlist"
    ]
)

# ============================================================
# TAB 1 — NUVEN SHORTLIST
# ============================================================

with tab1:

    st.subheader(
        "Nuveen priority companies"
    )

    view = targets.copy()

    view["_rank"] = (
        pd.to_numeric(
            view["rank"],
            errors="coerce"
        )
        .fillna(999)
    )

    view = view.sort_values(
        [
            "_rank",
            "company"
        ]
    )

    for _, target in view.iterrows():

        matches = ifema[
            ifema["company_key"]
            == target["company_key"]
        ]

        if not matches.empty:

            match = (
                matches.iloc[0]
            )

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

            confirmed = bool(
                match["stand"]
            )

            website = (
                match["website"]
            )

        else:

            pavilion = "TBC"
            stand = "TBC"
            confirmed = False
            website = ""

        with st.container(
            border=True
        ):

            left, right = (
                st.columns(
                    [5, 1]
                )
            )

            with left:

                st.markdown(
                    f"### #{target['rank']} · "
                    f"{target['company']}"
                )

                sector = (
                    target["sector"]
                    if target["sector"]
                    else "Sector TBC"
                )

                st.caption(
                    f"{sector} · "
                    f"Priority "
                    f"{target['priority']}"
                )

                st.markdown(
                    f"📍 **Pavilion "
                    f"{pavilion} · "
                    f"Stand {stand}**"
                )

                if confirmed:

                    st.success(
                        "Confirmed by IFEMA",
                        icon="✅"
                    )

                else:

                    st.warning(
                        "Location not yet "
                        "published by IFEMA",
                        icon="⏳"
                    )

                if (
                    target[
                        "why_interesting"
                    ]
                ):

                    st.write(
                        target[
                            "why_interesting"
                        ]
                    )

                if website:

                    st.markdown(
                        f"[Company website]"
                        f"({website})"
                    )

            with right:

                if (
                    target["visited"]
                    == "Yes"
                ):

                    st.success(
                        "Visited"
                    )

# ============================================================
# TAB 2 — ALL EXHIBITORS
# ============================================================

with tab2:

    st.subheader(
        f"All IFEMA exhibitors "
        f"({ifema_total:,})"
    )

    st.caption(
        "Search the full IFEMA catalogue "
        "and add companies directly to "
        "the Nuveen shortlist."
    )

    search = st.text_input(
        "Search exhibitor",
        placeholder=(
            "Hortifrut, Surexport, "
            "avocado, berries..."
        ),
        key="all_search"
    )

    f1, f2, f3 = (
        st.columns(3)
    )

    pavilion_options = sorted(
        {
            clean_text(x)
            for x
            in ifema["pavilion"]
            if clean_text(x)
        },
        key=pavilion_sort_key
    )

    pavilion_filter = (
        f1.multiselect(
            "Pavilion",
            pavilion_options
        )
    )

    selection_filter = (
        f2.selectbox(
            "Shortlist",
            [
                "All",
                "Selected",
                "Not selected"
            ]
        )
    )

    status_filter = (
        f3.selectbox(
            "IFEMA location",
            [
                "All",
                "Stand confirmed",
                "Stand pending"
            ]
        )
    )

    all_view = ifema.copy()

    # Search
    if search:

        all_view = (
            all_view[
                all_view["company"]
                .str.contains(
                    search,
                    case=False,
                    na=False,
                    regex=False
                )
            ]
        )

    # Pavilion
    if pavilion_filter:

        all_view = (
            all_view[
                all_view["pavilion"]
                .isin(
                    pavilion_filter
                )
            ]
        )

    # Shortlist status
    if (
        selection_filter
        == "Selected"
    ):

        all_view = (
            all_view[
                all_view["selected"]
            ]
        )

    elif (
        selection_filter
        == "Not selected"
    ):

        all_view = (
            all_view[
                ~all_view["selected"]
            ]
        )

    # Location status
    if (
        status_filter
        == "Stand confirmed"
    ):

        all_view = (
            all_view[
                all_view["stand"]
                != ""
            ]
        )

    elif (
        status_filter
        == "Stand pending"
    ):

        all_view = (
            all_view[
                all_view["stand"]
                == ""
            ]
        )

    # Relevance ordering
    all_view = (
        all_view
        .sort_values(
            [
                "selected",
                "nuveen_score",
                "company"
            ],
            ascending=[
                False,
                False,
                True
            ]
        )
    )

    all_view = (
        all_view
        .drop_duplicates(
            subset=[
                "company_key",
                "pavilion",
                "stand"
            ]
        )
    )

    # Table
    display = all_view[
        [
            "company",
            "pavilion",
            "stand",
            "ifema_status",
            "selected",
            "priority",
            "website",
            "nuveen_score",
            "company_key"
        ]
    ].copy()

    display.insert(
        0,
        "add",
        False
    )

    edited_exhibitors = (
        st.data_editor(
            display,
            use_container_width=True,
            hide_index=True,
            height=620,
            disabled=[
                "company",
                "pavilion",
                "stand",
                "ifema_status",
                "selected",
                "priority",
                "website",
                "nuveen_score",
                "company_key"
            ],
            column_config={

                "add":
                st.column_config.CheckboxColumn(
                    "Add",
                    help=(
                        "Tick companies to add "
                        "to the shortlist"
                    )
                ),

                "company":
                st.column_config.TextColumn(
                    "Company",
                    width="large"
                ),

                "pavilion":
                st.column_config.TextColumn(
                    "Pavilion"
                ),

                "stand":
                st.column_config.TextColumn(
                    "Stand"
                ),

                "ifema_status":
                st.column_config.TextColumn(
                    "IFEMA status"
                ),

                "selected":
                st.column_config.CheckboxColumn(
                    "Already selected"
                ),

                "priority":
                st.column_config.TextColumn(
                    "Priority"
                ),

                "website":
                st.column_config.LinkColumn(
                    "Website"
                ),

                "nuveen_score":
                st.column_config.NumberColumn(
                    "Nuveen relevance"
                ),

                "company_key": None
            }
        )
    )

    selected_to_add = (
        edited_exhibitors[
            edited_exhibitors["add"]
            == True
        ]
        .copy()
    )

    if not selected_to_add.empty:

        st.info(
            f"{len(selected_to_add)} "
            f"company / companies selected."
        )

        with st.expander(
            "⭐ Add selected companies "
            "to Nuveen shortlist",
            expanded=True
        ):

            add_password = (
                st.text_input(
                    "Editing password",
                    type="password",
                    key=(
                        "all_exhibitors_password"
                    )
                )
            )

            default_priority = (
                st.selectbox(
                    "Initial priority",
                    [
                        "High",
                        "Medium",
                        "Low"
                    ],
                    index=1,
                    key="bulk_priority"
                )
            )

            if st.button(
                "⭐ Add selected to shortlist",
                type="primary",
                key="add_from_all"
            ):

                if (
                    add_password
                    != EDIT_PASSWORD
                    or not EDIT_PASSWORD
                ):

                    st.error(
                        "Incorrect editing "
                        "password."
                    )

                else:

                    existing_keys = set(
                        targets[
                            "company_key"
                        ]
                    )

                    ranks = (
                        pd.to_numeric(
                            targets["rank"],
                            errors="coerce"
                        )
                    )

                    if (
                        ranks
                        .notna()
                        .any()
                    ):

                        next_rank = (
                            int(
                                ranks.max()
                            )
                            + 1
                        )

                    else:

                        next_rank = 1

                    new_rows = []

                    for _, row in (
                        selected_to_add
                        .iterrows()
                    ):

                        key = (
                            row[
                                "company_key"
                            ]
                        )

                        if key in existing_keys:
                            continue

                        new_rows.append({
                            "company":
                                row["company"],
                            "rank":
                                str(next_rank),
                            "priority":
                                default_priority,
                            "type":
                                "",
                            "sector":
                                "",
                            "why_interesting":
                                "",
                            "confirmed_hall":
                                "",
                            "confirmed_stand":
                                "",
                            "event_info":
                                "",
                            "contact":
                                "",
                            "meeting_date":
                                "",
                            "meeting_time":
                                "",
                            "visited":
                                "No",
                            "notes":
                                ""
                        })

                        next_rank += 1

                        existing_keys.add(
                            key
                        )

                    if not new_rows:

                        st.warning(
                            "The selected "
                            "companies are already "
                            "in the shortlist."
                        )

                    else:

                        updated = (
                            pd.concat(
                                [
                                    targets.drop(
                                        columns=[
                                            "company_key"
                                        ],
                                        errors=(
                                            "ignore"
                                        )
                                    ),
                                    pd.DataFrame(
                                        new_rows
                                    )
                                ],
                                ignore_index=True
                            )
                        )

                        success, message = (
                            save_to_github(
                                updated
                            )
                        )

                        if success:

                            st.success(
                                f"{len(new_rows)} "
                                f"company / companies "
                                f"added."
                            )

                            st.cache_data.clear()
                            st.rerun()

                        else:

                            st.error(
                                message
                            )

# ============================================================
# TAB 3 — BY PAVILION
# ============================================================

with tab3:

    st.subheader(
        "Shortlist by pavilion"
    )

    selected_ifema = (
        ifema[
            ifema["selected"]
        ]
        .copy()
    )

    if selected_ifema.empty:

        st.info(
            "No shortlist companies "
            "matched to IFEMA."
        )

    else:

        pavilion_values = {
            clean_text(x)
            for x
            in selected_ifema[
                "pavilion"
            ]
        }

        pavilion_options = sorted(
            pavilion_values,
            key=pavilion_sort_key
        )

        for pavilion in (
            pavilion_options
        ):

            pavilion_label = (
                pavilion
                if pavilion
                else "TBC"
            )

            st.markdown(
                f"## 📍 Pavilion "
                f"{pavilion_label}"
            )

            pavilion_df = (
                selected_ifema[
                    selected_ifema[
                        "pavilion"
                    ]
                    == pavilion
                ]
                .copy()
            )

            pavilion_df[
                "_rank"
            ] = pd.to_numeric(
                pavilion_df["rank"],
                errors="coerce"
            ).fillna(999)

            pavilion_df = (
                pavilion_df
                .sort_values(
                    [
                        "_rank",
                        "company"
                    ]
                )
            )

            for _, row in (
                pavilion_df
                .iterrows()
            ):

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
# TAB 4 — MEETINGS
# ============================================================

with tab4:

    st.subheader(
        "Meetings"
    )

    with st.expander(
        "➕ Add meeting",
        expanded=True
    ):

        shortlist_companies = (
            targets
            .sort_values(
                "company"
            )[
                "company"
            ]
            .tolist()
        )

        with st.form(
            "add_meeting_form"
        ):

            meeting_company = (
                st.selectbox(
                    "Company",
                    shortlist_companies
                )
            )

            m1, m2 = (
                st.columns(2)
            )

            meeting_date = (
                m1.date_input(
                    "Date"
                )
            )

            meeting_time = (
                m2.time_input(
                    "Time"
                )
            )

            meeting_contact = (
                st.text_input(
                    "Contact"
                )
            )

            meeting_notes = (
                st.text_area(
                    "Notes",
                    placeholder=(
                        "Topics to discuss, "
                        "meeting point..."
                    )
                )
            )

            submit_meeting = (
                st.form_submit_button(
                    "💾 Save meeting",
                    type="primary"
                )
            )

        if submit_meeting:

            updated = (
                targets.copy()
            )

            mask = (
                updated["company"]
                == meeting_company
            )

            updated.loc[
                mask,
                "meeting_date"
            ] = meeting_date.strftime(
                "%d %b %Y"
            )

            updated.loc[
                mask,
                "meeting_time"
            ] = meeting_time.strftime(
                "%H:%M"
            )

            updated.loc[
                mask,
                "contact"
            ] = meeting_contact

            updated.loc[
                mask,
                "notes"
            ] = meeting_notes

            success, message = (
                save_to_github(
                    updated
                )
            )

            if success:

                st.success(
                    "Meeting saved."
                )

                st.cache_data.clear()
                st.rerun()

            else:

                st.error(
                    message
                )

    st.divider()

    meetings = (
        targets[
            (
                targets[
                    "meeting_date"
                ] != ""
            )
            |
            (
                targets[
                    "meeting_time"
                ] != ""
            )
        ]
        .copy()
    )

    if meetings.empty:

        st.info(
            "No meetings scheduled yet."
        )

    else:

        meetings["_rank"] = (
            pd.to_numeric(
                meetings["rank"],
                errors="coerce"
            )
            .fillna(999)
        )

        meetings = (
            meetings
            .sort_values(
                [
                    "meeting_date",
                    "meeting_time",
                    "_rank"
                ]
            )
        )

        for _, row in (
            meetings.iterrows()
        ):

            with st.container(
                border=True
            ):

                st.markdown(
                    f"### 🤝 "
                    f"{row['company']}"
                )

                st.markdown(
                    f"**📅 "
                    f"{row['meeting_date']} "
                    f"· 🕐 "
                    f"{row['meeting_time']}**"
                )

                if row["contact"]:

                    st.write(
                        f"**Contact:** "
                        f"{row['contact']}"
                    )

                if row["notes"]:

                    st.write(
                        row["notes"]
                    )

# ============================================================
# TAB 5 — EVENTS
# ============================================================

with tab5:

    st.subheader(
        "Important events & talks"
    )

    st.info(
        "The full official 2026 conference "
        "programme has not yet been published. "
        "Confirmed events are shown below and "
        "TBC items are clearly marked."
    )

    relevance_order = {
        "High": 1,
        "Medium": 2,
        "Low": 3
    }

    event_df = pd.DataFrame(
        IMPORTANT_EVENTS
    )

    event_df["_sort"] = (
        event_df[
            "relevance"
        ]
        .map(
            relevance_order
        )
        .fillna(99)
    )

    event_df = (
        event_df
        .sort_values(
            [
                "_sort",
                "date",
                "time"
            ]
        )
    )

    for _, event in (
        event_df.iterrows()
    ):

        with st.container(
            border=True
        ):

            st.markdown(
                f"### 🎤 "
                f"{event['title']}"
            )

            c1, c2 = (
                st.columns(
                    [3, 1]
                )
            )

            with c1:

                st.markdown(
                    f"📅 **"
                    f"{event['date']} "
                    f"· {event['time']}**"
                )

                st.write(
                    f"📍 "
                    f"{event['location']}"
                )

                st.write(
                    event[
                        "description"
                    ]
                )

                st.caption(
                    f"Source: "
                    f"{event['source']}"
                )

            with c2:

                st.write(
                    f"**Relevance:** "
                    f"{event['relevance']}"
                )

                if (
                    event["status"]
                    == "Confirmed"
                ):

                    st.success(
                        "Confirmed"
                    )

                else:

                    st.warning(
                        event["status"]
                    )

    st.divider()

    st.markdown(
        f"🔗 [Open official IFEMA "
        f"programme]"
        f"({IFEMA_PROGRAM_URL})"
    )

# ============================================================
# TAB 6 — MANAGE SHORTLIST
# ============================================================

with tab6:

    st.subheader(
        "Manage Nuveen shortlist"
    )

    password = (
        st.text_input(
            "Editing password",
            type="password",
            key="manage_password"
        )
    )

    if (
        password
        == EDIT_PASSWORD
        and EDIT_PASSWORD
    ):

        st.success(
            "Editing enabled"
        )

        editable = (
            targets.drop(
                columns=[
                    "company_key"
                ],
                errors="ignore"
            )
            .copy()
        )

        editable[
            "_rank_sort"
        ] = pd.to_numeric(
            editable["rank"],
            errors="coerce"
        ).fillna(999)

        editable = (
            editable
            .sort_values(
                [
                    "_rank_sort",
                    "company"
                ]
            )
            .drop(
                columns=[
                    "_rank_sort"
                ]
            )
        )

        edited = (
            st.data_editor(
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

                    "why_interesting":
                    st.column_config.TextColumn(
                        "Why relevant",
                        width="large"
                    ),

                    "notes":
                    st.column_config.TextColumn(
                        "Notes",
                        width="large"
                    )
                }
            )
        )

        if st.button(
            "💾 Save shortlist changes",
            type="primary",
            key="save_manage"
        ):

            success, message = (
                save_to_github(
                    edited
                )
            )

            if success:

                st.success(
                    "Shortlist saved."
                )

                st.cache_data.clear()
                st.rerun()

            else:

                st.error(
                    message
                )

    elif password:

        st.error(
            "Incorrect password."
        )

# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "IFEMA catalogue re-checked hourly "
    "while the application is active · "
    f"Session refreshed "
    f"{datetime.now().strftime('%d %b %Y %H:%M')}"
)
