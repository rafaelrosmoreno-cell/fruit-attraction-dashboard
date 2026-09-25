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

EXCLUDED_SHORTLIST_KEYWORDS = [
    "agrimarba",
    "hsbc",
]

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

/* ---------- GENERAL ---------- */

.block-container {
    padding-top: 1rem !important;
    padding-bottom: 2rem !important;
    padding-left: 1.5rem !important;
    padding-right: 1.5rem !important;
    max-width: 1450px;
}

/* ---------- HEADER ---------- */

.fa-header {
    margin-bottom: 18px;
}

.fa-title {
    font-size: clamp(30px, 5vw, 46px);
    line-height: 1.08;
    font-weight: 750;
    margin: 0;
    padding: 0;
    color: #272b38;
}

.fa-subtitle {
    margin-top: 9px;
    font-size: 15px;
    color: #777b85;
}

/* ---------- KPI GRID ---------- */

.kpi-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 14px;
    margin-top: 20px;
    margin-bottom: 12px;
}

.kpi-card {
    border: 1px solid #e1e4e8;
    border-radius: 14px;
    padding: 16px 18px;
    background: white;
    min-width: 0;
}

.kpi-label {
    font-size: 14px;
    color: #50545d;
    margin-bottom: 5px;
}

.kpi-value {
    font-size: 34px;
    line-height: 1.1;
    font-weight: 500;
    color: #272b38;
}

.refresh-text {
    font-size: 13px;
    color: #8a8d94;
    margin-top: 10px;
}

/* ---------- OTHER STREAMLIT ---------- */

div[data-testid="stDataFrame"] {
    overflow-x: auto;
}

.stButton > button {
    border-radius: 10px;
}


/* ==========================================================
   MOBILE
   ========================================================== */

@media (max-width: 768px) {

    .block-container {
        padding-top: 0.55rem !important;
        padding-left: 0.7rem !important;
        padding-right: 0.7rem !important;
        padding-bottom: 1.5rem !important;
    }

    .fa-header {
        margin-bottom: 10px;
    }

    .fa-title {
        font-size: 29px !important;
        line-height: 1.05 !important;
        white-space: normal !important;
        word-break: normal !important;
    }

    .fa-subtitle {
        font-size: 12px;
        margin-top: 7px;
        line-height: 1.3;
    }

    .kpi-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 8px;
        margin-top: 14px;
    }

    .kpi-card {
        padding: 11px 12px;
        border-radius: 11px;
    }

    .kpi-label {
        font-size: 11px;
        line-height: 1.2;
    }

    .kpi-value {
        font-size: 25px;
    }

    .refresh-text {
        font-size: 10px;
        line-height: 1.25;
    }

    button[data-baseweb="tab"] {
        padding-left: 7px !important;
        padding-right: 7px !important;
        font-size: 11px !important;
        white-space: nowrap !important;
    }

    div[data-baseweb="tab-list"] {
        overflow-x: auto !important;
        flex-wrap: nowrap !important;
        scrollbar-width: none;
    }

    div[data-baseweb="tab-list"]::-webkit-scrollbar {
        display: none;
    }

    .stButton > button {
        width: 100%;
        min-height: 44px;
    }
}


/* Extra-small phones */

@media (max-width: 390px) {

    .fa-title {
        font-size: 26px !important;
    }

    .fa-subtitle {
        font-size: 11px;
    }

    .kpi-value {
        font-size: 23px;
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

    return " ".join(
        value.split()
    )


def is_excluded_from_shortlist(company):

    key = normalise_name(company)

    return any(
        normalise_name(word) in key
        for word in EXCLUDED_SHORTLIST_KEYWORDS
    )


def pavilion_sort_key(value):

    value = clean_text(
        value
    ).upper()

    if not value:
        return 999

    match = re.search(
        r"\d+",
        value
    )

    if match:
        return int(
            match.group()
        )

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

    return df[
        list(defaults.keys())
    ]


def reorder_shortlist(
    df,
    company,
    new_position
):

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
            [
                "_rank_num",
                "company"
            ]
        )
        .reset_index(drop=True)
    )

    moving = work[
        work["company"]
        == company
    ].copy()

    remaining = work[
        work["company"]
        != company
    ].copy()

    if moving.empty:
        return df

    position = (
        max(
            1,
            min(
                int(new_position),
                len(work)
            )
        )
        - 1
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
        for i in range(
            len(reordered)
        )
    ]

    return reordered.drop(
        columns=["_rank_num"],
        errors="ignore"
    )

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

    for exhibitor in result.get(
        "data",
        []
    ):

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
            exhibitor.get(
                "standsInfo"
            )
            or []
        )

        if stands:

            for stand in stands:

                rows.append({
                    "company":
                        company,

                    "company_key":
                        normalise_name(
                            company
                        ),

                    "website":
                        website,

                    "pavilion":
                        clean_text(
                            stand.get(
                                "location"
                            )
                        ),

                    "stand":
                        clean_text(
                            stand.get(
                                "name"
                            )
                        ),

                    "ifema_status":
                        "Confirmed by IFEMA",

                    "ifema_id":
                        exhibitor_id,
                })

        else:

            rows.append({
                "company":
                    company,

                "company_key":
                    normalise_name(
                        company
                    ),

                "website":
                    website,

                "pavilion":
                    "",

                "stand":
                    "",

                "ifema_status":
                    "Stand not yet published",

                "ifema_id":
                    exhibitor_id,
            })

    df = pd.DataFrame(
        rows
    )

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

    return (
        df,
        total_elements
    )

# ============================================================
# LOAD SHORTLIST
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

    df = ensure_target_columns(
        df
    )

    df = df[
        ~df["company"]
        .apply(
            is_excluded_from_shortlist
        )
    ].copy()

    initial_ranking = {
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

        company_key = (
            normalise_name(
                row["company"]
            )
        )

        for name, rank in (
            initial_ranking.items()
        ):

            if (
                normalise_name(name)
                in company_key
            ):
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

def save_to_github(
    dataframe
):

    if not GITHUB_TOKEN:

        return (
            False,
            "GITHUB_TOKEN is missing "
            "from Streamlit Secrets."
        )

    dataframe = (
        dataframe.copy()
    )

    dataframe = dataframe[
        ~dataframe["company"]
        .apply(
            is_excluded_from_shortlist
        )
    ].copy()

    dataframe = (
        dataframe.drop(
            columns=[
                "company_key"
            ],
            errors="ignore"
        )
    )

    dataframe = (
        ensure_target_columns(
            dataframe
        )
    )

    csv_content = (
        dataframe.to_csv(
            index=False
        )
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
            f"{current.status_code}: "
            f"{current.text}"
        )

    sha = current.json()[
        "sha"
    ]

    encoded = (
        base64.b64encode(
            csv_content.encode(
                "utf-8"
            )
        )
        .decode(
            "utf-8"
        )
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

    if response.status_code in [
        200,
        201
    ]:

        load_targets.clear()

        return (
            True,
            "Saved"
        )

    return (
        False,
        f"GitHub save error "
        f"{response.status_code}: "
        f"{response.text}"
    )

# ============================================================
# RELEVANCE ENGINE
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
        "Could not connect "
        "to the IFEMA catalogue."
    )

    st.code(
        str(error)
    )

    st.stop()


targets = load_targets()

targets["company_key"] = (
    targets["company"]
    .apply(
        normalise_name
    )
)

# ============================================================
# MERGE
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
        .get(
            key,
            {}
        )
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
        .get(
            key,
            {}
        )
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
    ifema["priority"]
    == "High",
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

st.title(
    "🌱 Fruit Attraction 2026"
)

st.caption(
    "Iberia Team · IFEMA Madrid · 6–8 October 2026"
)

meetings_count = len(
    targets[
        (
            targets[
                "meeting_date"
            ]
            != ""
        )
        |
        (
            targets[
                "meeting_time"
            ]
            != ""
        )
    ]
)

# KPI row 1
k1, k2 = st.columns(2)

k1.metric(
    "IFEMA exhibitors",
    f"{ifema_total:,}"
)

k2.metric(
    "Iberia shortlist",
    len(targets)
)

# KPI row 2
k3, k4 = st.columns(2)

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
    meetings_count
)

st.caption(
    "IFEMA exhibitor data is re-checked "
    "automatically every hour while "
    "the app is being used."
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
        "⭐ Shortlist",
        "🌍 Exhibitors",
        "📍 Pavilion",
        "📅 Meetings",
        "🎤 Events",
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
        [
            "_rank",
            "company"
        ]
    )

    for _, target in (
        view.iterrows()
    ):

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
                or "TBC"
            )

            stand = (
                match["stand"]
                or "TBC"
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

            st.markdown(
                f"### #{target['rank']} · "
                f"{target['company']}"
            )

            sector = (
                target["sector"]
                or "Sector TBC"
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

            if (
                target["visited"]
                == "Yes"
            ):

                st.caption(
                    "✅ Visited"
                )

# ============================================================
# TAB 2 — EXHIBITORS
# ============================================================

with tab2:

    st.subheader(
        f"All IFEMA exhibitors "
        f"({ifema_total:,})"
    )

    st.caption(
        "Search and add companies "
        "directly to the Iberia shortlist."
    )

    search = st.text_input(
        "Search exhibitor",
        placeholder=(
            "Hortifrut, Surexport, "
            "avocado, berries..."
        ),
        key="all_search",
    )

    pavilion_options = sorted(
        {
            clean_text(x)
            for x in ifema[
                "pavilion"
            ]
            if clean_text(x)
        },
        key=pavilion_sort_key,
    )

    f1, f2 = (
        st.columns(2)
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

    all_view = (
        ifema.copy()
    )

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

    if (
        selection_filter
        == "Selected"
    ):

        all_view = all_view[
            all_view["selected"]
        ]

    elif (
        selection_filter
        == "Not selected"
    ):

        all_view = all_view[
            ~all_view["selected"]
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

    default_priority = (
        st.selectbox(
            "Priority when adding",
            [
                "High",
                "Medium",
                "Low"
            ],
            index=1,
            key="mobile_add_priority",
        )
    )

    mobile_view = (
        st.toggle(
            "📱 Mobile-friendly cards",
            value=True
        )
    )

    if mobile_view:

        result_count = len(
            all_view
        )

        st.caption(
            f"{result_count} result(s). "
            f"Showing up to 50."
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

                location = (
                    f"{row['pavilion'] or 'TBC'} "
                    f"· "
                    f"{row['stand'] or 'TBC'}"
                )

                st.write(
                    f"📍 **{location}**"
                )

                st.caption(
                    row["ifema_status"]
                )

                if row["website"]:

                    st.markdown(
                        f"[Website]"
                        f"({row['website']})"
                    )

                st.write(
                    f"Iberia relevance: "
                    f"**"
                    f"{int(row['nuveen_score'])}"
                    f"**"
                )

                if row["selected"]:

                    st.success(
                        f"Already in shortlist "
                        f"· Priority "
                        f"{row['priority']}"
                    )

                else:

                    if (
                        is_excluded_from_shortlist(
                            row["company"]
                        )
                    ):

                        st.caption(
                            "Not included in "
                            "the working shortlist."
                        )

                    elif st.button(
                        "⭐ Add to shortlist",
                        key=(
                            "mobile_add_"
                            + row[
                                "company_key"
                            ]
                        ),
                        use_container_width=True,
                    ):

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

                        new_row = {
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
                                "",
                        }

                        updated = (
                            pd.concat(
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

                            st.error(
                                message
                            )

    else:

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
                "company_key",
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
                height=500,

                disabled=[
                    "company",
                    "pavilion",
                    "stand",
                    "ifema_status",
                    "selected",
                    "priority",
                    "website",
                    "nuveen_score",
                    "company_key",
                ],

                column_config={

                    "add":
                    st.column_config.CheckboxColumn(
                        "Add"
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
                        "Selected"
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
                        "Relevance"
                    ),

                    "company_key":
                        None,
                },
            )
        )

        selected_to_add = (
            edited_exhibitors[
                edited_exhibitors[
                    "add"
                ]
                == True
            ]
            .drop_duplicates(
                "company_key"
            )
        )

        if (
            not selected_to_add.empty
        ):

            st.success(
                f"{len(selected_to_add)} "
                f"company / companies "
                f"selected."
            )

            if st.button(
                "⭐ Add selected "
                "to shortlist",
                type="primary",
                use_container_width=True,
            ):

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

                    if (
                        key
                        in existing_keys
                        or
                        is_excluded_from_shortlist(
                            row["company"]
                        )
                    ):

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
                            "",
                    })

                    next_rank += 1

                    existing_keys.add(
                        key
                    )

                if new_rows:

                    updated = (
                        pd.concat(
                            [
                                targets.drop(
                                    columns=[
                                        "company_key"
                                    ],
                                    errors="ignore"
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

                        st.cache_data.clear()
                        st.rerun()

                    else:

                        st.error(
                            message
                        )

                else:

                    st.warning(
                        "Nothing new to add."
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
                or "TBC"
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
                pavilion_df[
                    "rank"
                ],
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
                    or "TBC"
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
        "➕ Add / update meeting",
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

        if not shortlist_companies:

            st.info(
                "Add companies to "
                "the shortlist first."
            )

        else:

            with st.form(
                "add_meeting_form"
            ):

                meeting_company = (
                    st.selectbox(
                        "Company",
                        shortlist_companies
                    )
                )

                meeting_date = (
                    st.date_input(
                        "Date"
                    )
                )

                meeting_time = (
                    st.time_input(
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
                ]
                != ""
            )
            |
            (
                targets[
                    "meeting_time"
                ]
                != ""
            )
        ]
        .copy()
    )

    if meetings.empty:

        st.info(
            "No meetings scheduled yet."
        )

    else:

        meetings = (
            meetings
            .sort_values(
                [
                    "meeting_date",
                    "meeting_time"
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

                if st.button(
                    "🗑 Remove meeting",
                    key=(
                        "remove_meeting_"
                        + row[
                            "company_key"
                        ]
                    ),
                    use_container_width=True,
                ):

                    updated = (
                        targets.copy()
                    )

                    mask = (
                        updated["company"]
                        == row["company"]
                    )

                    updated.loc[
                        mask,
                        [
                            "meeting_date",
                            "meeting_time",
                            "contact"
                        ]
                    ] = ""

                    success, message = (
                        save_to_github(
                            updated
                        )
                    )

                    if success:

                        st.cache_data.clear()
                        st.rerun()

                    else:

                        st.error(
                            message
                        )

# ============================================================
# TAB 5 — EVENTS
# ============================================================

with tab5:

    st.subheader(
        "Important events & talks"
    )

    st.info(
        "Confirmed information is "
        "shown as such. Items not yet "
        "published by IFEMA remain TBC."
    )

    event_df = (
        pd.DataFrame(
            IMPORTANT_EVENTS
        )
    )

    event_df["_sort"] = (
        event_df[
            "relevance"
        ]
        .map(
            {
                "High": 1,
                "Medium": 2,
                "Low": 3
            }
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

            st.write(
                f"**Relevance for Iberia Team:** "
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

    st.markdown(
        f"[Open official IFEMA programme]"
        f"({IFEMA_PROGRAM_URL})"
    )

# ============================================================
# TAB 6 — MANAGE
# ============================================================

with tab6:

    st.subheader(
        "Manage Iberia shortlist"
    )

    st.caption(
        "Mobile-friendly controls first; "
        "full table below."
    )

    ordered = (
        targets.copy()
    )

    ordered[
        "_rank_num"
    ] = pd.to_numeric(
        ordered["rank"],
        errors="coerce"
    ).fillna(999)

    ordered = (
        ordered
        .sort_values(
            [
                "_rank_num",
                "company"
            ]
        )
    )

    st.markdown(
        "### ↕️ Quick reorder"
    )

    company_to_move = (
        st.selectbox(
            "Company to move",
            ordered[
                "company"
            ].tolist(),
            key="reorder_company",
        )
    )

    current_rank_row = (
        ordered[
            ordered["company"]
            == company_to_move
        ]
    )

    current_rank_value = (
        pd.to_numeric(
            current_rank_row[
                "rank"
            ],
            errors="coerce"
        )
    )

    if (
        not current_rank_row.empty
        and
        pd.notna(
            current_rank_value.iloc[0]
        )
    ):

        current_rank = int(
            current_rank_value.iloc[0]
        )

    else:

        current_rank = 1

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
            step=1,
        )
    )

    if st.button(
        "↕️ Move company",
        type="primary",
        use_container_width=True,
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

            st.error(
                message
            )

    st.divider()

    st.markdown(
        "### ✏️ Full edit"
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
            height=520,

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
    )

    if st.button(
        "💾 Save shortlist changes",
        type="primary",
        use_container_width=True,
    ):

        edited[
            "rank"
        ] = (
            pd.to_numeric(
                edited["rank"],
                errors="coerce"
            )
            .fillna(999)
            .astype(int)
            .astype(str)
        )

        edited = edited[
            ~edited["company"]
            .apply(
                is_excluded_from_shortlist
            )
        ].copy()

        success, message = (
            save_to_github(
                edited
            )
        )

        if success:

            st.cache_data.clear()
            st.rerun()

        else:

            st.error(
                message
            )

# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "IFEMA catalogue re-checked hourly "
    "while the app is active · "
    f"Session refreshed "
    f"{datetime.now().strftime('%d %b %Y %H:%M')}"
)
