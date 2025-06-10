import streamlit as st
import pandas as pd
import requests
import folium
from streamlit_folium import st_folium
from streamlit_option_menu import option_menu
from streamlit_authenticator import Authenticate

API_KEY = 
st.title("Bienvenue sur l'application des parcs et jardins de Bruxelles 🌳")

# Authentification
lesDonneesDesComptes = {
    'usernames': {
        'utilisateur': {
            'name': 'utilisateur',
            'password': 'utilisateurMDP',
            'email': 'utilisateur@gmail.com',
            'role': 'utilisateur'
        },
        'root': {
            'name': 'root',
            'password': 'rootMDP',
            'email': 'admin@gmail.com',
            'role': 'admin'
        }
    }
}

authenticator = Authenticate(
    lesDonneesDesComptes,
    "cookie-name",
    "cookie-key",
    30
)

# ========== MENU ==========

selection = option_menu(
    menu_title=None,
    options=["Accueil", "Parcs et jardins de Bruxelles"]
)

# ========== DONNÉES DES PARCS ==========

@st.cache_data
def charger_parcs():
    url = "https://opendata.brussels.be/api/explore/v2.1/catalog/datasets/bruxelles_parcs_et_jardins/records?limit=100"
    res = requests.get(url)
    if res.ok:
        return pd.DataFrame(res.json().get("results", []))
    else:
        return pd.DataFrame()

df = charger_parcs()

def transforme(coord_dict):
    return list(coord_dict.values()) if coord_dict else [None, None]

df['couple_lon_lat'] = df['geo_coordinates'].apply(transforme)
df[['lon', 'lat']] = pd.DataFrame(df['couple_lon_lat'].tolist(), index=df.index)
df = df.dropna(subset=['lat', 'lon'])
list_lieu = df['description'].dropna().unique().tolist()

# ========== PAGE ACCUEIL ==========

if selection == "Accueil":
    st.title("🗺️ Carte des parcs et jardins de Bruxelles")

    lieu_select = st.selectbox("Choisissez un parc :", list_lieu)

    df_selection = df[df['description'] == lieu_select]
    if not df_selection.empty:
        lat = df_selection.iloc[0]['lat']
        lon = df_selection.iloc[0]['lon']
        m = folium.Map(location=[lat, lon], zoom_start=15)
        folium.Marker(
            location=[lat, lon],
            popup=lieu_select,
            tooltip=lieu_select,
            icon=folium.Icon(color="green", icon="info-sign")
        ).add_to(m)
        st_folium(m, width=700, height=500)
    else:
        st.warning("Aucun parc trouvé.")

# ========== PAGE VIDÉOS (AVEC AUTH) ==========

elif selection == "Parcs et jardins de Bruxelles":
    st.title("🎥 Vidéos des parcs de Bruxelles")

    authenticator.login()

    if st.session_state["authentication_status"]:
        st.success(f"Connecté en tant que {st.session_state['name']}")
        authenticator.logout("Déconnexion")

        lieu_select = st.selectbox("Choisissez un parc :", list_lieu)

        def API_address(lieu):
            headers = {'User-Agent': 'Mozilla/5.0'}
            params = {'q': lieu, 'format': 'json', 'limit': 1}
            url = 'https://nominatim.openstreetmap.org/search'
            r = requests.get(url, headers=headers, params=params)
            data = r.json()
            if data:
                return data[0]['lat'], data[0]['lon']
            return None, None

        def chercher_video_youtube(lieu, api_key):
            lat, lon = API_address(lieu)
            params = {
                "part": "snippet",
                "q": lieu,
                "type": "video",
                "maxResults": 1,
                "key": api_key
            }
            if lat and lon:
                params["location"] = f"{lat},{lon}"
                params["locationRadius"] = "10km"

            r = requests.get("https://www.googleapis.com/youtube/v3/search", params=params)
            items = r.json().get("items", [])
            if items:
                return f"https://www.youtube.com/watch?v={items[0]['id']['videoId']}"
            return None

        if st.button("🔍 Rechercher une vidéo"):
            video_url = chercher_video_youtube(lieu_select, API_KEY)
            if video_url:
                st.video(video_url)
            else:
                st.warning("Aucune vidéo trouvée pour ce lieu.")
    
    elif st.session_state["authentication_status"] is False:
        st.error("Identifiants incorrects")
    elif st.session_state["authentication_status"] is None:
        st.warning("Veuillez entrer vos identifiants")