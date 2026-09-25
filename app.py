import streamlit as st
import pandas as pd
import requests
import base64
import re
from datetime import datetime
from openai import OpenAI


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Fruit Attraction 2026 | Iberia Team",
    page_icon="🌱",
    layout="wide",
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

OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", "")

EXCLUDED_SHORTLIST_KEYWORDS = [
    "agrimarba",
    "hsbc",
]


# ============================================================
# EVENTS
# ============================================================

IMPORTANT_EVENTS = [
    {
        "date": "07 Oct 2026",
        "time": "16:30–19:30",
        "title": "Blueberry World Forum & Cocktail",
        "location": "Retiro Lounge · IFEMA Madrid",
        "category": "Berries",
        "relevance": "High",
        "status": "Confirmed",
        "description": (
            "International blueberry industry forum and networking event. "
            "Relevant for berry growers, operators, genetics and investors."
        ),
    },
    {
        "date": "6–8 Oct 2026",
        "time": "TBC",
        "title": "Factoría Chef",
        "location": "IFEMA Madrid · location TBC",
        "category": "Fresh Produce",
        "relevance": "Medium",
        "status": "Schedule pending",
        "description": (
            "Fruit Attraction product-presentation and gastronomy programme."
        ),
    },
    {
        "date": "6–8 Oct 2026",
        "time": "TBC",
        "title": "Official conferences & technical sessions",
        "location": "IFEMA Madrid",
        "category": "Industry",
        "relevance": "High",
        "status": "Programme TBC",
        "description": (
            "Industry forums, technical sessions, seminars and conferences. "
            "Detailed 2026 programme still pending."
        ),
    },
]


# ============================================================
# RESPONSIVE STYLE
# ============================================================

st.markdown(
    """
<style>

.block-container {
    padding-top: 0.8rem !important;
    padding-bottom: 2rem !important;
    max-width: 1400px !important;
}

/* Header */

.fa-title {
    font-size: 38px;
    line-height: 1.08;
    font-weight: 750;
    color: #282c3a;
    margin: 0 0 7px 0;
}

.fa-subtitle {
    font-size: 14px;
    color: #7a7f8a;
    margin-bottom: 18px;
}

/* Native metric cards */

div[data-testid="stMetric"] {
    border: 1px solid #e2e5e9 !important;
    border-radius: 12px !important;
    padding: 13px !important;
    background: white;
}

/* Tabs */

div[data-baseweb="tab-list"] {
    overflow-x: auto !important;
    flex-wrap: nowrap !important;
    scrollbar-width: none;
}

div[data-baseweb="tab-list"]::-webkit-scrollbar {
    display: none;
}

button[data-baseweb="tab"] {
    white-space: nowrap !important;
}

/* Buttons */

.stButton > button {
    border-radius: 10px;
}

/* MOBILE */

@media (max-width: 768px) {

    .block-container {
        padding-top: 0.4rem !important;
        padding-left: 0.65rem !important;
        padding-right: 0.65rem !important;
    }

    .fa-title {
        font-size: 25px !important;
        line-height: 1.1 !important;
        margin-bottom: 5px !important;
    }

    .fa-subtitle {
        font-size: 11px !important;
        line-height: 1.25 !important;
        margin-bottom: 11px !important;
    }

    div[data-testid="stMetric"] {
        padding: 8px !important;
        min-height: 80px !important;
    }

    div[data-testid="stMetricLabel"] p {
        font-size: 10px !important;
    }

    div[data-testid="stMetricValue"] {
        font-size: 22px !important;
    }

    button[data-baseweb="tab"] {
        padding-left: 7px !important;
        padding-right: 7px !important;
        font-size: 11px !important;
    }

    .stButton > button {
        width: 100%;
        min-height: 43px;
    }

    h2 {
        font-size: 22px !important;
    }

    h3 {
        font-size: 18px !important;
    }
}

</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# HELPERS
# ============================================================

def clean_text(value):
    return "" if value is None else str(value).strip()


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
        "&": "and",
    }

    for old, new in replacements.items():
        value = value.replace(old, new)

    value = re.sub(
        r"[^a-z0-9]+",
        " ",
        value
    )

    return " ".join(value.split())


def is_excluded_from_shortlist(company):

    key = normalise_name(company)

    return any(
        normalise_name(word) in key
        for word in EXCLUDED_SHORTLIST_KEYWORDS
    )


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
        "notes": "",
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


def reorder_shortlist(df, company, new_position):

    work = df.copy()

    work["_rank_num"] = (
        pd.to_numeric(
            work["rank"],
            errors="coerce"
        )
        .fillna(999)
    )

    work = (
        work
        .sort_values(
            ["_rank_num", "company"]
        )
        .reset_index(drop=True)
    )

    moving = work[
        work["company"] == company
    ].copy()

    remaining = work[
        work["company"] != company
    ].copy()

    if moving.empty:
        return df

    position = max(
        0,
        min(
            int(new_position) - 1,
            len(work) - 1
        )
    )

    reordered = pd.concat(
        [
            remaining.iloc[:position],
            moving,
            remaining.iloc[position:]
        ],
        ignore_index=True
    )

    reordered["rank"] = [
        str(i + 1)
        for i in range(len(reordered))
    ]

    return reordered.drop(
        columns=["_rank_num"],
        errors="ignore"
    )


# ============================================================
# IFEMA
# ============================================================

@st.cache_data(ttl=3600)
def load_ifema():

    payload = {
        "page": 0,
        "pageSize": 10000,
        "search": "",
        "dynamicFields": [],
        "countryIds": [],
        "categoryIds": [],
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
                    "company_key":
                        normalise_name(company),

                    "website": website,

                    "pavilion":
                        clean_text(
                            stand.get("location")
                        ),

                    "stand":
                        clean_text(
                            stand.get("name")
                        ),

                    "ifema_status":
                        "Confirmed by IFEMA",

                    "ifema_id":
                        exhibitor_id,
                })

        else:

            rows.append({
                "company": company,
                "company_key":
                    normalise_name(company),

                "website": website,
                "pavilion": "",
                "stand": "",

                "ifema_status":
                    "Stand not yet published",

                "ifema_id":
                    exhibitor_id,
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
                "ifema_id",
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
# SHORTLIST
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

    # Agrimarba + HSBC stay out of shortlist.
    df = df[
        ~df["company"]
        .apply(
            is_excluded_from_shortlist
        )
    ].copy()

    default_rank = {
        "hortifrut": 1,
        "citri and co": 2,
        "climate asset management": 3,
        "surexport": 4,
        "alcoaxarquia": 5,
        "veolia agricultura": 6,
        "fall creek": 7,
        "planasa": 8,
        "agq labs": 9,
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

        for name, rank in default_rank.items():

            if normalise_name(name) in key:
                return str(rank)

        return "99"

    df["rank"] = df.apply(
        assign_rank,
        axis=1
    )

    return df


# ============================================================
# SAVE GITHUB
# ============================================================

def save_to_github(dataframe):

    if not GITHUB_TOKEN:

        return (
            False,
            "GITHUB_TOKEN missing in Streamlit Secrets."
        )

    dataframe = dataframe.copy()

    dataframe = dataframe[
        ~dataframe["company"]
        .apply(
            is_excluded_from_shortlist
        )
    ].copy()

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
        "Authorization":
            f"Bearer {GITHUB_TOKEN}",

        "Accept":
            "application/vnd.github+json",
    }

    current = requests.get(
        url,
        headers=headers,
        timeout=20
    )

    if current.status_code != 200:

        return (
            False,
            f"GitHub read error "
            f"{current.status_code}"
        )

    sha = current.json()["sha"]

    encoded = (
        base64.b64encode(
            csv_content.encode("utf-8")
        )
        .decode("utf-8")
    )

    payload = {
        "message":
            "Update Fruit Attraction dashboard",

        "content":
            encoded,

        "sha":
            sha,
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

    return (
        False,
        f"GitHub save error "
        f"{response.status_code}"
    )


# ============================================================
# RELEVANCE
# ============================================================

def calculate_relevance(
    company,
    website=""
):

    text = (
        clean_text(company)
        + " "
        + clean_text(website)
    ).lower()

    score = 0

    strategic = [
        "hortifrut",
        "citri",
        "alcoaxarquia",
        "climate asset",
        "surexport",
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
        "olive",
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
        "vivero",
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
        "Could not connect to IFEMA."
    )

    st.code(str(error))

    st.stop()


targets = load_targets()

targets["company_key"] = (
    targets["company"]
    .apply(normalise_name)
)


# ============================================================
# MERGE DATA
# ============================================================

target_lookup = (
    targets
    .drop_duplicates("company_key")
    .set_index("company_key")
    .to_dict("index")
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
        .get(
            "priority",
            ""
        )
    )
)

ifema["rank"] = (
    ifema["company_key"]
    .apply(
        lambda key:
        target_lookup
        .get(key, {})
        .get(
            "rank",
            ""
        )
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

ifema.loc[
    ifema["selected"],
    "nuveen_score"
] += 100

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
    """
<div class="fa-title">
🌱 Fruit Attraction 2026
</div>

<div class="fa-subtitle">
Iberia Team · IFEMA Madrid · 6–8 October 2026
</div>
""",
    unsafe_allow_html=True,
)

meetings_count = len(
    targets[
        (
            targets["meeting_date"] != ""
        )
        |
        (
            targets["meeting_time"] != ""
        )
    ]
)

high_priority_count = len(
    targets[
        targets["priority"]
        == "High"
    ]
)

# Keep 2×2 always.
r1c1, r1c2 = st.columns(2)

with r1c1:

    st.metric(
        "IFEMA exhibitors",
        f"{ifema_total:,}",
        border=True
    )

with r1c2:

    st.metric(
        "Iberia shortlist",
        len(targets),
        border=True
    )

r2c1, r2c2 = st.columns(2)

with r2c1:

    st.metric(
        "High priority",
        high_priority_count,
        border=True
    )

with r2c2:

    st.metric(
        "Meetings",
        meetings_count,
        border=True
    )

st.caption(
    "IFEMA catalogue checked hourly while the app is active."
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
    tab6,
    tab7
) = st.tabs(
    [
        "⭐ Shortlist",
        "🌍 Exhibitors",
        "📍 Pavilion",
        "📅 Meetings",
        "🎤 Events",
        "🤖 Assistant",
        "✏️ Manage",
    ]
)


# ============================================================
# TAB 1 — SHORTLIST
# ============================================================

with tab1:

    st.subheader(
        "Iberia priority companies"
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
                or "TBC"
            )

            stand = (
                match["stand"]
                or "TBC"
            )

            website = (
                match["website"]
            )

            confirmed = bool(
                match["stand"]
            )

        else:

            pavilion = "TBC"
            stand = "TBC"
            website = ""
            confirmed = False

        with st.container(
            border=True
        ):

            st.markdown(
                f"### #{target['rank']} · "
                f"{target['company']}"
            )

            st.caption(
                f"{target['sector'] or 'Sector TBC'}"
                f" · Priority "
                f"{target['priority']}"
            )

            st.markdown(
                f"📍 **{pavilion} · "
                f"Stand {stand}**"
            )

            if confirmed:

                st.success(
                    "Confirmed by IFEMA",
                    icon="✅"
                )

            else:

                st.warning(
                    "Location pending IFEMA",
                    icon="⏳"
                )

            if target["why_interesting"]:

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


# ============================================================
# TAB 2 — EXHIBITORS
# ============================================================

with tab2:

    st.subheader(
        f"All IFEMA exhibitors "
        f"({ifema_total:,})"
    )

    search = st.text_input(
        "Search exhibitor",
        placeholder=(
            "Hortifrut, Surexport, "
            "avocado..."
        )
    )

    pavilion_options = sorted(
        {
            clean_text(x)
            for x in ifema[
                "pavilion"
            ]
            if clean_text(x)
        },
        key=pavilion_sort_key
    )

    pavilion_filter = (
        st.multiselect(
            "Pavilion",
            pavilion_options
        )
    )

    all_view = ifema.copy()

    if search:

        all_view = all_view[
            all_view["company"]
            .str.contains(
                search,
                case=False,
                na=False,
                regex=False
            )
        ]

    if pavilion_filter:

        all_view = all_view[
            all_view["pavilion"]
            .isin(
                pavilion_filter
            )
        ]

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
        .drop_duplicates(
            "company_key"
        )
    )

    priority_to_add = (
        st.selectbox(
            "Priority when adding",
            [
                "High",
                "Medium",
                "Low"
            ],
            index=1
        )
    )

    st.caption(
        f"{len(all_view)} result(s). "
        f"Showing first 50."
    )

    for _, row in (
        all_view
        .head(50)
        .iterrows()
    ):

        with st.container(
            border=True
        ):

            st.markdown(
                f"### {row['company']}"
            )

            st.write(
                f"📍 **"
                f"{row['pavilion'] or 'TBC'} "
                f"· Stand "
                f"{row['stand'] or 'TBC'}"
                f"**"
            )

            st.caption(
                row["ifema_status"]
            )

            if row["website"]:

                st.markdown(
                    f"[Website]"
                    f"({row['website']})"
                )

            if row["selected"]:

                st.success(
                    "Already in shortlist"
                )

            elif not (
                is_excluded_from_shortlist(
                    row["company"]
                )
            ):

                if st.button(
                    "⭐ Add to shortlist",
                    key=(
                        "add_"
                        + row["company_key"]
                    ),
                    use_container_width=True
                ):

                    ranks = (
                        pd.to_numeric(
                            targets["rank"],
                            errors="coerce"
                        )
                    )

                    next_rank = (
                        int(
                            ranks.max()
                        ) + 1
                        if ranks.notna().any()
                        else 1
                    )

                    new_row = {
                        "company":
                            row["company"],

                        "rank":
                            str(next_rank),

                        "priority":
                            priority_to_add,

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
                        "notes": "",
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

                        st.cache_data.clear()
                        st.rerun()

                    else:

                        st.error(message)


# ============================================================
# TAB 3 — PAVILION
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

    pavilion_values = sorted(
        {
            clean_text(x)
            for x in selected_ifema[
                "pavilion"
            ]
        },
        key=pavilion_sort_key
    )

    for pavilion in pavilion_values:

        st.markdown(
            f"## 📍 {pavilion or 'TBC'}"
        )

        pv = selected_ifema[
            selected_ifema[
                "pavilion"
            ] == pavilion
        ].copy()

        pv["_rank"] = (
            pd.to_numeric(
                pv["rank"],
                errors="coerce"
            )
            .fillna(999)
        )

        pv = pv.sort_values(
            ["_rank", "company"]
        )

        for _, row in pv.iterrows():

            st.write(
                f"**#{row['rank']} · "
                f"{row['company']}** "
                f"— {row['stand'] or 'TBC'}"
            )


# ============================================================
# TAB 4 — MEETINGS
# ============================================================

with tab4:

    st.subheader(
        "Meetings"
    )

    with st.expander(
        "➕ Add / update meeting",
        expanded=True
    ):

        companies = (
            targets
            .sort_values(
                "company"
            )[
                "company"
            ]
            .tolist()
        )

        if companies:

            with st.form(
                "meeting_form"
            ):

                company = (
                    st.selectbox(
                        "Company",
                        companies
                    )
                )

                date = (
                    st.date_input(
                        "Date"
                    )
                )

                time = (
                    st.time_input(
                        "Time"
                    )
                )

                contact = (
                    st.text_input(
                        "Contact"
                    )
                )

                notes = (
                    st.text_area(
                        "Notes"
                    )
                )

                submitted = (
                    st.form_submit_button(
                        "💾 Save meeting",
                        type="primary"
                    )
                )

            if submitted:

                updated = (
                    targets.copy()
                )

                mask = (
                    updated["company"]
                    == company
                )

                updated.loc[
                    mask,
                    "meeting_date"
                ] = date.strftime(
                    "%d %b %Y"
                )

                updated.loc[
                    mask,
                    "meeting_time"
                ] = time.strftime(
                    "%H:%M"
                )

                updated.loc[
                    mask,
                    "contact"
                ] = contact

                updated.loc[
                    mask,
                    "notes"
                ] = notes

                success, message = (
                    save_to_github(
                        updated
                    )
                )

                if success:

                    st.cache_data.clear()
                    st.rerun()

                else:

                    st.error(message)

    meetings = targets[
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

    if meetings.empty:

        st.info(
            "No meetings scheduled."
        )

    for _, row in meetings.iterrows():

        with st.container(
            border=True
        ):

            st.markdown(
                f"### 🤝 {row['company']}"
            )

            st.write(
                f"📅 **"
                f"{row['meeting_date']} · "
                f"{row['meeting_time']}**"
            )

            if row["contact"]:

                st.write(
                    f"Contact: "
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
        "TBC means IFEMA has not "
        "published the detail yet."
    )

    events = pd.DataFrame(
        IMPORTANT_EVENTS
    )

    for _, event in (
        events.iterrows()
    ):

        with st.container(
            border=True
        ):

            st.markdown(
                f"### 🎤 "
                f"{event['title']}"
            )

            st.write(
                f"📅 **"
                f"{event['date']} "
                f"· {event['time']}**"
            )

            st.write(
                f"📍 {event['location']}"
            )

            st.write(
                event["description"]
            )

            st.caption(
                f"Relevance: "
                f"{event['relevance']}"
            )

    st.markdown(
        f"[Official IFEMA programme]"
        f"({IFEMA_PROGRAM_URL})"
    )


# ============================================================
# ASSISTANT HELPERS
# ============================================================

def build_assistant_context(
    question
):

    question_norm = (
        normalise_name(
            question
        )
    )

    words = [
        w
        for w in question_norm.split()
        if len(w) >= 3
    ]

    # Shortlist context
    shortlist_lines = []

    ranked_targets = (
        targets.copy()
    )

    ranked_targets["_rank"] = (
        pd.to_numeric(
            ranked_targets["rank"],
            errors="coerce"
        )
        .fillna(999)
    )

    ranked_targets = (
        ranked_targets
        .sort_values("_rank")
    )

    for _, row in (
        ranked_targets.iterrows()
    ):

        matched = ifema[
            ifema["company_key"]
            == row["company_key"]
        ]

        pavilion = "TBC"
        stand = "TBC"

        if not matched.empty:

            pavilion = (
                matched.iloc[0][
                    "pavilion"
                ]
                or "TBC"
            )

            stand = (
                matched.iloc[0][
                    "stand"
                ]
                or "TBC"
            )

        shortlist_lines.append(
            f"- #{row['rank']} "
            f"{row['company']} | "
            f"Priority {row['priority']} | "
            f"{pavilion} | "
            f"Stand {stand} | "
            f"Sector {row['sector']} | "
            f"Why relevant: "
            f"{row['why_interesting']}"
        )

    # Relevant exhibitor matches
    exhibitor_matches = (
        ifema.copy()
    )

    if words:

        mask = pd.Series(
            False,
            index=exhibitor_matches.index
        )

        for word in words:

            mask = (
                mask
                |
                exhibitor_matches[
                    "company"
                ]
                .str.lower()
                .str.contains(
                    word,
                    na=False,
                    regex=False
                )
            )

        matched_exhibitors = (
            exhibitor_matches[
                mask
            ]
            .drop_duplicates(
                "company_key"
            )
            .head(25)
        )

    else:

        matched_exhibitors = (
            exhibitor_matches
            .head(15)
        )

    exhibitor_lines = []

    for _, row in (
        matched_exhibitors.iterrows()
    ):

        exhibitor_lines.append(
            f"- {row['company']} | "
            f"{row['pavilion'] or 'TBC'} | "
            f"Stand {row['stand'] or 'TBC'} | "
            f"Website {row['website'] or 'N/A'}"
        )

    # Meetings
    meeting_lines = []

    meetings = targets[
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

    for _, row in meetings.iterrows():

        meeting_lines.append(
            f"- {row['company']} | "
            f"{row['meeting_date']} "
            f"{row['meeting_time']} | "
            f"Contact {row['contact']} | "
            f"Notes {row['notes']}"
        )

    # Events
    event_lines = []

    for event in IMPORTANT_EVENTS:

        event_lines.append(
            f"- {event['title']} | "
            f"{event['date']} | "
            f"{event['time']} | "
            f"{event['location']} | "
            f"{event['status']}"
        )

    return f"""
FRUIT ATTRACTION 2026 INTERNAL DASHBOARD DATA

Shortlist:
{chr(10).join(shortlist_lines)}

Relevant IFEMA exhibitors for this question:
{chr(10).join(exhibitor_lines) if exhibitor_lines else "No direct catalogue match."}

Meetings:
{chr(10).join(meeting_lines) if meeting_lines else "No meetings scheduled."}

Events:
{chr(10).join(event_lines)}

Important:
- IFEMA catalogue data is the authoritative source for pavilion and stand in this dashboard.
- If a stand says TBC, say IFEMA has not published it yet.
- Do not invent meetings, stands or event times.
"""


def ask_assistant(question):

    if not OPENAI_API_KEY:

        return (
            "The assistant is not configured yet. "
            "Add OPENAI_API_KEY to Streamlit Secrets."
        )

    client = OpenAI(
        api_key=OPENAI_API_KEY
    )

    context = build_assistant_context(
        question
    )

    prompt = f"""
You are the Fruit Attraction 2026 assistant for an Iberia agricultural
investment team.

Your job is to help prepare for and navigate Fruit Attraction.

Use the internal dashboard data below first. You may use web search for
current external information about companies, people, news, strategies,
ownership, crops, operating footprint, partnerships or other useful context.

Rules:
1. For pavilion and stand, prefer the IFEMA dashboard data provided below.
2. Clearly say when IFEMA has not yet published something.
3. Never invent a stand, meeting, event time or person.
4. For web-derived claims, cite the web sources available to you.
5. Keep answers practical and concise.
6. If the user asks what to visit nearby, group suggestions by pavilion.
7. If the user asks about a company, explain why it may be relevant to an
   institutional agricultural / natural-capital investor.
8. Distinguish:
   - IFEMA data
   - Team data
   - External web research
9. Respond in the same language as the user's question.

INTERNAL DATA:
{context}

USER QUESTION:
{question}
"""

    response = client.responses.create(
        model="gpt-5.6-luna",
        reasoning={
            "effort": "low"
        },
        tools=[
            {
                "type":
                    "web_search",

                "search_context_size":
                    "low",
            }
        ],
        tool_choice="auto",
        input=prompt,
    )

    return response.output_text


# ============================================================
# TAB 6 — ASSISTANT
# ============================================================

with tab6:

    st.subheader(
        "🤖 Fruit Attraction Assistant"
    )

    st.caption(
        "Ask about exhibitors, stands, "
        "pavilions, meetings, events or "
        "request current web research."
    )

    if not OPENAI_API_KEY:

        st.warning(
            "Assistant not activated yet. "
            "Add OPENAI_API_KEY in "
            "Streamlit Secrets."
        )

    else:

        quick1, quick2 = st.columns(2)

        if quick1.button(
            "📍 What should I visit in Pavilion 9?",
            use_container_width=True
        ):

            st.session_state[
                "assistant_prefill"
            ] = (
                "¿Qué empresas de mi shortlist "
                "y otras empresas relevantes "
                "debería visitar en el pabellón 9?"
            )

        if quick2.button(
            "📅 Show my meetings",
            use_container_width=True
        ):

            st.session_state[
                "assistant_prefill"
            ] = (
                "¿Qué reuniones tengo y "
                "cómo debería organizarme?"
            )

        if (
            "assistant_messages"
            not in st.session_state
        ):

            st.session_state[
                "assistant_messages"
            ] = []

        for message in (
            st.session_state[
                "assistant_messages"
            ]
        ):

            with st.chat_message(
                message["role"]
            ):

                st.markdown(
                    message["content"]
                )

        default_question = (
            st.session_state.pop(
                "assistant_prefill",
                None
            )
        )

        question = st.chat_input(
            "Ask about Fruit Attraction..."
        )

        if default_question:

            question = (
                default_question
            )

        if question:

            st.session_state[
                "assistant_messages"
            ].append(
                {
                    "role":
                        "user",

                    "content":
                        question,
                }
            )

            with st.chat_message(
                "user"
            ):

                st.markdown(
                    question
                )

            with st.chat_message(
                "assistant"
            ):

                with st.spinner(
                    "Checking IFEMA data "
                    "and the web..."
                ):

                    try:

                        answer = (
                            ask_assistant(
                                question
                            )
                        )

                    except Exception as e:

                        answer = (
                            "I couldn't complete "
                            "the search. Error: "
                            f"{e}"
                        )

                st.markdown(
                    answer
                )

            st.session_state[
                "assistant_messages"
            ].append(
                {
                    "role":
                        "assistant",

                    "content":
                        answer,
                }
            )


# ============================================================
# TAB 7 — MANAGE
# ============================================================

with tab7:

    st.subheader(
        "Manage Iberia shortlist"
    )

    ordered = (
        targets.copy()
    )

    ordered["_rank_num"] = (
        pd.to_numeric(
            ordered["rank"],
            errors="coerce"
        )
        .fillna(999)
    )

    ordered = ordered.sort_values(
        [
            "_rank_num",
            "company"
        ]
    )

    st.markdown(
        "### ↕️ Quick reorder"
    )

    company_to_move = (
        st.selectbox(
            "Company",
            ordered[
                "company"
            ].tolist()
        )
    )

    current_row = ordered[
        ordered["company"]
        == company_to_move
    ]

    current_rank = 1

    if not current_row.empty:

        numeric_rank = (
            pd.to_numeric(
                current_row[
                    "rank"
                ],
                errors="coerce"
            )
            .iloc[0]
        )

        if pd.notna(
            numeric_rank
        ):

            current_rank = int(
                numeric_rank
            )

    new_position = (
        st.number_input(
            "New position",
            min_value=1,
            max_value=max(
                1,
                len(ordered)
            ),
            value=max(
                1,
                min(
                    current_rank,
                    len(ordered)
                )
            ),
            step=1
        )
    )

    if st.button(
        "↕️ Move company",
        type="primary",
        use_container_width=True
    ):

        reordered = (
            reorder_shortlist(
                targets,
                company_to_move,
                new_position
            )
        )

        success, message = (
            save_to_github(
                reordered
            )
        )

        if success:

            st.cache_data.clear()
            st.rerun()

        else:

            st.error(message)

    st.divider()

    st.markdown(
        "### ✏️ Full edit"
    )

    editable = targets.drop(
        columns=[
            "company_key"
        ],
        errors="ignore"
    ).copy()

    editable["_rank_sort"] = (
        pd.to_numeric(
            editable["rank"],
            errors="coerce"
        )
        .fillna(999)
    )

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

    edited = st.data_editor(
        editable,
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        height=500,

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
            ),
        },
    )

    if st.button(
        "💾 Save shortlist changes",
        type="primary",
        use_container_width=True
    ):

        edited["rank"] = (
            pd.to_numeric(
                edited["rank"],
                errors="coerce"
            )
            .fillna(999)
            .astype(int)
            .astype(str)
        )

        success, message = (
            save_to_github(
                edited
            )
        )

        if success:

            st.cache_data.clear()
            st.rerun()

        else:

            st.error(message)


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "IFEMA catalogue checked hourly · "
    f"Session refreshed "
    f"{datetime.now().strftime('%d %b %Y %H:%M')}"
)
