import json
import random
import datetime as dt
import re
import time
from pathlib import Path

import streamlit as st


# -----------------------------
# Page config
# -----------------------------
st.set_page_config(
    page_title="PropGuessr",
    page_icon="🏠",
    layout="centered",
)

APP_DIR = Path(__file__).parent
DATA_FILE = APP_DIR / "properties.json"
IMAGES_DIR = APP_DIR / "images"
ROUNDS_PER_GAME = 5


# -----------------------------
# Styling
# -----------------------------
st.markdown(
    """
    <style>
    .main .block-container {
        padding-top: 1.4rem;
        padding-bottom: 3rem;
        max-width: 980px;
    }

    .hero {
        text-align: center;
        margin-bottom: 0.8rem;
    }

    .hero h1 {
        margin-bottom: 0.2rem;
    }

    .hero p {
        color: #6b7280;
        margin-top: 0;
    }

    .panel {
        background: linear-gradient(180deg, #ffffff 0%, #fafafa 100%);
        border: 1px solid #ececec;
        border-radius: 18px;
        padding: 1rem 1rem 0.85rem 1rem;
        margin-bottom: 1rem;
        box-shadow: 0 8px 24px rgba(0,0,0,0.05);
    }

    .result-card {
        background: #f8fafc;
        border: 1px solid #e5e7eb;
        border-radius: 18px;
        padding: 1rem 1.1rem;
        margin-top: 0.75rem;
        margin-bottom: 1rem;
    }

    .library-card {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 18px;
        padding: 0.9rem 0.9rem 0.7rem 0.9rem;
        box-shadow: 0 6px 18px rgba(0,0,0,0.04);
        margin-bottom: 1rem;
        height: 100%;
    }

    .muted {
        color: #6b7280;
        font-size: 0.95rem;
    }

    .pill {
        display: inline-block;
        padding: 0.35rem 0.72rem;
        border-radius: 999px;
        font-size: 0.84rem;
        font-weight: 600;
        margin-right: 0.4rem;
        margin-bottom: 0.4rem;
        background: #f3f4f6;
        color: #111827;
    }

    .mode-banner {
        background: linear-gradient(90deg, #fff7ed 0%, #fffbeb 100%);
        border: 1px solid #fed7aa;
        border-radius: 16px;
        padding: 0.9rem 1rem;
        margin-bottom: 1rem;
    }

    .mode-title {
        font-weight: 700;
        color: #9a3412;
        margin-bottom: 0.15rem;
    }

    .recap-row {
        padding: 0.65rem 0;
        border-bottom: 1px solid #ececec;
    }

    .recap-row:last-child {
        border-bottom: none;
    }

    .share-box {
        background: #f9fafb;
        border: 1px dashed #d1d5db;
        border-radius: 14px;
        padding: 0.9rem 1rem;
        white-space: pre-wrap;
        font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
        font-size: 0.92rem;
    }

    .small-stat {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 14px;
        padding: 0.8rem 0.95rem;
        margin-bottom: 0.8rem;
    }

    .library-title {
        font-weight: 700;
        font-size: 1rem;
        margin-bottom: 0.15rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# -----------------------------
# Helpers
# -----------------------------
def load_properties():
    if not DATA_FILE.exists():
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_properties(properties):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(properties, f, indent=2, ensure_ascii=False)


def format_currency(value):
    return f"£{value:,.0f}"


def slugify(text):
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or "property"


def calculate_score(guess, actual):
    if actual <= 0:
        return 0
    error_ratio = abs(guess - actual) / actual
    score = round(5000 * max(0, 1 - error_ratio))
    return score


def feedback_band(score):
    if score >= 4600:
        return "🎯 Spot on", "That is annoyingly accurate."
    if score >= 3800:
        return "👌 Very close", "You clearly know your way around listings."
    if score >= 2500:
        return "🙂 Decent effort", "Not bad — respectable property instincts."
    if score >= 1200:
        return "😬 Bit off", "You had the right general area… spiritually."
    return "💀 Miles off", "A fearless valuation."

def final_verdict(total_score, max_score):
    pct = total_score / max_score if max_score else 0
    if pct >= 0.85:
        return "🏆 Elite estate-agent brain", "You absolutely know UK property values."
    if pct >= 0.65:
        return "📈 Strong effort", "Solid instincts. You’ve clearly browsed a few listings."
    if pct >= 0.45:
        return "🏠 Respectable", "Good moments, mixed with a few rogue guesses."
    return "🌀 Chaotic valuation era", "The market remains mysterious and you embraced that."


def get_seed_for_mode(mode, selected_date):
    if mode == "Daily Challenge":
        return int(selected_date.strftime("%Y%m%d"))
    return random.randint(1, 10_000_000)


def pick_rounds(properties, mode, selected_date):
    rounds_to_play = min(ROUNDS_PER_GAME, len(properties))
    if rounds_to_play == 0:
        return []

    if mode == "Daily Challenge":
        rng = random.Random(get_seed_for_mode(mode, selected_date))
        return rng.sample(properties, rounds_to_play)

    rng = random.Random()
    props = properties[:]
    rng.shuffle(props)
    return props[:rounds_to_play]


def build_game_key(mode, selected_date):
    if mode == "Daily Challenge":
        return f"daily_{selected_date.isoformat()}"
    return f"practice_{st.session_state.get('practice_run_id', 1)}"


def build_share_text():
    total = st.session_state.total_score
    total_rounds = len(st.session_state.rounds)
    max_score = total_rounds * 5000

    mode = st.session_state.mode
    if mode == "Daily Challenge":
        headline = f"PropGuessr — Daily Challenge ({st.session_state.selected_date.isoformat()})"
    else:
        headline = "PropGuessr — Practice Mode"

    lines = [
        headline,
        f"Score: {total:,}/{max_score:,}",
        "",
    ]

    for i, row in enumerate(st.session_state.history, start=1):
        lines.append(
            f"Round {i}: {row['town']} — guessed {format_currency(row['guess'])}, "
            f"actual {format_currency(row['actual'])}, score {row['score']:,}"
        )

    return "\n".join(lines)


def start_new_game(force=False):
    game_key = build_game_key(st.session_state.mode, st.session_state.selected_date)

    if force or st.session_state.get("game_key") != game_key:
        properties = load_properties()
        st.session_state.rounds = pick_rounds(
            properties,
            st.session_state.mode,
            st.session_state.selected_date,
        )
        st.session_state.round_index = 0
        st.session_state.total_score = 0
        st.session_state.revealed = False
        st.session_state.last_guess = None
        st.session_state.last_score = 0
        st.session_state.game_finished = False
        st.session_state.history = []
        st.session_state.game_key = game_key


def go_to_next_round():
    st.session_state.round_index += 1
    st.session_state.revealed = False
    st.session_state.last_guess = None
    st.session_state.last_score = 0

    if st.session_state.round_index >= len(st.session_state.rounds):
        st.session_state.game_finished = True


def reset_practice_mode():
    st.session_state.practice_run_id = st.session_state.get("practice_run_id", 1) + 1
    start_new_game(force=True)


def submit_guess(current_property, guess):
    actual = current_property["askingPrice"]
    round_score = calculate_score(guess, actual)

    st.session_state.last_guess = int(guess)
    st.session_state.last_score = round_score
    st.session_state.total_score += round_score
    st.session_state.revealed = True

    st.session_state.history.append(
        {
            "town": current_property["town"],
            "region": current_property["region"],
            "title": current_property["title"],
            "guess": int(guess),
            "actual": int(actual),
            "score": int(round_score),
        }
    )


def save_uploaded_image(uploaded_file, town, property_type):
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    original_suffix = Path(uploaded_file.name).suffix.lower()
    if original_suffix not in [".jpg", ".jpeg", ".png", ".webp"]:
        original_suffix = ".jpg"

    file_name = (
        f"{slugify(town)}_{slugify(property_type)}_{int(time.time() * 1000)}{original_suffix}"
    )
    output_path = IMAGES_DIR / file_name
    output_path.write_bytes(uploaded_file.getbuffer())

    return f"images/{file_name}"


def add_property_record(
    title,
    town,
    region,
    bedrooms,
    property_type,
    asking_price,
    uploaded_file,
):
    properties = load_properties()

    image_path = save_uploaded_image(uploaded_file, town, property_type)

    new_record = {
        "id": f"prop_{int(time.time() * 1000)}",
        "title": title.strip(),
        "town": town.strip(),
        "region": region.strip(),
        "bedrooms": int(bedrooms),
        "propertyType": property_type.strip(),
        "askingPrice": int(asking_price),
        "imagePath": image_path,
    }

    properties.append(new_record)
    save_properties(properties)
    return new_record


# -----------------------------
# State init
# -----------------------------
if "mode" not in st.session_state:
    st.session_state.mode = "Daily Challenge"

if "selected_date" not in st.session_state:
    st.session_state.selected_date = dt.date.today()

if "practice_run_id" not in st.session_state:
    st.session_state.practice_run_id = 1

if "game_key" not in st.session_state:
    st.session_state.game_key = None

if "history" not in st.session_state:
    st.session_state.history = []

if "admin_notice" not in st.session_state:
    st.session_state.admin_notice = None


# -----------------------------
# Sidebar controls
# -----------------------------
with st.sidebar:
    st.markdown("## Game mode")

    chosen_mode = st.radio(
        "Choose mode",
        ["Daily Challenge", "Practice Mode"],
        index=0 if st.session_state.mode == "Daily Challenge" else 1,
    )

    if chosen_mode != st.session_state.mode:
        st.session_state.mode = chosen_mode
        if chosen_mode == "Practice Mode":
            reset_practice_mode()
        else:
            start_new_game(force=True)
        st.rerun()

    if st.session_state.mode == "Daily Challenge":
        chosen_date = st.date_input(
            "Challenge date",
            value=st.session_state.selected_date,
        )

        if chosen_date != st.session_state.selected_date:
            st.session_state.selected_date = chosen_date
            start_new_game(force=True)
            st.rerun()

        st.caption("Same date = same 5 properties, so scores are comparable.")
    else:
        st.caption("Practice Mode gives you a reshuffled game whenever you reset.")
        if st.button("🔀 New practice run", use_container_width=True):
            reset_practice_mode()
            st.rerun()

    if st.button("♻️ Restart current game", use_container_width=True):
        start_new_game(force=True)
        st.rerun()

    st.divider()
    props_count = len(load_properties())
    st.metric("Properties in library", props_count)

    if DATA_FILE.exists():
        st.download_button(
            "⬇️ Download property bank JSON",
            data=DATA_FILE.read_text(encoding="utf-8"),
            file_name="properties_backup.json",
            mime="application/json",
            use_container_width=True,
        )


# Make sure the right game is loaded
start_new_game()

properties_all = load_properties()


# -----------------------------
# Header
# -----------------------------
st.markdown(
    """
    <div class="hero">
        <h1>🏠 PropGuessr</h1>
        <p>Think you know UK house prices?</p>
    </div>
    """,
    unsafe_allow_html=True,
)

if st.session_state.mode == "Daily Challenge":
    banner_text = f"Daily Challenge • {st.session_state.selected_date.strftime('%A %d %B %Y')}"
    banner_sub = "Everyone playing this date gets the same property set."
else:
    banner_text = "Practice Mode"
    banner_sub = "Play, tweak, test, repeat."

st.markdown(
    f"""
    <div class="mode-banner">
        <div class="mode-title">{banner_text}</div>
        <div class="muted">{banner_sub}</div>
    </div>
    """,
    unsafe_allow_html=True,
)


# -----------------------------
# Tabs
# -----------------------------
play_tab, add_tab, library_tab = st.tabs(["🎮 Play", "➕ Add Property", "🗂️ Library"])


# -----------------------------
# PLAY TAB
# -----------------------------
with play_tab:
    if len(st.session_state.rounds) == 0:
        st.error("Your property bank is empty. Add some properties in the 'Add Property' tab first.")
    elif st.session_state.game_finished:
        max_score = len(st.session_state.rounds) * 5000
        verdict, subtext = final_verdict(st.session_state.total_score, max_score)
        share_text = build_share_text()

        st.progress(100, text="Game complete")
        st.markdown("## Final Score")

        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Your total", f"{st.session_state.total_score:,}", border=True)
        with c2:
            st.metric("Max possible", f"{max_score:,}", border=True)
        with c3:
            pct = round((st.session_state.total_score / max_score) * 100) if max_score else 0
            st.metric("Accuracy vibe", f"{pct}%", border=True)

        st.markdown(
            f"""
            <div class="result-card">
                <div style="font-weight: 700; font-size: 1.05rem; margin-bottom: 0.2rem;">{verdict}</div>
                <div class="muted">{subtext}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.session_state.total_score >= 20000:
            st.balloons()

        st.markdown("### Round recap")
        for i, row in enumerate(st.session_state.history, start=1):
            diff = row["guess"] - row["actual"]
            direction = "too high" if diff > 0 else "too low" if diff < 0 else "exact"
            diff_text = "exact" if diff == 0 else f"{format_currency(abs(diff))} {direction}"

            st.markdown(
                f"""
                <div class="recap-row">
                    <strong>Round {i} — {row['town']}, {row['region']}</strong><br>
                    <span class="muted">{row['title']}</span><br>
                    Guessed <strong>{format_currency(row['guess'])}</strong> •
                    Actual <strong>{format_currency(row['actual'])}</strong> •
                    {diff_text} •
                    Score <strong>{row['score']:,}</strong>
                </div>
                """,
                unsafe_allow_html=True,
            )

        share_text = f"""🏠 PropGuessr

        I scored {st.session_state.total_score:,} / {len(st.session_state.rounds) * 5000:,}
        on today's PropGuessr.

        Can you beat me?
        """

        st.markdown("### Share text")
        st.markdown(
            f'<div class="share-box">{share_text}</div>',
            unsafe_allow_html=True,
        )

        st.download_button(
            "⬇️ Download share text",
            data=share_text,
            file_name="propguessr_share_text.txt",
            mime="text/plain",
            use_container_width=True,
        )

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("🔁 Play again", type="primary", use_container_width=True):
                if st.session_state.mode == "Practice Mode":
                    reset_practice_mode()
                else:
                    start_new_game(force=True)
                st.rerun()

        with col_b:
            if st.button("🏠 Back to round 1", use_container_width=True):
                start_new_game(force=True)
                st.rerun()

    else:
        current_round = st.session_state.round_index + 1
        total_rounds = len(st.session_state.rounds)
        prop = st.session_state.rounds[st.session_state.round_index]

        progress_pct = int((current_round - 1) / total_rounds * 100)
        st.progress(progress_pct, text=f"Round {current_round} of {total_rounds}")

        st.markdown("## Current property")

        st.markdown('<div class="panel">', unsafe_allow_html=True)

        image_path = APP_DIR / prop["imagePath"]
        if image_path.exists():
            st.image(str(image_path), caption=prop["title"], width="stretch")
        else:
            st.warning(f"Image not found: {prop['imagePath']}")

        st.markdown(
            f"""
            <div style="margin-top: 0.3rem;">
                <span class="pill">📍 {prop['town']}, {prop['region']}</span>
                <span class="pill">🏷️ {prop['propertyType']}</span>
                <span class="pill">🛏️ {prop['bedrooms']} beds</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("</div>", unsafe_allow_html=True)

        if not st.session_state.revealed:
            st.markdown("### Your guess")

            guess = st.number_input(
                "What do you think the asking price is? (£)",
                min_value=0,
                value=None,
                step=5000,
                placeholder="Enter your guess here",
                key=f"guess_round_{st.session_state.round_index}",
            )

            help_c1, help_c2 = st.columns(2)
            with help_c1:
                st.caption("Examples: 225000, 450000, 695000")
            with help_c2:
                st.caption("Think size + location together.")

            if st.button("Submit guess", type="primary", use_container_width=True):
                if guess is None:
                    st.warning("Enter a price first.")
                else:
                    submit_guess(prop, int(guess))
                    st.rerun()

        else:
            actual = prop["askingPrice"]
            guess = st.session_state.last_guess
            diff = guess - actual
            label, sublabel = feedback_band(st.session_state.last_score)

            st.markdown("### Result")

            m1, m2, m3 = st.columns(3)
            with m1:
                st.metric("Your guess", format_currency(guess), border=True)
            with m2:
                st.metric("Actual price", format_currency(actual), border=True)
            with m3:
                st.metric("Round score", f"{st.session_state.last_score:,}", border=True)

            if diff > 0:
                delta_label = f"{format_currency(abs(diff))} too high"
                delta_color = "inverse"
            elif diff < 0:
                delta_label = f"{format_currency(abs(diff))} too low"
                delta_color = "normal"
            else:
                delta_label = "Exact guess"
                delta_color = "off"

            r1, r2 = st.columns([1.25, 1])
            with r1:
                st.metric(
                    "Difference",
                    "£0" if diff == 0 else format_currency(abs(diff)),
                    delta=delta_label,
                    delta_color=delta_color,
                    border=True,
                )
            with r2:
                st.metric(
                    "Running total",
                    f"{st.session_state.total_score:,}",
                    border=True,
                )

            if diff == 0:
                st.balloons()

            st.markdown(
                f"""
                <div class="result-card">
                    <div style="font-weight: 700; font-size: 1.05rem; margin-bottom: 0.2rem;">{label}</div>
                    <div class="muted">{sublabel}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            if current_round < total_rounds:
                if st.button("Next round ➜", type="primary", use_container_width=True):
                    go_to_next_round()
                    st.rerun()
            else:
                if st.button("See final score ➜", type="primary", use_container_width=True):
                    go_to_next_round()
                    st.rerun()


# -----------------------------
# ADD PROPERTY TAB
# -----------------------------
with add_tab:
    st.markdown("## Add a new property")

    if st.session_state.admin_notice:
        st.success(st.session_state.admin_notice)
        st.session_state.admin_notice = None

    st.caption("Upload a property image and add the metadata that powers the game.")

    with st.form("add_property_form", clear_on_submit=True):
        uploaded_file = st.file_uploader(
            "Property image",
            type=["jpg", "jpeg", "png", "webp"],
        )

        col1, col2 = st.columns(2)
        with col1:
            title = st.text_input("Listing title", placeholder="e.g. 3-bed semi-detached house")
            town = st.text_input("Town / city", placeholder="e.g. Sheffield")
            region = st.text_input("Region / county", placeholder="e.g. South Yorkshire")
        with col2:
            property_type = st.text_input("Property type", placeholder="e.g. Semi-detached")
            bedrooms = st.number_input("Bedrooms", min_value=0, step=1, value=3)
            asking_price = st.number_input("Asking price (£)", min_value=0, step=5000, value=250000)

        submitted = st.form_submit_button("Save property", type="primary", use_container_width=True)

        if submitted:
            missing = []
            if uploaded_file is None:
                missing.append("image")
            if not title.strip():
                missing.append("listing title")
            if not town.strip():
                missing.append("town / city")
            if not region.strip():
                missing.append("region / county")
            if not property_type.strip():
                missing.append("property type")

            if missing:
                st.error("Please complete: " + ", ".join(missing))
            else:
                new_record = add_property_record(
                    title=title,
                    town=town,
                    region=region,
                    bedrooms=bedrooms,
                    property_type=property_type,
                    asking_price=asking_price,
                    uploaded_file=uploaded_file,
                )

                start_new_game(force=True)
                st.session_state.admin_notice = (
                    f"Added: {new_record['title']} in {new_record['town']} for {format_currency(new_record['askingPrice'])}."
                )
                st.rerun()

    st.markdown("### Quick notes")
    st.markdown(
        """
        - Use clear property photos with good lighting  
        - Keep titles simple and consistent  
        - If you add a lot of new properties, hit **Restart current game** in the sidebar to refresh the round pool
        """
    )


# -----------------------------
# LIBRARY TAB
# -----------------------------
with library_tab:
    st.markdown("## Property library")

    if not properties_all:
        st.info("No properties yet — add your first one in the 'Add Property' tab.")
    else:
        st.caption(f"{len(properties_all)} properties currently in the bank.")

        stats1, stats2, stats3 = st.columns(3)
        with stats1:
            st.metric("Total properties", len(properties_all), border=True)
        with stats2:
            avg_price = round(sum(p["askingPrice"] for p in properties_all) / len(properties_all))
            st.metric("Average price", format_currency(avg_price), border=True)
        with stats3:
            avg_beds = round(sum(p["bedrooms"] for p in properties_all) / len(properties_all), 1)
            st.metric("Average bedrooms", avg_beds, border=True)

        search = st.text_input("Search library", placeholder="Search by town, region, type, or title")

        filtered = properties_all
        if search.strip():
            q = search.strip().lower()
            filtered = [
                p for p in properties_all
                if q in p["title"].lower()
                or q in p["town"].lower()
                or q in p["region"].lower()
                or q in p["propertyType"].lower()
            ]

        if not filtered:
            st.warning("No properties matched that search.")
        else:
            cols = st.columns(2)
            for idx, prop in enumerate(filtered):
                with cols[idx % 2]:
                    st.markdown('<div class="library-card">', unsafe_allow_html=True)

                    image_path = APP_DIR / prop["imagePath"]
                    if image_path.exists():
                        st.image(str(image_path), width="stretch")
                    else:
                        st.warning(f"Missing image: {prop['imagePath']}")

                    st.markdown(
                        f"""
                        <div class="library-title">{prop['title']}</div>
                        <div class="muted">{prop['town']}, {prop['region']}</div>
                        """,
                        unsafe_allow_html=True,
                    )

                    st.markdown(
                        f"""
                        <div style="margin-top: 0.45rem;">
                            <span class="pill">💷 {format_currency(prop['askingPrice'])}</span>
                            <span class="pill">🏷️ {prop['propertyType']}</span>
                            <span class="pill">🛏️ {prop['bedrooms']} beds</span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    st.caption(f"Image path: {prop['imagePath']}")
                    st.markdown("</div>", unsafe_allow_html=True)


st.divider()

with st.expander("How scoring works"):
    st.write(
        """
- Exact guess = **5000 points**
- Bigger misses score less
- Daily Challenge gives everyone the same 5 properties for that chosen date
- Practice Mode reshuffles so you can keep testing the concept
- The Add Property tab lets you expand the game without editing JSON by hand
"""
    )