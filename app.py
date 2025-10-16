import streamlit as st
import pandas as pd
import random
import plotly.express as px
import time
import streamlit.components.v1 as components
import requests
import math

API_URL = st.secrets["SHEETBEST_URL"]
API_URL_STATS = "https://api.sheetbest.com/sheets/b182e0f1-84d8-41f6-9ad3-ea8473065730/tabs/Stats" 

def scroll_top():
    components.html(
        """
        <script>
        window.parent.scrollTo({top: 0, behavior: 'smooth'});
        </script>
        """,
        height=0,
    )

def save_row(role, co2_devices, co2_ewaste, co2_ai, co2_digital, co2_total):
    # restituisce numeri (float), non stringhe
    def norm_val(x):
        try:
            v = float(x)
            if abs(v) < 1e-12:
                return 0.0
            # arrotonda ma resta numero
            return round(v, 6)
        except Exception:
            return 0.0

    payload = {
        "Role": str(role or ""),
        "CO2 Devices": norm_val(co2_devices),
        "CO2 E-Waste": norm_val(co2_ewaste),
        "CO2 AI": norm_val(co2_ai),
        "CO2 Digital Activities": norm_val(co2_digital),
        "CO2 Total": norm_val(co2_total),
    }

    r = requests.post(API_URL, json=payload, timeout=10)
    r.raise_for_status()
    return r.json()

def _to_float(x):
    # Converte "310,2" o "310.2" in float, gestisce None
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).strip().replace(" ", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None

def fetch_role_stats():
    """Legge il tab 'Stats' via Sheet.best: [{'Role':'Student','AvgCO2':'297.3','Count':'42'}, ...]."""
    if not API_URL_STATS:
        return []
    r = requests.get(API_URL_STATS, timeout=10)
    r.raise_for_status()
    return r.json() or []

def get_avg_for_role_from_stats(role: str):
    """Ritorna (avg, count) per il ruolo dal tab 'Stats', oppure (None, None) se non disponibile."""
    try:
        rows = fetch_role_stats()
    except Exception:
        return None, None
    role = (role or "").strip()
    for row in rows:
        if (row.get("Role") or "").strip() == role:
            avg = _to_float(row.get("AvgCO2"))
            cnt = int(_to_float(row.get("Count")) or 0)
            return avg, cnt
    return None, None


st.set_page_config(page_title="Digital Carbon Footprint Calculator", layout="wide")

# Init session state
if "page" not in st.session_state or st.session_state.page not in ["intro", "main", "guess", "results_cards", "results_breakdown", "results_equiv", "virtues", "final"]:
    st.session_state.page = "intro"
if "role" not in st.session_state:
    st.session_state.role = ""
if "device_inputs" not in st.session_state:
    st.session_state.device_inputs = {}
if "results" not in st.session_state:
    st.session_state.results = {}
if "archetype_guess" not in st.session_state:
    st.session_state.archetype_ = None

activity_factors = {
    "Student": {
        "MS Office (e.g. Excel, Word, PPT, Outlook…)": 0.00901,
        "Technical softwares (e.g. Matlab, Python…)": 0.00901,
        "Web browsing": 0.0264,
        "Watching lecture recordings": 0.0439,
        "Online classes streaming or video call": 0.112,
        "Reading study materials on your computer (e.g. slides, articles, digital textbooks)": 0.004352
    },
    "Professor": {
        "MS Office (e.g. Excel, Word, PPT, Outlook…)": 0.00901,
        "Web browsing": 0.0264,
        "Videocall (e.g. Zoom, Teams…)": 0.112,
        "Online classes streaming": 0.112,
        "Reading materials on your computer (e.g. slides, articles, digital textbooks)": 0.004352,
        "Technical softwares (e.g. Matlab, Python…)": 0.00901
    },
    "Staff Member": {
        "MS Office (e.g. Excel, Word, PPT, Outlook…)": 0.00901,
        "Management software (e.g. SAP)": 0.00901,
        "Web browsing": 0.0264,
        "Videocall (e.g. Zoom, Teams…)": 0.112,
        "Reading materials on your computer (e.g. documents)": 0.004352
    }
}

ai_factors = {
    "Summarize texts or articles": 0.000711936,
    "Translate sentences or texts": 0.000363008,
    "Explain a concept": 0.000310784,
    "Generate quizzes or questions": 0.000539136,
    "Write formal emails or messages": 0.000107776,
    "Correct grammar or style": 0.000107776,
    "Analyze long PDF documents": 0.001412608,
    "Write or test code": 0.002337024,
    "Generate images": 0.00206,
    "Brainstorm for thesis or projects": 0.000310784,
    "Explain code step-by-step": 0.003542528,
    "Prepare lessons or presentations": 0.000539136
}

device_ef = {
    "Desktop Computer": 296,
    "Laptop Computer": 170,
    "Smartphone": 38.4,
    "Tablet": 87.1,
    "External Monitor": 235,
    "Headphones": 10.22,
    "Printer": 62.3,
    "Home Router/Modem": 106,
    "Maxi-screen": 1320,
    "Projector": 145,
    
}

eol_modifier = {
    "I bring it to a certified e-waste collection center": -0.224,
    "I throw it away in general waste": 0.611,
    "I return it to manufacturer for recycling or reuse": -0.3665,
    "I sell or donate it to someone else": -0.445,
    "I store it at home, unused": 0.402,
    "Device provided by the university, I return it after use": -0.089,
}

DEFAULT_LIFESPAN = {
    "Desktop Computer": 6,
    "Laptop Computer": 5,
    "Smartphone": 3,
    "Tablet": 4,
    "External Monitor": 8,
    "Headphones": 3,
    "Printer": 7,
    "Home Router/Modem": 8,
    "Maxi-screen": 8,
    "Projector": 8,
}


DAYS = 250  # Typical number of work/study days per year


emails = {
    "-- Select option --": 0,
    "0": 0,
    "1–10": 5,
    "11–20": 15,
    "21–30": 25,
    "31–40": 35,
    "41–80": 60, 
    "81–100": 90, 
    ">100": 150,
}
cloud_gb = {
    "-- Select option --": 0,
    "<5GB": 2.5,
    "5–20GB": 12.5,
    "20–50GB": 35,
    "50–100GB": 75,
    "100–200GB": 150,
}

ARCHETYPES = [
    {
        "key": "Devices",
        "name": "Lord of the Latest Gadgets",
        "category": "Devices",
        "image": "lord_of_the_latest_gadgets.png",   # file nella stessa cartella di app.py
    },
    {
        "key": "ai",
        "name": "Prompt Pirate, Ruler of the Queries",
        "category": "Artificial Intelligence",
        "image": "prompt_pirate.png",
    },
    {
        "key": "weee",
        "name": "Guardian of the Eternal E-Waste Pile",
        "category": "E-Waste",
        "image": "guardian_ewaste.png",
    },
    {
        "key": "activities",
        "name": "Master of Endless Streams",
        "category": "Digital Activities",
        "image": "master_endless_streams.png",
    },
]

AVERAGE_CO2_BY_ROLE = {
    "Student": 297,      
    "Professor": 323,
    "Staff Member": 309,
}

# INTRO PAGE 

def show_intro():
    scroll_top()
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }

        h1, h2, h3, h4 {
            color: #1d3557;
        }

        .intro-box {
            background: linear-gradient(to right, #d8f3dc, #a8dadc);
            padding: 40px 25px;
            border-radius: 15px;
            text-align: center;
            box-shadow: 0 4px 18px rgba(0,0,0,0.06);
            margin-bottom: 30px;
        }

        .selectbox-container {
            background-color: #f1faee;
            border-left: 5px solid #52b788;
            border-radius: 10px;
            padding: 20px;
            margin-top: 25px;
        }

        .start-button {
            margin-top: 20px;
        }
        </style>
    """, unsafe_allow_html=True)

    # --- HERO INTUITIVO
    st.markdown("""
        <div class="intro-box">
            <h1 style="font-size: 2.6em; text-align: center; margin: 0;">
                Digital Carbon Footprint Calculator📱
            </h1>
        </div>
    """, unsafe_allow_html=True)


    # --- TESTO DESCRITTIVO + LOGO A DESTRA (Streamlit columns, no <img>) ---
    col_welcome, col_logo = st.columns([8, 2])

    with col_welcome:
        st.markdown(
        f"""
        <div style="margin-top:20px;">
        Welcome to the <b>Digital Carbon Footprint Calculator</b>, a tool developed within the <i>Green DiLT project</i> to raise awareness about the hidden environmental impact of digital habits in academia.

        This calculator is tailored for <b>university students, professors, and staff members</b>, helping you estimate your CO₂e emissions from everyday digital activities, often overlooked, but increasingly relevant.
        </div>
        """,
        unsafe_allow_html=True
        )

    with col_logo:
        # Logo grande che occupa lo spazio a destra
        box = st.container()
        with box:
            st.image("logo.png", width=300)  # <-- niente <img>, funziona anche con repo privata
            st.image("logo2.png", width=300)

    st.divider()  # linea continua a tutta larghezza




    # --- SELECTBOX ---
    with st.container():
        st.session_state.role = st.selectbox(
            "What is your role in academia?",
            ["", "Student", "Professor", "Staff Member"]
        )

    # --- INPUT NOME ---
    st.session_state.name = st.text_input("What is your name?")

    # --- PRIVACY DISCLAIMER ---
    st.markdown(
        "<p style='font-size:0.85rem; color:gray; margin-top:-6px;'>"
        "The information collected will be processed exclusively for research and educational purposes, in compliance with applicable data protection regulations, and will be handled confidentially and anonymously."
        "</p>",
        unsafe_allow_html=True
    )

    
    # --- BOTTONE START ---
    st.markdown('<div class="start-button">', unsafe_allow_html=True)
    if st.button("➡️ Start Calculation"):
        if st.session_state.role and st.session_state.name.strip():
            st.session_state.page = "main"
            st.rerun()
        else:
            st.warning("⚠️ Please enter your name and select your role before continuing.")
    st.markdown('</div>', unsafe_allow_html=True)


# MAIN PAGE
def show_main():
    scroll_top()

    st.markdown("""
    <style>
    .label-with-tooltip {
        display: flex;
        align-items: center;
        gap: 6px;
    }
    .info-icon {
        display: inline-block;
        width: 22px;
        height: 22px;
        border-radius: 50%;
        background: #457b9d; /* blu elegante */
        color: #fff;
        font-weight: 700;
        font-size: 14px;
        line-height: 22px;
        text-align: center;
        cursor: default;
        position: relative;
        transition: all 0.2s ease-in-out;
        box-shadow: 0 2px 6px rgba(0,0,0,0.15);
        margin-left: 6px;
    }
    .info-icon:hover {
        background: #1d3557; /* più scuro in hover */
        box-shadow: 0 4px 10px rgba(0,0,0,0.25);
    }
    .info-icon .tooltip-text {
        visibility: hidden;
        opacity: 0;
        position: absolute;
        top: 120%;
        left: 50%;
        transform: translateX(-50%);
        background: #1d3557;
        color: #fff;
        border-radius: 10px;
        padding: 10px 12px;
        font-size: 13px;
        line-height: 1.45;
        width: 360px !important;           
        max-width: min(90vw, 420px) !important;
        white-space: normal !important;        
        word-break: break-word;               
        box-shadow: 0 8px 24px rgba(0,0,0,.15);
        transition: opacity .15s ease-in-out;
        z-index: 9999;
        text-align: left;
        font-weight: 400;
    }
    .info-icon:hover .tooltip-text {
        visibility: visible;
        opacity: 1;
    }
    .info-icon .tooltip-text::after {
        content: "";
        position: absolute;
        top: -6px;
        left: 50%;
        transform: translateX(-50%);
        border-width: 6px;
        border-style: solid;
        border-color: transparent transparent #1d3557 transparent;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div style="
        background: linear-gradient(to right, #d8f3dc, #a8dadc);
        padding: 25px 20px;
        border-radius: 12px;
        box-shadow: 0 4px 18px rgba(0,0,0,0.06);
        text-align: center;
        margin-bottom: 20px;
    ">
        <h1 style="font-size: 2.2em; color:#1d3557; margin-bottom: 0;">
            Hello <b>{st.session_state.name}</b>, it’s time to uncover the impact of your digital world! 🚀
        </h1>
    </div>
""", unsafe_allow_html=True)


    st.markdown(f"""
        <p style="font-size: 1em; color: #6c757d; margin-top: -8px;">
            First, we’ll ask you a few quick questions about your studying/working habits. This will take less than <b>5 minutes</b>.
        </p>
    """, unsafe_allow_html=True)

    st.markdown("""
    <h3 style="margin-top: 25px; color:#1d3557;">💻 Devices & E-Waste</h3>
    <p>
        Please select only the digital devices you use for <b>study or work</b>. Example: If you own a personal smartphone and a work smartphone, include <b>only the one used for study or work</b>. 
    </p>
    """, unsafe_allow_html=True)


    # --- STATE INIT ---
    if "device_list" not in st.session_state:
        st.session_state.device_list = []
    if "device_expanders" not in st.session_state:
        st.session_state.device_expanders = {}
    if "device_inputs" not in st.session_state:
        st.session_state.device_inputs = {}
    # NEW: token per expander per forzare re-mount alla conferma
    if "expander_tokens" not in st.session_state:
        st.session_state.expander_tokens = {}

    # --- Device picker più chiaro (quantità per tipo) ---
    st.markdown("""
        <style>
        .chips{margin:.25rem 0 .5rem}
        .chip{display:inline-block;background:#f1faee;border:1px solid #e6ebe9;border-radius:999px;
              padding:4px 10px;margin:4px 6px 0 0;font-size:.85rem;color:#1b4332}
        </style>
    """, unsafe_allow_html=True)

    device_emoji = {
        "Desktop Computer": "🖥️", "Laptop Computer": "💻", "Smartphone": "📱", "Tablet": "📲",
        "External Monitor": "🖥️", "Headphones": "🎧", "Printer": "🖨️", "Home Router/Modem": "🛜", "Projector": "📽️", "Maxi-screen": "📺"
    }

    st.markdown("**Set a quantity for each device you own. Then, you will then be asked a few details about how you use it and what you do when it is no longer needed.**")

    # Filtra i device in base al ruolo
    role_curr = st.session_state.get("role", "")
    if role_curr == "Student":
        # Gli studenti non vedono Maxi-screen e Projector
        types = [d for d in device_ef.keys() if d not in ["Maxi-screen", "Projector"]]
        num_cols = 4
    else:
        # Professor o Staff Member vedono tutti i device
        types = list(device_ef.keys())
        num_cols = 5

    # memorizza le quantità precedenti per rilevare cambi (no bottone)
    if "picker_prev" not in st.session_state:
        st.session_state.picker_prev = {t: 0 for t in types}
    else:
        for _t in types:
            st.session_state.picker_prev.setdefault(_t, 0)

    # reset sicuro delle qty dopo "Add selected devices"
    if st.session_state.get("_picker_reset"):
        for t in types:
            st.session_state.pop(f"picker_qty_{t}", None)
        st.session_state["_picker_reset"] = False

    # Crea il layout dinamico (4 colonne per studenti, 5 per altri)
    cols = st.columns(num_cols)
    for i, t in enumerate(types):
        with cols[i % num_cols]:
            st.markdown(f"{device_emoji.get(t, '•')} **{t}**")
            st.number_input(
                "Qty",
                min_value=0,
                max_value=10,
                value=st.session_state.picker_prev.get(t, 0),
                step=1,
                key=f"picker_qty_{t}",
                label_visibility="collapsed"
            )


    # Applica la differenza subito quando cambi i Qty (senza bottone)
    from collections import Counter

    changed_any = False
    # conteggio attuale per tipo
    current_counts = Counter(d.rsplit("_", 1)[0] for d in st.session_state.device_list)

    for t in types:
        desired = int(st.session_state.get(f"picker_qty_{t}", 0) or 0)
        prev = int(st.session_state.picker_prev.get(t, 0))
        if desired == prev:
            continue

        delta = desired - prev
        # AGGIUNGI
        if delta > 0:
            for _ in range(delta):
                # prossimo indice per quel tipo
                curr_ids = [i for i in st.session_state.device_list if i.rsplit("_", 1)[0] == t]
                next_idx = len(curr_ids)
                new_id = f"{t}_{next_idx}"
                st.session_state.device_list.insert(0, new_id)
                st.session_state.device_inputs[new_id] = {
                    "years": 1.0, "used": "-- Select --", "shared": "-- Select --", "eol": "-- Select --"
                }
                st.session_state.device_expanders[new_id] = True
                st.session_state.expander_tokens[new_id] = 0
            changed_any = True

        # RIMUOVI (prima non confermati, poi i più recenti)
        else:
            to_remove = -delta
            ids_of_type = [i for i in st.session_state.device_list if i.rsplit("_", 1)[0] == t]
            unconf = [i for i in ids_of_type if st.session_state.device_expanders.get(i, True)]
            conf   = [i for i in ids_of_type if i not in unconf]
            key_idx = lambda s: int(s.rsplit("_", 1)[1]) if "_" in s else -1
            ordered = sorted(unconf, key=key_idx, reverse=True) + sorted(conf, key=key_idx, reverse=True)
            for rid in ordered[:to_remove]:
                st.session_state.device_list.remove(rid)
                st.session_state.device_inputs.pop(rid, None)
                st.session_state.device_expanders.pop(rid, None)
                st.session_state.expander_tokens.pop(rid, None)
            changed_any = True

        # aggiorna il "precedente" per questo tipo
        st.session_state.picker_prev[t] = desired

    if changed_any:
        st.rerun()


    # Riepilogo compatto dei device già aggiunti
    from collections import Counter
    if st.session_state.device_list:
        counts = Counter(d.rsplit("_", 1)[0] for d in st.session_state.device_list)
        chips = "".join(
            f"<span class='chip'>{device_emoji.get(k, '•')} {k} × {v}</span>"
            for k, v in counts.items()
        )
        st.markdown(f"<div class='chips'>{chips}</div>", unsafe_allow_html=True)


    total_prod, total_eol = 0, 0

    for device_id in st.session_state.device_list:
        base_device = device_id.rsplit("_", 1)[0]
        prev = st.session_state.device_inputs[device_id]
        is_open = st.session_state.device_expanders.get(device_id, True)
        token = st.session_state.expander_tokens.get(device_id, 0)

        # Cambiamo l’etichetta SOLO quando vogliamo forzare la chiusura
        suffix = "" if is_open else ("\u200B" * (token + 1))
        label = f"{base_device}{suffix}"

        with st.expander(label, expanded=is_open):
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.markdown("""
                    <div style='margin-bottom:-20px'>
                        <strong>Ownership</strong><br/>
                        <span style='font-size:12px; color:gray'>Is this device used only by you or shared?</span>
                    </div>
                """, unsafe_allow_html=True)
                shared_options = ["-- Select --", "Personal", "Shared with family", "Shared in university"]
                shared_index = shared_options.index(prev["shared"]) if prev["shared"] in shared_options else 0
                shared = st.selectbox("", shared_options, index=shared_index, key=f"{device_id}_shared")

            with col2:
                st.markdown("""
                    <div style='margin-bottom:-20px'>
                        <strong>Condition</strong><br/>
                        <span style='font-size:12px; color:gray'>Was the device new or used when you got it?</span>
                    </div>
                """, unsafe_allow_html=True)
                used_options = ["-- Select --", "New", "Used"]
                used_index = used_options.index(prev["used"]) if prev["used"] in used_options else 0
                used = st.selectbox("", used_options, index=used_index, key=f"{device_id}_used")

            with col3:
                st.markdown(f"""
                    <div style='margin-bottom:-20px'>
                        <div class="label-with-tooltip">
                            <strong>Device's lifespan</strong>
                            <div class="info-icon">i
                                <div class="tooltip-text">
                                    <b>Example:</b> if you have had a phone for 2 years and expect to keep it for 3 more, enter 5. 
                                    If the device was purchased second-hand, only count your own usage period, not the years used by the previous owner.
                                </div>
                            </div>
                        </div>
                        <span style='font-size:12px; color:gray'>
                            How many years you plan to use the device in total
                        </span>
                    </div>
                """, unsafe_allow_html=True)

                # chiave di stato per il toggle "I don't know"
                idk_key = f"{device_id}_idk"
                years_key = f"{device_id}_years"
                avg_years = DEFAULT_LIFESPAN.get(base_device, 5)

                # Inizializza lo stato se non presente
                if idk_key not in st.session_state:
                    st.session_state[idk_key] = False

                # Se "I don't know" è attivo, forza il valore medio e disabilita l'input
                if st.session_state[idk_key]:
                    st.session_state[years_key] = float(avg_years)
                    years = st.number_input(
                        "",
                        0.5,
                        20.0,
                        step=0.5,
                        format="%.1f",
                        key=years_key,
                        disabled=True
                    )
                else:
                    years = st.number_input(
                        "",
                        0.5,
                        20.0,
                        step=0.5,
                        format="%.1f",
                        key=years_key
                    )

                # --- "I don't know" single-radio style toggle ---
                st.markdown("""
                    <style>
                    .radio-like input[type=checkbox] {
                        appearance: none;
                        -webkit-appearance: none;
                        width: 16px;
                        height: 16px;
                        border-radius: 50%;
                        border: 2px solid #999;
                        outline: none;
                        cursor: pointer;
                        vertical-align: middle;
                        margin-right: 6px;
                    }
                    .radio-like input[type=checkbox]:checked {
                        background-color: #6c757d;
                        border-color: #6c757d;
                    }
                    .radio-like label {
                        cursor: pointer;
                        font-size: 14px;
                    }
                    </style>
                """, unsafe_allow_html=True)


                prev_state = st.session_state.get(idk_key, False)
                is_idk = st.checkbox(
                    "I don’t know",
                    value=prev_state,
                    key=f"idk_checkbox_{device_id}",
                     help="If you select this option, the average lifespan of the device will be considered.",
                    label_visibility="visible"
                )

                if is_idk != prev_state:
                    st.session_state[idk_key] = is_idk
                    st.rerun()
                else:
                    st.session_state[idk_key] = is_idk

            
            with col4:
                st.markdown("""
                    <div style='margin-bottom:-20px'>
                        <strong>End-of-life behavior</strong><br/>
                        <span style='font-size:12px; color:gray'>What do you usually do when the device reaches its end of life?</span>
                    </div>
                """, unsafe_allow_html=True)
                role_curr = st.session_state.get("role", "")
                all_eol = list(eol_modifier.keys())
                # Filtra la nuova opzione per gli studenti
                filtered_eol = [
                    k for k in all_eol
                    if (role_curr in ["Professor", "Staff Member"]) or (k != "Device provided by the university, I return it after use")
                ]
                eol_options = ["-- Select --"] + filtered_eol               
                eol_index = eol_options.index(prev["eol"]) if prev["eol"] in eol_options else 0
                eol = st.selectbox("", eol_options, index=eol_index, key=f"{device_id}_eol")

            # --- calcoli (immutati) ---
            impact = device_ef.get(base_device, 0)
            if used == "New" and shared == "Personal":
                adj_years = years
            elif used == "Used" and shared == "Personal":
                adj_years = years + (years / 2)

            elif used == "New" and shared == "Shared with family":
                adj_years = years * 3
            elif used == "Used" and shared == "Shared with family":
                adj_years = years * 4.5

            elif used == "New" and shared == "Shared in university":
                adj_years = years * 10
            elif used == "Used" and shared == "Shared in university":
                adj_years = years * 15  # 10 * 1.5 (come proporzione coerente)

            else:
                adj_years = years


            eol_mod = eol_modifier.get(eol, 0)
            prod_per_year = impact / adj_years if adj_years else 0
            eol_impact = (impact * eol_mod) / adj_years if adj_years else 0
            total_prod += prod_per_year
            total_eol += eol_impact

            col_remove, _, col_confirm = st.columns([1, 8, 1])

            with col_remove:
                if st.button(f"🗑 Remove", key=f"remove_{device_id}"):
                    st.session_state.device_list.remove(device_id)
                    st.session_state.device_inputs.pop(device_id, None)
                    st.session_state.device_expanders.pop(device_id, None)
                    st.session_state.expander_tokens.pop(device_id, None)  # NEW
                    st.rerun()

            with col_confirm:
                confirm_key = f"confirm_{device_id}"
                if st.button("✅ Confirm", key=confirm_key):
                    if "-- Select --" in [used, shared, eol]:
                        st.warning("Please complete all fields before confirming.")
                    else:
                        st.session_state.device_inputs[device_id] = {
                            "years": years, "used": used, "shared": shared, "eol": eol
                        }
                        # Forza CHIUSURA e RE-MOUNT alla prossima esecuzione
                        st.session_state.device_expanders[device_id] = False
                        st.session_state.expander_tokens[device_id] = st.session_state.expander_tokens.get(device_id, 0) + 1
                        st.rerun()



    # === DIGITAL ACTIVITIES ===

    st.markdown("""
        <h3 style="margin-top: 25px; color:#1d3557;">🔌 Digital Activities</h3>
        <p>
            Estimate how many hours per day you spend on each activity during a typical 8-hour study or work day.
            <br>
            <b style="color: #40916c;">You may exceed 8 hours if multitasking</b> 
            <span style="color: #495057;">(e.g., watching a lecture while writing notes).</span>
        </p>
    """, unsafe_allow_html=True)

    role = st.session_state.role
    ore_dict = {}
    hours_total = 0
    col1, col2 = st.columns(2)

    # Sliders con -- Select --
    for i, (act, ef) in enumerate(activity_factors[role].items()):
        with (col1 if i % 2 == 0 else col2):
            ore = st.slider(
                f"{act} (h/day)",
                min_value=0.0,
                max_value=8.0,
                value=0.0,
                step=0.5,
                key=f"slider_{act}"
            )
            ore_dict[act] = ore

    total_hours_raw = sum(ore_dict.values())
    warn_color = "#B58900"  # giallo scuro
    color = "#6EA8FE" if total_hours_raw <= 8 else warn_color

    # Riga totale ore (con colore condizionale)
    st.markdown(
        f"<div style='text-align:right; font-size:0.9rem; color:{color}; margin-top:-6px;'>"
        f"Total: <b>{total_hours_raw:.1f}</b> h/day</div>",
        unsafe_allow_html=True
    )

    # Nota esplicativa se supera 8h
    if total_hours_raw > 8:
        st.markdown(
            "<div style='text-align:right; font-size:0.85rem; color:#B58900; margin-top:-8px;'>"
            "Overlapping activities can push the total above 8 hours.</div>",
            unsafe_allow_html=True
        )


    
    for act, ore in ore_dict.items():
        hours_total += ore * activity_factors[role][act] * DAYS
    
    # Parte 2: Email, cloud, printing, connectivity
    st.markdown("""
        <hr style="margin-top: 30px; margin-bottom: 20px;">
        <p style="font-size: 17px; line-height: 1.5;">
            Now tell us more about your habits related to <b style="color: #40916c;">email, cloud, printing and connectivity</b>.
        </p>
        <p style="font-size: 13px; color: gray; margin-top: 8px;">
            How many study or work emails do you send or receive in a typical 8-hour day? 
            Please do not count spam messages.
        </p>
    """, unsafe_allow_html=True)

    email_opts = ["-- Select option --", "0", "1–10", "11–20", "21–30", "31–40", "41–80", "81–100", ">100"]
    cloud_opts = ["-- Select option --", "<5GB", "5–20GB", "20–50GB", "50–100GB", "100–200GB"]


    email_col1, email_col2 = st.columns(2)

    with email_col1:
        email_plain = st.selectbox("Emails (no attachments)", email_opts, index=0, key="email_plain")

    with email_col2:
        email_attach = st.selectbox("Emails (with attachments)", email_opts, index=0, key="email_attach")

    cloud = st.selectbox("Cloud storage you currently use for academic or work-related files (e.g., on iCloud, Google Drive, OneDrive)", cloud_opts, index=0, key="cloud")

    wifi = st.slider("Estimate your daily Wi-Fi connection time during a typical 8-hour study or work day, including hours when you're not actively using your device (e.g., background apps, idle mode)", 0.0, 8.0, 4.0, 0.5, key="wifi")
    pages = st.number_input("Printed pages per week", 0, 100, 0, key="pages")

    idle = st.radio("Do you turn off your computer at the end of the workday, or leave it on standby?", ["I turn it off", "I leave it on (idle mode)", "I don’t have a computer"],
    key="idle")

    st.session_state["idle_turns_off"] = (st.session_state.get("idle") == "I turn it off")
    st.session_state["idle_is_left_on"] = (st.session_state.get("idle") == "I leave it on (idle mode)")

    


# --- CALCOLI 
    em_plain  = emails.get(st.session_state.get("email_plain"), 0)
    em_attach = emails.get(st.session_state.get("email_attach"), 0)
    cld = cloud_gb.get(st.session_state.get("cloud"), 0)

    st.session_state["da_em_plain"]   = int(em_plain)
    st.session_state["da_em_attach"]  = int(em_attach)
    st.session_state["da_cloud_gb"]   = float(cld)
    st.session_state["da_pages"] = int(st.session_state.get("pages", 0) or 0)


    mail_total = (em_plain * 0.004 + em_attach * 0.035 + cld * 0.01) * DAYS
    wifi_total  = st.session_state.get("wifi", 4.0) * 0.00584 * DAYS
    pages = int(st.session_state.get("pages", 0) or 0)
    print_total = pages * 0.0045 * (DAYS/5)

    idle_val = st.session_state.get("idle")
    if idle_val == "I leave it on (idle mode)":
        idle_total = DAYS * 0.0104 * 16
    elif idle_val == "I turn it off":
        idle_total = DAYS * 0.0005204 * 16
    else:
        idle_total = 0

    digital_total = hours_total + mail_total + wifi_total + print_total + idle_total


    # === AI TOOLS ===
    st.markdown("""
    <h3 style="margin-top: 25px; color:#1d3557;">🦾 AI Tools</h3>
    <p>
        Estimate how many queries you make for each AI-powered task on a typical 8-hour study/working day.
        As a reference, users submit approximately 15 to 20 queries during a half-hour interaction with an AI assistant.
    </p>
    """, unsafe_allow_html=True)

    ai_total = 0
    ai_queries_count = 0
    cols = st.columns(4)

    for i, (task, ef) in enumerate(ai_factors.items()):
        with cols[i % 4]:
            st.markdown(f"""
            <div style='margin-bottom: 12px;'>
                <div style='
                    font-weight: 600;
                    font-size: 15px;
                    color: #1d3557;
                    margin-bottom: 6px;
                '>
                    {task}
                </div>
            """, unsafe_allow_html=True)

            q = st.number_input(
                label="",
                min_value=0,
                max_value=10000,
                value=0,
                step=5,
                key=task,
                label_visibility="collapsed"
            )
            ai_total += q * ef * DAYS
            ai_queries_count += int(q)

            st.markdown("</div>", unsafe_allow_html=True)

    st.session_state.ai_total_queries = ai_queries_count


    # === FINAL BUTTONS (BACK + NEXT) ===
    col_back, col_space, col_next = st.columns([1, 4, 1])

    with col_back:
        if st.button("⬅️ Back", key="main_back_btn", use_container_width=True):
            st.session_state.page = "intro"  # Oppure "main" se serve tornare a una sottosezione
            st.rerun()

    with col_next:
        next_clicked = st.button(
            f"Next ➡️",
            key="main_next_btn",
            use_container_width=True
        )

    def _devices_missing():
        """
        Ritorna True se esiste almeno un device con select lasciate su '-- Select --'
        (Ownership/Condition/EOL) oppure senza anni validi.
        """
        for dev_id in st.session_state.get("device_list", []):
            vals = st.session_state.get("device_inputs", {}).get(dev_id, {})
            if (
                vals.get("used", "-- Select --") == "-- Select --" or
                vals.get("shared", "-- Select --") == "-- Select --" or
                vals.get("eol", "-- Select --") == "-- Select --" or
                float(vals.get("years", 0) or 0) <= 0
            ):
                return True
        return False


    # --- LOGICA DEL NEXT ---
    if next_clicked:
        unconfirmed_devices = [
            key for key in st.session_state.get("device_expanders", {})
            if st.session_state.device_expanders[key]
        ]

        missing_activities = (
            st.session_state.get("email_plain", "-- Select option --") == "-- Select option --"
            or st.session_state.get("email_attach", "-- Select option --") == "-- Select option --"
            or st.session_state.get("cloud", "-- Select option --") == "-- Select option --"
        )
        no_devices = len(st.session_state.get("device_list", [])) == 0

        missing_devices = _devices_missing()

        # Mostra eventuali warning
        if no_devices:
            st.warning("⚠️ Please add at least one device.")
        if unconfirmed_devices:
            st.warning("⚠️ You have devices not yet confirmed. Please click 'Confirm' in each box to proceed.")
        if _devices_missing() and not no_devices:
            st.warning("⚠️ Please complete Ownership, Condition, and End-of-life for all devices, then press 'Confirm'.")
        if missing_activities:
            st.warning("⚠️ Please complete all digital activity fields before continuing.")


        # Procedi solo se tutto è OK
        if not (no_devices or unconfirmed_devices or _devices_missing() or missing_activities):
            st.session_state.results = {
                "Devices": total_prod,
                "E-Waste": total_eol,
                "Digital Activities": digital_total,
                "AI Tools": ai_total
            }
            st.session_state.page = "guess"
            st.rerun()


def show_guess():
    scroll_top()

    if "archetype_guess" not in st.session_state:
        st.session_state.archetype_guess = None

    # ---- Stili ---- (aggiunta intro-box, senza rimuovere il resto)
    st.markdown("""
        <style>
        .intro-box {
            background: linear-gradient(to right, #d8f3dc, #a8dadc);
            padding: 40px 25px;
            border-radius: 15px;
            text-align: center;
            box-shadow: 0 4px 18px rgba(0,0,0,0.06);
            margin-bottom: 30px;
        }
        .arc-card h4{
            margin: 6px 0 10px; text-align:center; color:#1d3557;
            font-weight:800; font-size:1.05rem;
        }
        .arc-badge{
            display:inline-block; margin:10px auto 12px; padding:6px 12px;
            border:1px solid #e9ecef; border-radius:999px; background:#fff;
            color:#1b4332; font-weight:700; font-size:.9rem;
        }
        .picked { box-shadow: 0 0 0 3px #52b788 inset; border-radius: 12px; }
        div[data-testid="stVerticalBlockBorderWrapper"] > div:empty { display:none; }
        </style>
    """, unsafe_allow_html=True)

    # --- Box identico a intro ---
    st.markdown(f"""
        <div class="intro-box">
            <h2 style="margin:.2rem 0;">{st.session_state.get('name','')}, before you discover your full Digital Carbon Footprint, take a guess!</h2>
            <p style="margin:.2rem 0; color:#1b4332;">
                Based on the area where you think you have the biggest impact, which digital archetype matches you best?
            </p>
        </div>
    """, unsafe_allow_html=True)


    cols = st.columns(4)
    for i, arc in enumerate(ARCHETYPES):
        with cols[i]:
            # contenitore unico con bordo (titolo+img+badge+bottone)
            cont = st.container(border=True)
            with cont:
                # aggiungo una classe 'picked' al contenitore se selezionato
                if st.session_state.get("archetype_guess") == arc["key"]:
                    st.markdown('<div class="picked">', unsafe_allow_html=True)

                st.markdown(f"<div class='arc-card'><h4>{arc['name']}</h4></div>", unsafe_allow_html=True)
                st.image(arc["image"], width=290)
                st.markdown(f"<div style='text-align:center;'><span class='arc-badge'>{arc['category']}</span></div>",
                            unsafe_allow_html=True)

                if st.button("Choose", key=f"choose_{arc['key']}", use_container_width=True):
                    st.session_state.archetype_guess = arc["key"]
                    st.rerun()

                if st.session_state.get("archetype_guess") == arc["key"]:
                    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("### ")
    left, _, right = st.columns([1, 4, 1])
    with left:
        if st.button("⬅️ Back", key="guess_back_btn", use_container_width=True):
            st.session_state.page = "main"
            st.rerun()
    with right:
        if st.button("Discover your Carbon Footprint➡️",
                     key="guess_continue_btn",
                     use_container_width=True,
                     disabled=st.session_state.get("archetype_guess") is None):
            st.session_state.page = "results_cards"
            st.rerun()


# RESULTS PAGES

def show_results_cards():
    scroll_top()
    # stile + header
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
        html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
        h1, h2, h3, h4 { color: #1d3557; }
        </style>
    """, unsafe_allow_html=True)
    st.markdown("""
        <div style="background: linear-gradient(to right, #d8f3dc, #a8dadc); padding: 40px 20px; border-radius: 12px; text-align: center; box-shadow: 0 4px 20px rgba(0,0,0,0.08); margin-bottom: 30px;">
            <h1 style="font-size: 2.8em; margin-bottom: 0.1em;">Your Digital Carbon Footprint🌍</h1>
            <p style="font-size: 1.2em; color: #1b4332;">Discover your impact — and what to do about it.</p>
        </div>
    """, unsafe_allow_html=True)

    res = st.session_state.results
    total = sum(res.values())

    with st.spinner("🔍 Calculating your footprint..."):
        time.sleep(1.2)

    cat_by_value = {
        "Devices": res.get("Devices", 0),
        "E-Waste": res.get("E-Waste", 0),
        "Digital Activities": res.get("Digital Activities", 0),
        "Artificial Intelligence": res.get("AI Tools", 0),
    }
    actual_top = max(cat_by_value, key=cat_by_value.get)
    key_to_category = {a["key"]: a["category"] for a in ARCHETYPES}
    category_to_arc = {a["category"]: a for a in ARCHETYPES}
    guessed_key = st.session_state.get("archetype_guess")
    guessed = next((a for a in ARCHETYPES if a["key"] == guessed_key), None)
    actual = category_to_arc.get(actual_top)
    guessed_right = bool(guessed) and (key_to_category.get(guessed["key"]) == actual_top)

    
    # --- Dynamic average from Stats with minimum sample threshold ---
    MIN_SAMPLES = 10

    role_label = st.session_state.get("role", "")
    total = sum(res.values())

    avg_dynamic, sample_n = get_avg_for_role_from_stats(role_label)
    use_dynamic = (
        isinstance(avg_dynamic, (int, float)) and avg_dynamic > 0 and (sample_n or 0) >= MIN_SAMPLES
    )

    # Use this variable everywhere below
    avg_used = avg_dynamic if use_dynamic else AVERAGE_CO2_BY_ROLE.get(role_label)

    msg, comp_color = None, "#6EA8FE"
    if isinstance(avg_used, (int, float)) and avg_used > 0:
        diff_pct = ((total - avg_used) / avg_used) * 100
        abs_pct = abs(diff_pct)
        if abs_pct < 1:
            msg = f"You're roughly in line with the average {role_label.lower()}."
            comp_color = "#6EA8FE"
        elif diff_pct > 0:
            msg = f"You emit {abs_pct:.0f}% more than the average {role_label.lower()}."
            comp_color = "#e63946"
        else:
            msg = f"You emit {abs_pct:.0f}% less than the average {role_label.lower()}."
            comp_color = "#2b8a3e"


    c1, c2, c3 = st.columns(3)
    CARD_STYLE = """
        display:flex; flex-direction:column; justify-content:center; align-items:center;
        gap:.55rem; min-height:220px; text-align:center;
    """
    CARD_ACCENT = "border-left:4px solid #52b788; padding-left:12px;"

    # Card 1 — Total
    with c1:
        card = st.container(border=True)
        with card:
            st.markdown(
                f"<div style='{CARD_STYLE} {CARD_ACCENT}'>"
                f"<div style='font-size:2rem; color:#1b4332; font-weight:800; margin:0;'>{st.session_state.get('name','')}, your total CO₂e is…</div>"
                f"<div style='font-size:clamp(2.6rem,6vw,3.6rem); line-height:1; font-weight:900; color:#ff7f0e; letter-spacing:-0.5px; margin:0;'>{total:.0f} kg/year</div>"
                f"</div>", unsafe_allow_html=True
            )
    # Card 2 — Comparison
    with c2:
        card = st.container(border=True)
        with card:
            if msg:
                st.markdown(
                    f"<div style='{CARD_STYLE} {CARD_ACCENT}'>"
                    f"<div style='font-size:1.3rem; font-weight:800; color:#1b4332; margin:0;'>Your footprint vs average</div>"
                    f"<div style='font-size:2rem; font-weight:800; color:{comp_color}; line-height:1.15; margin:0;'>{msg}</div>"
                    f"<div style='font-size:1.05rem; color:#1b4332; margin:0;'>Average {role_label.lower()} emissions: <b>{avg_used:.0f} kg/year</b></div>"
                    f"</div>", unsafe_allow_html=True
                )
            else:
                st.markdown(f"<div style='{CARD_STYLE} {CARD_ACCENT}'>No average available for your role.</div>", unsafe_allow_html=True)

    # Card 3 — Archetype
    from pathlib import Path
    if actual is None and actual_top in category_to_arc:
        actual = category_to_arc[actual_top]
    show_arc = guessed if (guessed_right and guessed) else (actual or {})
    arc_name = show_arc.get("name", "")
    arc_img_rel = show_arc.get("image")
    arc_img = None
    if arc_img_rel:
        p = (Path(__file__).parent / arc_img_rel).resolve()
        arc_img = str(p) if p.exists() else arc_img_rel
    title = "Great job, you guessed it! Your match is" if guessed_right else "Nice try, but your match is"

    with c3:
        card = st.container(border=True)
        with card:
            left, right = st.columns([5, 3])
            H = 220
            with left:
                st.markdown(
                    f"""
                    <div style="display:flex; flex-direction:column; justify-content:center; align-items:flex-start;
                                min-height:{H}px; text-align:left; gap:.45rem; {CARD_ACCENT}">
                        <div style="font-size:1.2rem; font-weight:800; color:#1b4332; margin:0;">{title}</div>
                        <div style="font-weight:800; font-size:2rem; line-height:1.1; color:#ff7f0e; margin:0;">{arc_name}</div>
                        <div style="font-size:1.05rem; color:#1b4332; margin:0;">Your biggest footprint comes from <b>{actual_top}</b></div>
                    </div>
                    """, unsafe_allow_html=True
                )
            with right:
                st.markdown("<div style='display:flex; align-items:flex-start; justify-content:flex-end; padding-top:4px;'>", unsafe_allow_html=True)
                if arc_img:
                    st.image(arc_img, width=180)
                st.markdown("</div>", unsafe_allow_html=True)

    # Nav
    st.markdown("### ")
    left, _, right = st.columns([1, 4, 1])
    with left:
        if st.button("⬅️ Back", key="res_cards_back", use_container_width=True):
            st.session_state.page = "guess"
            st.rerun()
    with right:
        if st.button("Next ➡️", key="res_cards_next", use_container_width=True):
            st.session_state.page = "results_breakdown"
            st.rerun()

def show_results_breakdown():
    scroll_top()
    # stile + header
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
        html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
        h1, h2, h3, h4 { color: #1d3557; }
        .tip-card { background-color: #e3fced; border-radius: 10px; padding: 15px; margin-bottom: 10px; }
        </style>
    """, unsafe_allow_html=True)
    st.markdown("""
        <div style="background: linear-gradient(to right, #d8f3dc, #a8dadc); padding: 28px 16px; border-radius: 12px; text-align: center; margin-bottom: 16px;">
            <h2 style="margin:0;">Your footprint breakdown📊</h2>
        </div>
    """, unsafe_allow_html=True)

    res = st.session_state.results

    st.markdown("<br><h3>Breakdown by Category:</h3>", unsafe_allow_html=True)
    st.markdown(f"""
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 15px;">
            <div class="tip-card" style="text-align:center;">
                <div style="font-size: 2em;">💻</div>
                <div style="font-size: 1.2em;"><b>{res['Devices']:.2f} kg CO2e/year</b></div>
                <div style="color: #555;">Devices</div>
            </div>
            <div class="tip-card" style="text-align:center;">
                <div style="font-size: 2em;">🗑️</div>
                <div style="font-size: 1.2em;"><b>{res['E-Waste']:.2f} kg CO2e/year</b></div>
                <div style="color: #555;">E-Waste</div>
            </div>
            <div class="tip-card" style="text-align:center;">
                <div style="font-size: 2em;">🔌</div>
                <div style="font-size: 1.2em;"><b>{res['Digital Activities']:.2f} kg CO2e/year</b></div>
                <div style="color: #555;">Digital Activities</div>
            </div>
            <div class="tip-card" style="text-align:center;">
                <div style="font-size: 2em;">🦾</div>
                <div style="font-size: 1.2em;"><b>{res['AI Tools']:.2f} kg CO2e/year</b></div>
                <div style="color: #555;">AI Tools</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Show E-Waste notes conditionally
    ewaste_val = float(res.get("E-Waste", 0) or 0)
    eps = 1e-9  # to avoid float noise

    if ewaste_val < -eps:
        st.markdown("""
            <div style="background-color:#fefae0; border-left: 6px solid #e09f3e; 
                        padding: 14px; border-radius: 8px; margin-top: 18px;">
                <h4 style="margin-top:0;">Why is my E-Waste impact negative?</h4>
                <p style="margin:0; font-size: 15px; line-height: 1.5;">
                    Sometimes your E-Waste value can be <b>negative</b>: this means that you adopt 
                    responsible practices such as donating devices, bringing them to proper recycling 
                    centers, or returning them to the manufacturer. 
                    These actions help offset part of the CO₂ emissions associated with electronic devices, 
                    and consequently reduce your overall footprint. Good job!
                </p>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
            <div style="background-color:#fefae0; border-left: 6px solid #e09f3e; 
                        padding: 14px; border-radius: 8px; margin-top: 18px;">
                <h4 style="margin-top:0;">Did you know your E-Waste impact could reduce emissions?</h4>
                <p style="margin:0; font-size: 15px; line-height: 1.5;">
                    By making more responsible end-of-life choices for your devices, such as taking them to a
                    certified e-waste collection center, returning them to the manufacturer,
                    or selling/donating them for reuse, you can not only bring this category down to zero, but
                    actually <b>offset</b> part of your overall emissions! 
                </p>
            </div>
        """, unsafe_allow_html=True)


    st.divider()

    st.subheader("Hotspots at a glance")
    df_plot = pd.DataFrame({
        "Category": ["Devices", "Digital Activities", "Artificial Intelligence", "E-Waste"],
        "CO₂e (kg)": [res["Devices"], res["Digital Activities"], res["AI Tools"], res["E-Waste"]]
    })
    fig = px.bar(df_plot, x="CO₂e (kg)", y="Category", orientation="h",
                 color="Category",
                 color_discrete_sequence=["#95d5b2", "#74c69d", "#52b788", "#1b4332"],
                 height=400)
    fig.update_layout(showlegend=False, plot_bgcolor="#f1faee", paper_bgcolor="#f1faee", font_family="Inter")
    fig.update_traces(marker=dict(line=dict(width=1.5, color='white')))
    st.plotly_chart(fig, use_container_width=True)

    # Nav
    st.markdown("### ")
    left, _, right = st.columns([1, 4, 1])
    with left:
        if st.button("⬅️ Back", key="res_brk_back", use_container_width=True):
            st.session_state.page = "results_cards"
            st.rerun()
    with right:
        if st.button("Next ➡️", key="res_brk_next", use_container_width=True):
            st.session_state.page = "results_equiv"
            st.rerun()

def show_results_equiv():
    scroll_top()
    if "saved_once" not in st.session_state:
        st.session_state.saved_once = False

    # stile + header
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
        html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
        h1, h2, h3, h4 { color: #1d3557; }
        .equiv-card { background-color: white; border-left: 6px solid #52b788; border-radius: 12px; padding: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); text-align: center; }
        </style>
    """, unsafe_allow_html=True)
    st.markdown("""
        <div style="background: linear-gradient(to right, #d8f3dc, #a8dadc); padding: 28px 16px; border-radius: 12px; text-align: center; margin-bottom: 16px;">
            <h2 style="margin:0;">The same amount of emissions corresponds to...</h2>
        </div>
    """, unsafe_allow_html=True)

    res = st.session_state.results
    total = sum(res.values())

    burger_eq = total / 4.6
    led_days_eq = (total / 0.256) / 24
    car_km_eq = total / 0.17
    netflix_hours_eq = total / 0.055

    st.markdown(f"""
        <style>
        .equiv-grid {{
            display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 25px; margin-top: 25px;
        }}
        .equiv-emoji {{ font-size: 3.5em; margin-bottom: 15px; }}
        .equiv-text {{ font-size: 1.05em; line-height: 1.6; color: #333; }}
        .equiv-value {{ font-weight: 600; font-size: 1.2em; color: #1b4332; }}
        </style>

        <div class="equiv-grid">
            <div class="equiv-card">
                <div class="equiv-emoji">🍔</div>
                <div class="equiv-text">Eating <span class="equiv-value">~{burger_eq:.0f}</span> beef burgers</div>
            </div>
            <div class="equiv-card">
                <div class="equiv-emoji">💡</div>
                <div class="equiv-text">Keeping 100 LED bulbs (10W) on for <span class="equiv-value">~{led_days_eq:.0f}</span> days</div>
            </div>
            <div class="equiv-card">
                <div class="equiv-emoji">🚗</div>
                <div class="equiv-text">Driving a gasoline car for <span class="equiv-value">~{car_km_eq:.0f}</span> km</div>
            </div>
            <div class="equiv-card">
                <div class="equiv-emoji">📺</div>
                <div class="equiv-text">Watching Netflix for <span class="equiv-value">~{netflix_hours_eq:.0f}</span> hours</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div style="text-align: center; padding: 40px 10px;">
        <h2 style="color: #1d3557;">Visit the next page to discover useful tips for reducing your footprint!💥</h2>
    </div>
    """, unsafe_allow_html=True)

    # Nav + autosave
    st.markdown("### ")
    left, _, right = st.columns([1, 4, 1])
    with left:
        if st.button("⬅️ Back", key="res_eq_back", use_container_width=True):
            st.session_state.page = "results_breakdown"
            st.rerun()
    with right:
        if st.button("➡️ Discover Tips", key="res_eq_next", use_container_width=True):
            try:
                if not st.session_state.get("saved_once", False):
                    import sys
                    api_url = st.secrets.get("SHEETBEST_URL", None)
                    assert api_url, "SHEETBEST_URL not found in st.secrets"

                    role_label = st.session_state.get("role", "")
                    total_val = float(sum(st.session_state.results.values()))
                    resp = save_row(
                        role_label,
                        st.session_state.results.get("Devices", 0),
                        st.session_state.results.get("E-Waste", 0),
                        st.session_state.results.get("AI Tools", 0),
                        st.session_state.results.get("Digital Activities", 0),
                        total_val
                    )
                    print("[autosave] response:", resp, file=sys.stderr)
                    st.session_state.saved_once = True
            except Exception as e:
                import traceback, sys
                print("[autosave][ERROR]", e, file=sys.stderr)
                traceback.print_exc()

            st.session_state.page = "virtues"
            st.rerun()



def show_virtues():
    scroll_top()

    name = (st.session_state.get("name") or "").strip()
    st.markdown(f"""
        <div style="background: linear-gradient(to right, #d8f3dc, #a8dadc);
                    padding: 28px 16px; border-radius: 12px; margin-bottom: 16px; text-align:center;">
            <h2 style="margin:0; color:#1d3557; font-size:2.2rem; line-height:1.2;">
                {name}, here are some practical tips to shrink your digital footprint!
            </h2>
            <p style="margin:8px 0 0; color:#1b4332; font-size:1.05rem;">
                We’ll start with actions tailored to your highest-impact area, followed by general tips you can apply every day.
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    # =======================
    # PERSONALIZED TIPS
    # =======================

    # Prendi i risultati
    res = st.session_state.get("results", {})
    if res:
        # Ricostruisci il ranking categorie
        df_plot = pd.DataFrame({
            "Category": ["Devices", "Digital Activities", "Artificial Intelligence", "E-Waste"],
            "CO₂e (kg)": [res.get("Devices", 0), res.get("Digital Activities", 0), res.get("AI Tools", 0), res.get("E-Waste", 0)]
        })

        most_impact_cat = df_plot.sort_values("CO₂e (kg)", ascending=False).iloc[0]["Category"]

        # === 1) GENERIC (evergreen) TIPS, per categoria ===
        GENERIC_TIPS = {
                "Devices": [
                        "<b>Update software regularly.</b> This enhances efficiency and performance, often reducing energy consumption.",
                        "<b>Activate power-saving settings, reduce screen brightness and enable dark mode.</b> This lowers energy use.",
                        "<b>Choose accessories made from recycled or sustainable materials.</b> This minimizes the environmental impact of your tech choices."
                ],
                "E-Waste": [
                        "<b>Repair instead of replacing.</b> Fix broken electronics whenever possible to avoid unnecessary waste."
                ],
                "Digital Activities": [
                        "<b>Use your internet mindfully:</b> close unused apps, avoid sending large attachments, and turn off video during calls when not essential."
                ],
                "Artificial Intelligence": [
                        "<b>Use search engines for simple tasks: </b> They consume far less energy than AI tools.",
                        "<b>Disable AI-generated results in search engines</b> (e.g., on Bing: go to Settings > Search > Uncheck \"Include AI-powered answers\" or similar option).",
                        "<b>Prefer smaller AI models when possible.</b> For basic tasks, use lighter versions like GPT-4o-mini instead of more energy-intensive models.",
                        "<b>Be concise in AI prompts and require concise answers:</b> short inputs and outputs require less processing."
                ]
        }
        
        # === 2) PERSONALIZED TIPS FACTORIES 
        
        # ===============================
        # Helpers comuni
        # ===============================
        def _adj_years(years: float, used: str, shared: str) -> float:
            if years <= 0:
                return 0.0
            if shared == "Personal":
                return years * (1.5 if used == "Used" else 1.0)
            elif shared == "Shared with family":
                return years * (4.5 if used == "Used" else 3.0)
            elif shared == "Shared in university":
                return years * (15 if used == "Used" else 10.0)
            else:
                return years

        def _fmt_kg(x: float) -> str:
            # arrotonda "pulito": 0 decimali se grande, 1 decimale altrimenti
            if x >= 10:
                return f"{round(x):,}".replace(",", " ")
            return f"{round(x, 1)}"

        # ===============================
        # Personalized Tips – DEVICES
        # ===============================
        def tip_devices_new_laptopdesktop_best(state) -> str | None:
            """
            Se esistono Laptop/Desktop nuovi, suggerisci il ricondizionato.
            Mostra solo il device con risparmio annuo maggiore.
            """
            best_saving = 0.0
            best_noun = None

            for dev_id, vals in (state.get("device_inputs") or {}).items():
                base = dev_id.rsplit("_", 1)[0]
                if base not in ("Laptop Computer", "Desktop Computer"):
                    continue
                if vals.get("used") != "New":
                    continue

                try:
                    years = float(vals.get("years", 0) or 0)
                except Exception:
                    years = 0.0
                if years <= 0:
                    continue

                shared = vals.get("shared") or "Personal"
                impact = float(device_ef.get(base, 0) or 0)
                if impact <= 0:
                    continue

                adj_curr = _adj_years(years, used="New", shared=shared)
                # scenario alternativo: stesso shared, ma 'Used'
                adj_alt = _adj_years(years, used="Used", shared=shared)
                if adj_curr <= 0 or adj_alt <= 0:
                    continue

                saving = impact * (1.0 / adj_curr - 1.0 / adj_alt)  # kg/anno
                if saving > best_saving:
                    best_saving = saving
                    best_noun = "laptop" if base == "Laptop Computer" else "desktop"

            if best_saving > 0 and best_noun:
                X = _fmt_kg(best_saving)
                return (
                    f"<b>You bought a new {best_noun}: next time consider choosing a used or refurbished one.</b> "
                    f"You could save about {X} kg CO₂e/year (vs a new device with the same usage)."
                )
            return None

        def tip_devices_extend_life_any_device(state) -> str | None:
            """
            Qualsiasi device con lifespan <= 3 anni → suggerisci estensione di +2 anni.
            Mostra solo il caso con risparmio annuo maggiore.
            """
            best = {"base": None, "years": None, "saving": 0.0}

            for dev_id, vals in (state.get("device_inputs") or {}).items():
                base = dev_id.rsplit("_", 1)[0]
                try:
                    years = float(vals.get("years", 0) or 0)
                except Exception:
                    years = 0.0
                if years <= 0 or years > 3:
                    continue

                used = vals.get("used") or "New"
                shared = vals.get("shared") or "Personal"
                impact = float(device_ef.get(base, 0) or 0)
                if impact <= 0:
                    continue

                adj_curr = _adj_years(years, used=used, shared=shared)
                adj_ext = _adj_years(years + 2.0, used=used, shared=shared)
                if adj_curr <= 0 or adj_ext <= 0:
                    continue

                saving = impact * (1.0 / adj_curr - 1.0 / adj_ext)  # kg CO2e/anno
                if saving > best["saving"]:
                    best.update({"base": base, "years": years, "saving": saving})

            if best["saving"] > 0 and best["base"]:
                X = _fmt_kg(best["saving"])
                device_label = best["base"].lower()
                return (
                    f"<b>You plan to use your {device_label} for {best['years']:.0f} years.</b> "
                    f"if you extend it to {best['years'] + 2:.0f}, you could save about {X} kg CO₂e/year."
                )
            return None


        # ===============================
        # Personalized Tips – E-WASTE
        # ===============================
        def tip_ewaste_stored_at_home(state) -> str | None:
            """
            Per tutti i device con eol == 'I store it at home, unused':
            stima saving annuo passando da 'store' (0.402) a:
              - centro raccolta (-0.224)  → delta min
              - sell/donate (-0.445)      → delta max
            Somma i risparmi e mostra range.
            """
            items = []
            saving_min = 0.0
            saving_max = 0.0

            for dev_id, vals in (state.get("device_inputs") or {}).items():
                if vals.get("eol") != "I store it at home, unused":
                    continue

                base = dev_id.rsplit("_", 1)[0]
                try:
                    years = float(vals.get("years", 0) or 0)
                except Exception:
                    years = 0.0
                if years <= 0:
                    continue

                used = vals.get("used") or "New"
                shared = vals.get("shared") or "Personal"
                impact = float(device_ef.get(base, 0) or 0)
                if impact <= 0:
                    continue

                adj = _adj_years(years, used=used, shared=shared)
                if adj <= 0:
                    continue

                # delta verso alternative (per anno)
                delta_min = impact * ((0.402 - (-0.224)) / adj)   # -> certified
                delta_max = impact * ((0.402 - (-0.445)) / adj)   # -> sell/donate
                saving_min += max(0.0, delta_min)
                saving_max += max(0.0, delta_max)
                items.append(base)

            if items and (saving_min > 0 or saving_max > 0):
                uniq = ", ".join(sorted(set(items)))
                lo = _fmt_kg(saving_min)
                hi = _fmt_kg(saving_max)
                return (
                    f"<b>You have {uniq} stored at home.</b> Recycling or reusing them could save between {lo} and {hi} kg CO₂e/year. Don’t let them gather dust!"
                )
            return None

        def tip_ewaste_general_trash(state) -> str | None:
            """
            Per device con eol == 'I throw it away in general waste' (0.611):
            stima il saving annuo se passassero alla miglior alternativa (sell/donate: -0.445)
            e indica per quali device vale.
            """
            total_saving = 0.0
            devices = []

            for dev_id, vals in (state.get("device_inputs") or {}).items():
                if vals.get("eol") != "I throw it away in general waste":
                    continue

                base = dev_id.rsplit("_", 1)[0]
                devices.append(base)

                try:
                    years = float(vals.get("years", 0) or 0)
                except Exception:
                    years = 0.0
                if years <= 0:
                    continue

                used = vals.get("used") or "New"
                shared = vals.get("shared") or "Personal"
                impact = float(device_ef.get(base, 0) or 0)
                if impact <= 0:
                    continue

                adj = _adj_years(years, used=used, shared=shared)
                if adj <= 0:
                    continue

                # delta verso best alternative (sell/donate: -0.445)
                delta = impact * ((0.611 - (-0.445)) / adj)
                total_saving += max(0.0, delta)

            if devices and total_saving > 0:
                names = ", ".join(sorted(set(devices)))
                X = _fmt_kg(total_saving)
                return (
                    f"<b>You throw {names} away in general waste. this prevents proper recycling or reuse.</b> "
                    f"Bringing it to a certified collection point could save about {X} kg CO₂e/year."
                )
            return None


        # ===============================
        # Personalized Tips – DIGITAL ACTIVITIES
        # ===============================
        def tip_emails_with_attachments_impact(state) -> str | None:
                """
                Mostra l'impatto annuo delle email con allegati
                SOLO se > 10 email/giorno (soglia).
                """
                em_attach = int(state.get("da_em_attach", 0))  # soglia > 10
                if em_attach <= 10:
                        return None
                impact_year = em_attach * 0.035 * DAYS  # kg CO2e/anno
                X = _fmt_kg(impact_year)
                return (
                        f"<b>Currently, your emails with attachments emit around {X} kg CO₂e/year.</b> Try sharing links to OneDrive or Google Drive instead of large attachments."
                )

        def tip_emails_plain_impact(state) -> str | None:
                """
                Mostra l'impatto annuo delle email senza allegati
                SOLO se > 10 email/giorno (soglia).
                """
                em_plain = int(state.get("da_em_plain", 0))  # soglia > 10
                if em_plain <= 10:
                        return None
                impact_year = em_plain * 0.004 * DAYS  # kg CO2e/anno
                X = _fmt_kg(impact_year)
                return (
                        f"<b>Currently, your emails without attachments emit around {X} kg CO₂e/year. </b> To reduce this, opt for instant messaging where possible."
                )
            
        def tip_cloud_storage_impact(state) -> str | None:
                """
                Se lo storage cloud è >50GB, mostra l'impatto annuo attuale e consiglia di fare decluttering.
                """
                cld = float(state.get("da_cloud_gb", 0))  # soglia > 50
                if cld <= 50:
                        return None
                impact_year = cld * 0.01  # kg CO2e/anno
                X = _fmt_kg(impact_year)
                return (
                        f"<b>At the moment, your annual footprint from stored data is {X} kg CO₂e/year.</b> Try to declutter your digital space by regularly deleting unnecessary files and emptying trash and spam folders to reduce digital pollution."
                )

        def tip_idle_left_on(state) -> str | None:
            """
            Se 'I leave it on (idle mode)': saving passando a 'I turn it off'.
            """
            if not state.get("idle_is_left_on", False):
                return None
            saved = DAYS * 16.0 * (0.0104 - 0.0005204)
            X = _fmt_kg(saved)
            return (
                f"<b>You usually leave your computer on in idle mode. </b> Turning it off at the end of the day could save up to {X} kg CO₂e/year and extend its lifespan."
            )

        # ===============================
        # Personalized Tips – AI
        # ===============================
        def tip_ai_queries_volume(state) -> str | None:
                """
                Mostra il volume totale di query AI al giorno.
                Se > 30, suggerisce di fare richieste più mirate per ridurre il numero e l'energia usata.
                """
                Q = int(state.get("ai_total_queries", 0) or 0)
                if Q <= 30:
                        return None
                return (
                        f"<b>You're asking about {Q} AI queries per day. </b> Try making more targeted requests to reduce this number and save energy."
                )

        # ===============================
        # Registry + Aggregator + Rendering
        # ===============================
        PERSONALIZED_TIP_FACTORIES = {
            "Devices": [
                tip_devices_new_laptopdesktop_best,
                tip_devices_extend_life_any_device,
            ],
            "E-Waste": [
                tip_ewaste_stored_at_home,
                tip_ewaste_general_trash,
            ],
            "Digital Activities": [
                tip_cloud_storage_impact,
                tip_emails_with_attachments_impact,
                tip_idle_left_on,
                tip_emails_plain_impact,
            ],
            "Artificial Intelligence": [
                tip_ai_queries_volume,
            ],
        }

        def gather_personalized_tips(state):
            out = {k: [] for k in PERSONALIZED_TIP_FACTORIES}
            for cat, funcs in PERSONALIZED_TIP_FACTORIES.items():
                for f in funcs:
                    try:
                        tip = f(state)
                    except Exception:
                        tip = None
                    if tip:
                        out[cat].append(tip)
            return out

        def _dedup_keep_order(seq):
            seen = set()
            out = []
            for x in seq:
                if x not in seen:
                    out.append(x)
                    seen.add(x)
            return out

        # --- Build personalized tips
        personalized = gather_personalized_tips(st.session_state)

        # --- TOP CATEGORY → show ALL tips (personalized + generic)
        top_personal = personalized.get(most_impact_cat, [])
        top_generic  = GENERIC_TIPS.get(most_impact_cat, [])
        top_tips = _dedup_keep_order(top_personal + top_generic)

        with st.expander(f"📌 Tips for top impact area: {most_impact_cat}", expanded=True):
            for tip in top_tips:
                st.markdown(
                    f"<div style='background:#e3fced; padding:15px; border-radius:10px; margin-bottom:10px;'>{tip}</div>",
                    unsafe_allow_html=True
                )

        # --- OTHER CATEGORIES → up to 2 tips each, prioritize personalized
        seed = f"{st.session_state.get('name','')}|{st.session_state.get('role','')}"
        rnd = random.Random(seed)  # stable per utente

        for cat in [c for c in GENERIC_TIPS.keys() if c != most_impact_cat]:
            pers = personalized.get(cat, [])
            picked = pers[:2]  # take up to 2 personalized

            if len(picked) < 2:
                remaining = 2 - len(picked)
                gen_pool = [g for g in GENERIC_TIPS.get(cat, []) if g not in picked]
                if gen_pool:
                    picked += gen_pool if len(gen_pool) <= remaining else rnd.sample(gen_pool, remaining)

            if picked:  # se resta solo 1 tip va bene
                with st.expander(f"📌 More to improve in {cat}", expanded=False):
                    for tip in picked:
                        st.markdown(
                            f"<div style='background:#e3fced; padding:15px; border-radius:10px; margin-bottom:10px;'>{tip}</div>",
                            unsafe_allow_html=True
                        )

    st.markdown("""
        <div style="background-color:#fefae0; border-left: 6px solid #e09f3e; 
                    padding: 14px; border-radius: 8px; margin-top: 18px;">
            <h4 style="margin-top:0;">Next step...</h4>
            <p style="margin:0; font-size: 15px; line-height: 1.5;">
                Try applying some or all of these tips, then come back in 6 months and recalculate your footprint. 
                You’ll see how much you’ve improved!
            </p>
        </div>
    """, unsafe_allow_html=True)



    st.markdown("""
        <style>
        .virtue-card {
            background-color: #e7f5ff;
            border-radius: 12px;
            padding: 14px 16px;
            margin-bottom: 10px;
            border-left: 6px solid #74C0FC;
        }
        </style>
    """, unsafe_allow_html=True)

    name = st.session_state.get("name", "").strip() or "there"

    # Raccogli virtù
    virtues = []

    # 1) Devices usati: elenca i device usati
    used_devices = []
    for dev_id, vals in st.session_state.get("device_inputs", {}).items():
        if vals.get("used") == "Used":
            base = dev_id.rsplit("_", 1)[0]
            used_devices.append(base)
    if used_devices:
        unique_used = ", ".join(sorted(set(used_devices)))
        virtues.append(f"You chose a used device for your {unique_used}! This typically reduces manufacturing emissions by 30–50% per device.")

    # 2) Device longevity: usati per più di 5 anni
    long_lived_devices = []
    for dev_id, vals in st.session_state.get("device_inputs", {}).items():
        try:
            if float(vals.get("years", 0)) > 5:
                base = dev_id.rsplit("_", 1)[0]
                long_lived_devices.append(base)
        except Exception:
            pass

    if long_lived_devices:
        names = ", ".join(sorted(set(long_lived_devices)))
        virtues.append(f"You use your {names} for more than 5 years! Extending device life reduces the need for new production and saves valuable resources.")

    
    # 3) End-of-life virtuoso (almeno uno dei device)
    good_eols = {
        "I bring it to a certified e-waste collection center",
        "I return it to manufacturer for recycling or reuse",
        "I sell or donate it to someone else",
        "Device provided by the university, I return it after use",
    }
    has_good_eol = any(
        vals.get("eol") in good_eols
        for vals in st.session_state.get("device_inputs", {}).values()
    )
    if has_good_eol:
        virtues.append("You dispose some of devices responsibly! EU aims to achieve a correct e-waste disposal rate of 65%, but many countries are still below this threshold.")

    # 4) Poche email con allegato (1–10)
    da_em_attach = int(st.session_state.get("da_em_attach", 0) or 0)
    if da_em_attach <= 10:
        virtues.append(
            "You keep the exchange of emails with attachments low. An email with an attachment typically weighs almost ten times more than one without."
        )
  
    # 5) Cloud storage basso (<5GB o 5–20GB)
    da_cloud_gb = float(st.session_state.get("da_cloud_gb", 0) or 0.0)
    if da_cloud_gb <= 20:
        virtues.append(
            "You keep your cloud storage light by cleaning up files you no longer need! This reduces the energy required to store and maintain them."
        )

    # 6) Spegnere il computer quando non usato
    if st.session_state.get("idle_turns_off"):
        virtues.append("You turn off your computer when not in use. This single action can save over 150 kWh of energy per year for a single computer!")

    # 7) Zero stampe
    pages = int(st.session_state.get("da_pages", 0) or 0)
    if pages == 0:
        virtues.append(
            "You never print. This saves paper, ink, and the energy needed for printing... the trees thank you!"
        )

    # 8) Uso moderato dell’AI (< 20 query/giorno)
    ai_total_queries = int(st.session_state.get("ai_total_queries", 0))
    if ai_total_queries <= 20:
        virtues.append(
            "You use AI sparingly, staying under 20 queries a day. This reduces the energy consumed by high-compute AI models."
        )

    if virtues:
        st.markdown("#### You’re already making smart choices")
        st.markdown(
            "<p style='margin-top:-4px; font-size:0.95rem; color:#1b4332;'>Here are a few great habits we noticed from your answers.</p>",
            unsafe_allow_html=True
        )
        for v in virtues:
            st.markdown(f'<div class="virtue-card">{v}</div>', unsafe_allow_html=True)

    # Pulsante per passare ai risultati
    st.markdown("### ")

    left, _, right = st.columns([1, 4, 1])
    with left:
        if st.button("⬅️ Back", key="virt_back_btn", use_container_width=True):
            st.session_state.page = "results_equiv"
            st.rerun()
    with right:
        if st.button("Finish ➡️", key="virt_finish_btn", use_container_width=True):
            st.session_state.page = "final"
            st.rerun()   


CONTACT_EMAIL = "marta.pinzone@polimi.it"

def show_final():
    scroll_top()

    name = (st.session_state.get("name") or "").strip()
    st.markdown(f"""
        <div style="background: linear-gradient(to right, #d8f3dc, #a8dadc);
                    padding: 40px 25px; border-radius: 15px; text-align:center;
                    box-shadow: 0 4px 18px rgba(0,0,0,0.06); margin-bottom: 30px;">
            <h2 style="font-size:2.2rem; color:#1d3557; margin-bottom:0.6em;">
                Great job, {name}! Keep going💪
            </h2>
            <p style="font-size:1.05rem; color:#1b4332; line-height:1.6; max-width:760px; margin:0 auto;">
                By completing this tool, you are already part of the change towards greener digital practices.
                <br><br>
                The emission factors used in the calculator come primarily from internationally recognized databases, 
                such as Ecoinvent v3.11 and Base Carbone® (ADEME, v23.7). Where not available, they have been 
                supplemented with peer-reviewed scientific studies and specialized literature, listed below.
                <br><br>
                If you would like more information about the calculator or the <i>Green DiLT</i> project,
                or if you have suggestions for improvement, feel free to contact us at:
                <b>{CONTACT_EMAIL}</b>.
            </p>
        </div>
    """, unsafe_allow_html=True)

    # 📚 Tendina delle fonti fuori dal box verde
    st.markdown("""
        <details style="margin-top:10px; cursor:pointer;">
            <summary style="font-weight:bold; color:#1b4332; font-size:1rem;">
                Literature sources
            </summary>
            <ul style="margin-top:10px; padding-left:20px; color:#1b4332; text-align:left;">
                <li>Herrmann et al. (2023): <i>The Climate Impact of the Usage of Headphones and Headsets</i></li>
                <li>Sanchez-Cuadrado & Morato (2024): <i>The carbon footprint of Spanish university websites</i></li>
                <li>Dias & Arroja (2012): <i>Comparison of methodologies for estimating the carbon footprint – case study of office paper</i></li>
                <li>Lannelongue & Inouye (2023): <i>Carbon footprint estimation for computational research</i></li>
                <li>Jegham et al. (2025): <i>How Hungry is AI? Benchmarking Energy, Water, and Carbon Footprint of LLM Inference</i></li>
                <li>Tomlinson et al. (2024): <i>The Carbon Emissions of Writing and Illustrating Are Lower for AI than for Humans</i></li>
                <li>André et al. (2019): <i>Resource and environmental impacts of using second-hand laptop computers: A case study of commercial reuse</i></li>
                <li>Choi et al. (2006): <i>Life Cycle Assessment of a Personal Computer and its Effective Recycling Rate</i></li>
                <li>Yuksek et al. (2023): <i>Sustainability Assessment of Electronic Waste Remanufacturing: The Case of Laptop</i></li>
                <li>Tua et al. (2022): <i>Editoria scolastica e impatti ambientali: analisi del caso Zanichelli tramite la metodologia LCA</i></li>
            </ul>
        </details>
    """, unsafe_allow_html=True)




    # --- Navigazione finale ---
    st.markdown("### ")
    left, _, right = st.columns([1, 4, 1])
    with left:
        if st.button("⬅️ Back", key="final_back_btn", use_container_width=True):
            st.session_state.page = "virtues"
            st.rerun()
    with right:
        if st.button("✏️ Edit your answers", key="final_edit_btn", use_container_width=True):
            st.session_state.page = "main"
            st.rerun()   
    
    _, _, right = st.columns([1, 4, 1])        
    with right:
        if st.button("🔄 Restart", key="final_restart_btn", use_container_width=True):
            st.session_state.clear() 
            st.session_state.page = "intro"
            st.rerun()


# === PAGE NAVIGATION ===
if st.session_state.page == "intro":
    show_intro()
elif st.session_state.page == "main":
    show_main()
elif st.session_state.page == "guess":
    show_guess()
elif st.session_state.page == "results_cards":
    show_results_cards()
elif st.session_state.page == "results_breakdown":
    show_results_breakdown()
elif st.session_state.page == "results_equiv":
    show_results_equiv()
elif st.session_state.page == "virtues":
    show_virtues()
elif st.session_state.page == "final":
    show_final()
































































