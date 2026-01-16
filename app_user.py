import os
import re
import hashlib
from datetime import datetime, timezone

import streamlit as st
import pandas as pd

from recombee_api_client.api_client import RecombeeClient
from recombee_api_client.api_requests import (
    AddUser,
    AddUserProperty,
    SetUserValues,
    GetUserValues,
    GetItemValues,
    RecommendItemsToUser,
    RecommendItemsToItem,
    AddDetailView,
    AddRating,
)

# ---------------------------------------------------------
# Recombee Config
# ---------------------------------------------------------
RECOMBEE_DB = os.getenv("RECOMBEE_DB", "sisteme-de-recomandare-upb-dev")
RECOMBEE_TOKEN = os.getenv(
    "RECOMBEE_TOKEN",
    "TYn7x2wy7S9bzzMDUXkxbw22QrBTvzXAiCvtKKl0dG9xfaXDpemDpPavgFLaVpyp",
)
client = RecombeeClient(RECOMBEE_DB, RECOMBEE_TOKEN)

SCENARIO_USER = "recommend_items_to_user"
SCENARIO_ITEM = "recommend_items_to_item"
SCENARIO_CATALOG = "catalog_popular"  # recomandat: scenariu fara filters/boosters

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUTH_FILE = os.path.join(BASE_DIR, "auth_users.csv")
INTERACTIONS_DIR = os.path.join(BASE_DIR, "interactions")


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------
def sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def sanitize_username(username: str) -> str:
    u = (username or "").strip().lower()
    u = re.sub(r"[^a-z0-9._-]", "_", u)
    return u


def make_recombee_user_id(username: str) -> str:
    return f"app_{sanitize_username(username)}"


def ensure_auth_file():
    if not os.path.exists(AUTH_FILE):
        pd.DataFrame(columns=["username", "password_hash", "recombee_user_id"]).to_csv(
            AUTH_FILE, index=False
        )


def load_users() -> pd.DataFrame:
    ensure_auth_file()
    return pd.read_csv(AUTH_FILE)


def save_users(df: pd.DataFrame):
    df.to_csv(AUTH_FILE, index=False)


def ensure_recombee_user(user_id: str):
    try:
        client.send(AddUser(user_id))
    except Exception:
        pass


def num_or_zero(v) -> float:
    try:
        if v is None:
            return 0.0
        return float(v)
    except Exception:
        return 0.0


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def fmt_ts(ts: str) -> str:
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.astimezone().strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return ts


def safe_get_item_values(item_id: str) -> dict:
    """
    Ia item-ul din Recombee. Dacă ID-ul e numeric, încearcă și variante cu zero-padding
    (caz clasic: dataset cu ID-uri de tip '00390').
    """
    item_id = str(item_id)

    # 1) try direct
    try:
        return client.send(GetItemValues(item_id))
    except Exception:
        pass

    # 2) try padded variants if numeric
    if item_id.isdigit():
        for width in (4, 5, 6):
            cand = item_id.zfill(width)
            try:
                return client.send(GetItemValues(cand))
            except Exception:
                continue

    # 3) give up
    raise Exception(f"Item {item_id} not found in Recombee (tried padding too).")


# ---------------------------------------------------------
# Recombee user properties
# ---------------------------------------------------------
USER_PROPS_MAIN = {
    "first_name": "string",
    "last_name": "string",
    "age": "int",
    "city": "string",
    "budget": "double",
    "fuel_preference": "string",
    "transmission_preference": "string",
    "preferred_seller": "string",
}
USER_PROPS_COMPAT = {
    "fuel": "string",
    "transmission": "string",
    "seller_type": "string",
    "max_price": "double",
}
USER_PROPS_OLD_TO_CLEAR = ["owner", "min_year", "max_km_driven"]


@st.cache_resource
def ensure_user_properties_once():
    for d in (USER_PROPS_MAIN, USER_PROPS_COMPAT):
        for prop, typ in d.items():
            try:
                client.send(AddUserProperty(prop, typ))
            except Exception:
                pass
    return True


# ---------------------------------------------------------
# Local interactions logging
# ---------------------------------------------------------
def ensure_interactions_dir():
    os.makedirs(INTERACTIONS_DIR, exist_ok=True)


def interactions_path(user_id: str, kind: str) -> str:
    ensure_interactions_dir()
    safe_user = re.sub(r"[^a-zA-Z0-9._-]", "_", user_id)
    return os.path.join(INTERACTIONS_DIR, f"{safe_user}_{kind}.csv")


def append_interaction(user_id: str, item_id: str, kind: str):
    path = interactions_path(user_id, kind)
    row = {"ts": utc_now_iso(), "user_id": user_id, "item_id": str(item_id)}

    if os.path.exists(path):
        try:
            df = pd.read_csv(path)
        except Exception:
            df = pd.DataFrame(columns=["ts", "user_id", "item_id"])
    else:
        df = pd.DataFrame(columns=["ts", "user_id", "item_id"])

    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_csv(path, index=False)

    st.toast(f"Salvat {kind}: {item_id}", icon="✅")


def load_interactions(user_id: str, kind: str) -> pd.DataFrame:
    path = interactions_path(user_id, kind)
    if not os.path.exists(path):
        return pd.DataFrame(columns=["ts", "user_id", "item_id"])
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame(columns=["ts", "user_id", "item_id"])


def unique_recent_item_ids(df: pd.DataFrame, limit: int = 200) -> list[str]:
    if df.empty:
        return []
    d = df.copy()
    if "ts" in d.columns:
        d = d.sort_values("ts", ascending=False)
    seen = set()
    out = []
    for item_id in d["item_id"].astype(str).tolist():
        if item_id not in seen:
            seen.add(item_id)
            out.append(item_id)
        if len(out) >= limit:
            break
    return out


def get_interaction_sets(user_id: str) -> tuple[set[str], set[str]]:
    df_l = load_interactions(user_id, "likes")
    df_v = load_interactions(user_id, "views")
    likes = set(df_l["item_id"].astype(str).tolist()) if not df_l.empty else set()
    views = set(df_v["item_id"].astype(str).tolist()) if not df_v.empty else set()
    return likes, views


# ---------------------------------------------------------
# Styling
# ---------------------------------------------------------
st.markdown(
    """
<style>
body, .stApp { background-color: #1a1a1a; color: #ffffff; }
.card {
    background-color: #2a2a2a; padding: 18px 22px; border-radius: 10px;
    border: 1px solid #3a3a3a; margin-bottom: 18px; box-shadow: 0 1px 3px rgba(0,0,0,0.45);
}
.card-title { font-size: 22px; font-weight: 600; color: #ffffff; margin-bottom: 6px; }
.prop-row { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #444444; }
.prop-label { color: #cccccc; font-weight: 500; }
.prop-value { color: #ffffff; }
h1, h2, h3, h4 { color: #ffffff !important; }
span, p, label, .stTextInput, .stButton, .stMarkdown { color: #ffffff !important; }
.badge {
  display:inline-block; padding:4px 10px; border-radius:999px;
  border:1px solid #3a3a3a; margin-right:8px; font-size:12px;
}
.badge-like { background:#2b1f2b; border-color:#4a2a4a; }
.badge-view { background:#1f2b3b; border-color:#2a4a68; }
</style>
""",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# UI helpers
# ---------------------------------------------------------
def render_car_card(details: dict, is_liked: bool = False, is_viewed: bool = False):
    badges = []
    if is_liked:
        badges.append("<span class='badge badge-like'>❤️ Apreciată</span>")
    if is_viewed:
        badges.append("<span class='badge badge-view'>👀 Vizualizată</span>")

    badge_html = ""
    if badges:
        badge_html = "<div style='margin-top:6px; margin-bottom:10px;'>" + "".join(badges) + "</div>"

    st.markdown(
        f"<div class='card'><div class='card-title'>{details.get('name', 'Fără nume')}</div>{badge_html}",
        unsafe_allow_html=True,
    )

    keys_order = ["year", "fuel", "transmission", "km_driven", "selling_price", "seller_type", "owner"]
    for key in keys_order:
        if key in details:
            st.markdown(
                f"<div class='prop-row'><span class='prop-label'>{key}</span>"
                f"<span class='prop-value'>{details[key]}</span></div>",
                unsafe_allow_html=True,
            )
    st.markdown("</div>", unsafe_allow_html=True)


def render_list_meta(title: str, df: pd.DataFrame, kind: str):
    total = 0 if df is None or df.empty else len(df)
    last_ts = ""
    if df is not None and not df.empty and "ts" in df.columns:
        try:
            last_ts = fmt_ts(df.sort_values("ts", ascending=False).iloc[0]["ts"])
        except Exception:
            last_ts = ""

    st.markdown(
        f"""
        <div class='card'>
          <div class='card-title'>{title}</div>
          <div class='prop-row'><span class='prop-label'>Total {kind}</span><span class='prop-value'>{total}</span></div>
          <div class='prop-row'><span class='prop-label'>Ultima interacțiune</span><span class='prop-value'>{last_ts or "-"}</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def track_buttons(logged_user_id: str, item_id: str, prefix: str = "", slot: str = ""):
    k_seen = f"{prefix}seen_{item_id}_{slot}"
    k_like = f"{prefix}like_{item_id}_{slot}"

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Am văzut", key=k_seen):
            try:
                client.send(AddDetailView(logged_user_id, item_id, cascade_create=True))
            except Exception:
                pass
            append_interaction(logged_user_id, item_id, "views")

            st.session_state.pop("recs_cache_key", None)
            st.session_state.pop("recs_ids", None)
            st.session_state.pop("recs_mode", None)

    with c2:
        if st.button("Îmi place", key=k_like):
            try:
                client.send(AddRating(logged_user_id, item_id, 1, cascade_create=True))
            except Exception:
                pass
            append_interaction(logged_user_id, item_id, "likes")

            st.session_state.pop("recs_cache_key", None)
            st.session_state.pop("recs_ids", None)
            st.session_state.pop("recs_mode", None)


def reset_profile_in_recombee(user_id: str):
    ensure_user_properties_once()
    ensure_recombee_user(user_id)

    payload = {k: None for k in USER_PROPS_MAIN.keys()}
    payload.update({k: None for k in USER_PROPS_COMPAT.keys()})
    for k in USER_PROPS_OLD_TO_CLEAR:
        payload[k] = None

    try:
        client.send(SetUserValues(user_id, payload, cascade_create=True))
    except Exception:
        pass

    st.session_state.pop("recs_cache_key", None)
    st.session_state.pop("recs_ids", None)
    st.session_state.pop("recs_mode", None)


# ---------------------------------------------------------
# Auth UI
# ---------------------------------------------------------
def login_register_view():
    st.title("Autentificare")
    tabs = st.tabs(["Login", "Register"])

    with tabs[0]:
        username = st.text_input("Username", key="login_user")
        password = st.text_input("Password", type="password", key="login_pw")

        if st.button("Login", key="btn_login"):
            username = (username or "").strip()
            password = password or ""

            if not username or not password:
                st.error("Completează username și password.")
                return

            df = load_users()
            row = df[df["username"] == username]
            if row.empty:
                st.error("User inexistent. Fă register.")
                return

            if sha256(password) != row.iloc[0]["password_hash"]:
                st.error("Parolă greșită.")
                return

            user_id = row.iloc[0]["recombee_user_id"]
            ensure_user_properties_once()
            ensure_recombee_user(user_id)

            st.session_state["auth"] = True
            st.session_state["username"] = username
            st.session_state["user_id"] = user_id

            st.session_state.pop("recs_cache_key", None)
            st.session_state.pop("recs_ids", None)
            st.session_state.pop("recs_mode", None)
            st.session_state.pop("catalog_ids", None)

            st.rerun()

    with tabs[1]:
        username = st.text_input("Username nou", key="reg_user")
        password = st.text_input("Password nou", type="password", key="reg_pw")
        password2 = st.text_input("Confirmă password", type="password", key="reg_pw2")

        if st.button("Register", key="btn_register"):
            username = (username or "").strip()
            password = password or ""
            password2 = password2 or ""

            if not username or not password:
                st.error("Completează username și password.")
                return
            if password != password2:
                st.error("Parolele nu coincid.")
                return

            df = load_users()
            if not df[df["username"] == username].empty:
                st.error("Username deja folosit.")
                return

            user_id = make_recombee_user_id(username)
            ensure_user_properties_once()
            ensure_recombee_user(user_id)

            df = pd.concat(
                [
                    df,
                    pd.DataFrame(
                        [{"username": username, "password_hash": sha256(password), "recombee_user_id": user_id}]
                    ),
                ],
                ignore_index=True,
            )
            save_users(df)
            st.success("Cont creat. Acum fă login.")


def logout_button():
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()


# ---------------------------------------------------------
# Catalog (fără profil)
# ---------------------------------------------------------
def catalog_view(logged_user_id: str):
    st.title("Catalog mașini (fără profil)")

    ensure_user_properties_once()
    ensure_recombee_user("anon_user")

    likes_set, views_set = get_interaction_sets(logged_user_id)

    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("Refresh catalog", key="btn_refresh_catalog"):
            st.session_state.pop("catalog_ids", None)
            st.rerun()
    with col2:
        st.write("Listă de mașini fără profil. Recomandat: scenariu `catalog_popular` fără Filters/Boosters.")

    n = st.slider("Număr mașini", min_value=10, max_value=100, value=50, step=10, key="catalog_slider")

    if st.session_state.get("catalog_ids"):
        ids = st.session_state["catalog_ids"][:n]
    else:
        ids = []

        try:
            resp = client.send(
                RecommendItemsToUser(
                    user_id="anon_user",
                    count=max(100, n),
                    scenario=SCENARIO_CATALOG,
                )
            )
            ids = [r["id"] for r in (resp.get("recomms", []) or [])][:n]
        except Exception:
            ids = []

        if not ids:
            try:
                resp = client.send(
                    RecommendItemsToUser(
                        user_id="anon_user",
                        count=max(100, n),
                    )
                )
                ids = [r["id"] for r in (resp.get("recomms", []) or [])][:n]
            except Exception:
                ids = []

        if ids:
            st.session_state["catalog_ids"] = ids

    if not ids:
        st.info(
            "Catalog gol. Creează în Recombee scenariul `catalog_popular` fără Filters/Boosters "
            "sau testează RecommendItemsToUser pentru user `anon_user`."
        )
        return

    cars = []
    for item_id in ids:
        try:
            details = client.send(GetItemValues(item_id))
            details["_rid"] = str(item_id)
            cars.append(details)
        except Exception:
            pass

    cars = sorted(cars, key=lambda x: num_or_zero(x.get("selling_price")), reverse=True)

    for idx, d in enumerate(cars):
        rid = str(d.get("_rid"))
        render_car_card(d, is_liked=(rid in likes_set), is_viewed=(rid in views_set))
        track_buttons(logged_user_id, rid, prefix="cat_", slot=str(idx))


# ---------------------------------------------------------
# Profile
# ---------------------------------------------------------
def profile_view(user_id: str):
    st.title("Profil utilizator")
    ensure_user_properties_once()
    ensure_recombee_user(user_id)

    try:
        current = client.send(GetUserValues(user_id)) or {}
    except Exception:
        current = {}

    c_reset, c_save = st.columns([1, 1])

    with c_reset:
        if st.button("Reset profil"):
            reset_profile_in_recombee(user_id)
            for k in [
                "p_first_name", "p_last_name", "p_age", "p_city",
                "p_budget", "p_fuel_pref", "p_trans_pref", "p_pref_seller"
            ]:
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()

    first_name = st.text_input("first_name", value=str(current.get("first_name") or ""), key="p_first_name")
    last_name = st.text_input("last_name", value=str(current.get("last_name") or ""), key="p_last_name")

    age_val = current.get("age")
    try:
        age_val = int(age_val) if age_val is not None else 26
    except Exception:
        age_val = 26
    age = st.number_input("age", min_value=0, max_value=120, value=int(age_val), step=1, key="p_age")

    city = st.text_input("city", value=str(current.get("city") or ""), key="p_city")

    budget_val = current.get("budget")
    try:
        budget_val = float(budget_val) if budget_val is not None else 650000.0
    except Exception:
        budget_val = 650000.0
    budget = st.number_input("budget", min_value=0.0, value=float(budget_val), step=5000.0, key="p_budget")

    fuel_options = ["", "Petrol", "Diesel", "Electric", "Hybrid", "CNG", "LPG"]
    fuel_pref_current = current.get("fuel_preference")
    fuel_preference = st.selectbox(
        "fuel_preference",
        fuel_options,
        index=fuel_options.index(fuel_pref_current) if fuel_pref_current in fuel_options else 0,
        key="p_fuel_pref",
    )

    trans_options = ["", "Manual", "Automatic"]
    trans_pref_current = current.get("transmission_preference")
    transmission_preference = st.selectbox(
        "transmission_preference",
        trans_options,
        index=trans_options.index(trans_pref_current) if trans_pref_current in trans_options else 0,
        key="p_trans_pref",
    )

    seller_options = ["", "Individual", "Dealer"]
    seller_current = current.get("preferred_seller")
    preferred_seller = st.selectbox(
        "preferred_seller",
        seller_options,
        index=seller_options.index(seller_current) if seller_current in seller_options else 0,
        key="p_pref_seller",
    )

    with c_save:
        if st.button("Salvează profilul"):
            values = {
                "first_name": first_name or None,
                "last_name": last_name or None,
                "age": int(age),
                "city": city or None,
                "budget": float(budget),
                "fuel_preference": fuel_preference or None,
                "transmission_preference": transmission_preference or None,
                "preferred_seller": preferred_seller or None,

                "fuel": fuel_preference or None,
                "transmission": transmission_preference or None,
                "seller_type": preferred_seller or None,
                "max_price": float(budget),
            }

            for k in USER_PROPS_OLD_TO_CLEAR:
                values[k] = None

            try:
                client.send(SetUserValues(user_id, values, cascade_create=True))
                st.session_state.pop("recs_cache_key", None)
                st.session_state.pop("recs_ids", None)
                st.session_state.pop("recs_mode", None)
                st.success("Profil salvat în Recombee.")
            except Exception as e:
                st.error(f"Eroare la SetUserValues: {e}")


# ---------------------------------------------------------
# Recommendations (AUTO, 50)
# ---------------------------------------------------------
def recommend_for_logged_user_view(user_id: str):
    st.title("Recomandări pentru mine (auto, 50)")

    likes_set, views_set = get_interaction_sets(user_id)

    col_a, col_b = st.columns([1, 3])
    with col_a:
        if st.button("Refresh recomandări", key="btn_refresh_recs"):
            st.session_state.pop("recs_cache_key", None)
            st.session_state.pop("recs_ids", None)
            st.session_state.pop("recs_mode", None)
            st.rerun()

    with col_b:
        st.write(f"User: `{st.session_state.get('username', '')}` ({user_id})")

    try:
        u = client.send(GetUserValues(user_id)) or {}
    except Exception:
        u = {}

    cache_key = (
        user_id,
        u.get("fuel_preference"),
        u.get("transmission_preference"),
        u.get("preferred_seller"),
        u.get("budget"),
    )

    if st.session_state.get("recs_cache_key") == cache_key and st.session_state.get("recs_ids"):
        ids = st.session_state["recs_ids"]
    else:
        ids = []
        try:
            resp = client.send(
                RecommendItemsToUser(
                    user_id=user_id,
                    count=50,
                    scenario=SCENARIO_USER,
                )
            )
            ids = [r["id"] for r in (resp.get("recomms", []) or [])]
        except Exception:
            ids = []

        if ids:
            st.session_state["recs_cache_key"] = cache_key
            st.session_state["recs_ids"] = ids
        else:
            st.session_state.pop("recs_cache_key", None)
            st.session_state.pop("recs_ids", None)

    if not ids:
        st.info("Nu am găsit rezultate. Verifică Preview Results în Recombee pentru userul ăsta.")
        return

    cars = []
    for item_id in ids:
        try:
            details = client.send(GetItemValues(item_id))
            details["_rid"] = str(item_id)
            cars.append(details)
        except Exception:
            pass

    cars = sorted(cars, key=lambda x: num_or_zero(x.get("selling_price")), reverse=True)

    for idx, d in enumerate(cars):
        rid = str(d.get("_rid"))
        render_car_card(d, is_liked=(rid in likes_set), is_viewed=(rid in views_set))
        track_buttons(user_id, rid, prefix="auto_", slot=str(idx))


def recommend_by_item_view(user_id: str):
    st.title("Recomandări de mașini similare (Items → Item)")
    item_id = st.text_input("ID-ul mașinii de referință", key="item_input")

    if not item_id.strip():
        st.caption("Introdu un item_id (ex: 00390) ca să vezi similarități.")
        return

    likes_set, views_set = get_interaction_sets(user_id)

    try:
        details = client.send(GetItemValues(item_id))
        details["_rid"] = str(item_id)
        st.subheader("📌 Mașina de referință")
        render_car_card(details, is_liked=(str(item_id) in likes_set), is_viewed=(str(item_id) in views_set))

        response = client.send(
            RecommendItemsToItem(
                item_id=item_id,
                target_user_id=user_id,
                count=10,
                scenario=SCENARIO_ITEM,
            )
        )
        recomms = response.get("recomms", []) or []

        st.subheader("🚗 Rezultate recomandate")
        if not recomms:
            st.warning("Nu am găsit mașini similare.")
            return

        for idx, r in enumerate(recomms):
            rid = str(r["id"])
            try:
                vals = client.send(GetItemValues(rid))
                vals["_rid"] = rid
                render_car_card(vals, is_liked=(rid in likes_set), is_viewed=(rid in views_set))
                track_buttons(user_id, rid, prefix="it_", slot=str(idx))
            except Exception:
                st.error(f"Nu pot încărca item-ul {rid}")

    except Exception as e:
        st.error(f"Eroare: {e}")


# ---------------------------------------------------------
# Favorites / Viewed pages
# ---------------------------------------------------------
def liked_view(user_id: str):
    st.title("❤️ Apreciate")

    df = load_interactions(user_id, "likes")
    render_list_meta("Apreciate (local)", df, "like-uri")

    likes_set, views_set = get_interaction_sets(user_id)

    ids = unique_recent_item_ids(df, limit=200)
    if not ids:
        st.info("Nu ai aprecieri încă.")
        return

    max_n = min(200, len(ids))
    default_n = min(50, max_n)

    # FIX: dacă max_n e 1, nu afișăm slider (Streamlit cere min < max)
    if max_n <= 1:
        n = max_n
    else:
        slider_key = f"liked_slider_{max_n}"
        n = st.slider(
            "Număr mașini",
            min_value=1,
            max_value=max_n,
            value=default_n,
            step=1,
            key=slider_key,
        )

    ids = ids[:n]

    cars = []
    missing = 0
    for item_id in ids:
        try:
            details = safe_get_item_values(str(item_id))
            details["_rid"] = str(item_id)
            cars.append(details)
        except Exception as e:
            missing += 1
            st.caption(f"Nu pot încărca item_id={item_id} din Recombee: {e}")

    cars = sorted(cars, key=lambda x: num_or_zero(x.get("selling_price")), reverse=True)

    if missing:
        st.caption(f"{missing} item-uri nu au putut fi încărcate din Recombee (șterse, id invalid sau padding diferit).")

    for idx, d in enumerate(cars):
        rid = str(d.get("_rid"))
        render_car_card(d, is_liked=(rid in likes_set), is_viewed=(rid in views_set))
        track_buttons(user_id, rid, prefix="likepage_", slot=str(idx))


def viewed_view(user_id: str):
    st.title("👀 Vizualizate")

    df = load_interactions(user_id, "views")
    render_list_meta("Vizualizate (local)", df, "vizualizări")

    likes_set, views_set = get_interaction_sets(user_id)

    ids = unique_recent_item_ids(df, limit=200)
    if not ids:
        st.info("Nu ai vizualizări încă.")
        return

    max_n = min(200, len(ids))
    default_n = min(50, max_n)

    # FIX: dacă max_n e 1, nu afișăm slider (Streamlit cere min < max)
    if max_n <= 1:
        n = max_n
    else:
        slider_key = f"viewed_slider_{max_n}"
        n = st.slider(
            "Număr mașini",
            min_value=1,
            max_value=max_n,
            value=default_n,
            step=1,
            key=slider_key,
        )

    ids = ids[:n]

    cars = []
    missing = 0
    for item_id in ids:
        try:
            details = safe_get_item_values(str(item_id))
            details["_rid"] = str(item_id)
            cars.append(details)
        except Exception as e:
            missing += 1
            st.caption(f"Nu pot încărca item_id={item_id} din Recombee: {e}")

    cars = sorted(cars, key=lambda x: num_or_zero(x.get("selling_price")), reverse=True)

    if missing:
        st.caption(f"{missing} item-uri nu au putut fi încărcate din Recombee (șterse, id invalid sau padding diferit).")

    for idx, d in enumerate(cars):
        rid = str(d.get("_rid"))
        render_car_card(d, is_liked=(rid in likes_set), is_viewed=(rid in views_set))
        track_buttons(user_id, rid, prefix="viewpage_", slot=str(idx))


# ---------------------------------------------------------
# App router
# ---------------------------------------------------------
def app():
    st.sidebar.title("Meniu")

    if "auth" not in st.session_state:
        st.session_state["auth"] = False

    if not st.session_state["auth"]:
        login_register_view()
        return

    logout_button()

    user_id = st.session_state["user_id"]
    ensure_user_properties_once()
    ensure_recombee_user(user_id)

    st.sidebar.write(
        f"Likes: {len(load_interactions(user_id,'likes'))} | Views: {len(load_interactions(user_id,'views'))}"
    )

    page = st.sidebar.radio(
        "Pagini",
        [
            "📋 Catalog mașini (fără profil)",
            "Profil",
            "👤 Recomandări pentru mine",
            "🔍 Recomandări după ITEM",
            "❤️ Apreciate",
            "👀 Vizualizate",
        ],
    )

    if page == "📋 Catalog mașini (fără profil)":
        catalog_view(user_id)
    elif page == "Profil":
        profile_view(user_id)
    elif page == "👤 Recomandări pentru mine":
        recommend_for_logged_user_view(user_id)
    elif page == "🔍 Recomandări după ITEM":
        recommend_by_item_view(user_id)
    elif page == "❤️ Apreciate":
        liked_view(user_id)
    else:
        viewed_view(user_id)


if __name__ == "__main__":
    app()
