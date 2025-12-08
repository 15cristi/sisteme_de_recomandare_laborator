import streamlit as st
from recombee_api_client.api_client import RecombeeClient
from recombee_api_client.api_requests import *
from recombee_api_client.exceptions import ResponseException
import pandas as pd

# ---------------------------------------------------------
# Recombee Config
# ---------------------------------------------------------
client = RecombeeClient(
    'sisteme-de-recomandare-upb-dev',
    'TYn7x2wy7S9bzzMDUXkxbw22QrBTvzXAiCvtKKl0dG9xfaXDpemDpPavgFLaVpyp'
)

# Creăm user fallback
try:
    client.send(AddUser("anon_user"))
except:
    pass


st.markdown("""
<style>
body, .stApp {
    background-color: #1a1a1a;
    color: #ffffff;
}

/* Card */
.card {
    background-color: #2a2a2a;
    padding: 18px 22px;
    border-radius: 10px;
    border: 1px solid #3a3a3a;
    margin-bottom: 18px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.45);
}

/* Card title */
.card-title {
    font-size: 22px;
    font-weight: 600;
    color: #ffffff;
    margin-bottom: 12px;
}

/* Rows */
.prop-row {
    display: flex;
    justify-content: space-between;
    padding: 6px 0;
    border-bottom: 1px solid #444444;
}

.prop-label {
    color: #cccccc;
    font-weight: 500;
}

.prop-value {
    color: #ffffff;
}

/* Titles */
h1, h2, h3, h4 {
    color: #ffffff !important;
}

/* General text */
span, p, label, .stTextInput, .stButton, .stMarkdown {
    color: #ffffff !important;
}
</style>
""", unsafe_allow_html=True)


tab1, tab2 = st.tabs(["🔍 Recomandări după ITEM", "👤 Recomandări pentru USER"])



with tab1:
    st.title("Recomandări de mașini similare (Items → Item)")

    item_id = st.text_input("ID-ul mașinii de referință", key="item_input")

    generate_item = st.button("Generează recomandări (Item)", key="btn_item")

    if generate_item:
        if not item_id.strip():
            st.error("Te rog introdu un ID de mașină valid.")
        else:
            st.subheader("📌 Mașina de referință")

            try:
                details = client.send(GetItemValues(item_id))

                st.markdown(
                    f"<div class='card'><div class='card-title'>{details.get('name','Fără nume')}</div>",
                    unsafe_allow_html=True
                )

                for k, v in details.items():
                    st.markdown(
                        f"<div class='prop-row'><span class='prop-label'>{k}</span>"
                        f"<span class='prop-value'>{v}</span></div>",
                        unsafe_allow_html=True
                    )

                st.markdown("</div>", unsafe_allow_html=True)

                # Recomandări
                response = client.send(RecommendItemsToItem(
                    item_id=item_id,
                    target_user_id="anon_user",
                    count=10,
                    scenario="recommend_items_to_item"
                ))

                recomms = response.get("recomms", [])

                st.subheader("🚗 Rezultate recomandate")

                if not recomms:
                    st.warning("Nu am găsit mașini similare.")
                else:
                    for r in recomms:
                        rid = r["id"]
                        try:
                            vals = client.send(GetItemValues(rid))

                            st.markdown(
                                f"<div class='card'><div class='card-title'>{vals.get('name','Fără nume')}</div>",
                                unsafe_allow_html=True
                            )

                            keys_order = ["year", "fuel", "transmission", "km_driven",
                                        "selling_price", "seller_type", "owner"]

                            for key in keys_order:
                                if key in vals:
                                    st.markdown(
                                        f"<div class='prop-row'><span class='prop-label'>{key}</span>"
                                        f"<span class='prop-value'>{vals[key]}</span></div>",
                                        unsafe_allow_html=True
                                    )

                            st.markdown("</div>", unsafe_allow_html=True)

                        except:
                            st.error(f"Nu pot încărca item-ul {rid}")

            except ResponseException as e:
                st.error(f"Eroare Recombee: {e}")



with tab2:
    st.title("Recomandări personalizate pentru utilizatori")

    user_id = st.text_input("Introdu ID-ul userului", key="user_input")

    if st.button("Generează recomandări (User)", key="btn_user"):

        if user_id.strip():
            try:
                response = client.send(RecommendItemsToUser(
                    user_id=user_id,
                    count=10,
                    scenario="recommend_items_to_user"
                ))

                st.subheader(f"Recomandări pentru user: {user_id}")

                recomms = response.get("recomms", [])

                if not recomms:
                    st.warning("Nu există recomandări pentru acest user.")
                else:

                    cars = []

                    # Preluăm detaliile fiecărei recomandări
                    for r in recomms:
                        item_id = r["id"]
                        try:
                            details = client.send(GetItemValues(item_id))
                            cars.append(details)
                        except:
                            pass

                    # Sortare după preț DESC
                    cars = sorted(cars, key=lambda x: x.get("selling_price", 0), reverse=True)

                    # Afișare carduri
                    for details in cars:
                        st.markdown(
                            f"<div class='card'><div class='card-title'>{details.get('name', 'Fără nume')}</div>",
                            unsafe_allow_html=True
                        )

                        keys_order = ["year", "fuel", "transmission", "km_driven",
                                      "selling_price", "seller_type", "owner"]

                        for key in keys_order:
                            if key in details:
                                st.markdown(
                                    f"<div class='prop-row'><span class='prop-label'>{key}</span>"
                                    f"<span class='prop-value'>{details[key]}</span></div>",
                                    unsafe_allow_html=True
                                )

                        st.markdown("</div>", unsafe_allow_html=True)

            except Exception as e:
                st.error(f"Eroare: {e}")

        else:
            st.error("Te rog introdu un user_id valid.")
