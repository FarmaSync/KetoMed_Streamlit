# app.py
import streamlit as st
import pandas as pd
from fuzzywuzzy import process
from datetime import datetime, timedelta
import os

# Constants
DRUGS_CSV = 'data/drugs.csv'
INACTIVITY_TIMEOUT = 30  # in minutes

# Initialize session state
if 'bookmarks' not in st.session_state:
    st.session_state.bookmarks = []
if 'search_history' not in st.session_state:
    st.session_state.search_history = []
if 'last_active' not in st.session_state:
    st.session_state.last_active = datetime.now()

# Function to load drug data
@st.cache(allow_output_mutation=True)
def load_drug_data():
    df = pd.read_csv(DRUGS_CSV)
    return df

# Function to perform fuzzy search
def fuzzy_search(query, choices, limit=5):
    results = process.extract(query, choices, limit=limit)
    return [result[0] for result in results]

# Function to update last active timestamp
def update_last_active():
    st.session_state.last_active = datetime.now()

# Function to check inactivity
def check_inactivity():
    now = datetime.now()
    if now - st.session_state.last_active > timedelta(minutes=INACTIVITY_TIMEOUT):
        st.session_state.bookmarks = []
        st.session_state.search_history = []
        st.warning("You have been logged out due to inactivity.")
        st.session_state.last_active = datetime.now()

# UI Components
def main_app():
    update_last_active()
    check_inactivity()
    
    st.sidebar.title("Ketomed")
    menu = ["Zoeken", "Boekmarks", "Recente Zoeken", "FAQ", "Voorwaarden", "Reset Session"]
    choice = st.sidebar.selectbox("Menu", menu)

    drug_df = load_drug_data()

    if choice == "Zoeken":
        st.header("Zoek naar een geneesmiddel")
        search_term = st.text_input("Voer merknaam of werkzame stof in")
        if search_term:
            # Fuzzy search on brand name and active component
            brand_names = drug_df['brand_name'].tolist()
            active_components = drug_df['active_component'].tolist()
            combined = brand_names + active_components
            suggestions = fuzzy_search(search_term, combined)
            results = drug_df[
                drug_df['brand_name'].str.contains('|'.join(suggestions), case=False, na=False) |
                drug_df['active_component'].str.contains('|'.join(suggestions), case=False, na=False)
            ]
            # Apply filters
            st.sidebar.subheader("Filters")
            admin_route = st.sidebar.multiselect("Toedieningsweg", options=drug_df['administration_route'].unique())
            keto_status = st.sidebar.multiselect("Ketogene Status", options=drug_df['ketogenic_status'].unique())
            if admin_route:
                results = results[results['administration_route'].isin(admin_route)]
            if keto_status:
                results = results[results['ketogenic_status'].isin(keto_status)]
            st.write(f"Aantal resultaten: {len(results)}")
            for index, row in results.iterrows():
                with st.expander(f"{row['brand_name']} ({row['active_component']})"):
                    st.write(f"**Toedieningsweg:** {row['administration_route']}")
                    st.write(f"**Ketogene Status:** {row['ketogenic_status']}")
                    # Bookmark button
                    if row['drug_id'] in st.session_state.bookmarks:
                        if st.button("Verwijder Bookmark", key=f"remove_{row['drug_id']}"):
                            st.session_state.bookmarks.remove(row['drug_id'])
                            st.success("Bookmark verwijderd.")
                    else:
                        if st.button("Bookmark Toevoegen", key=f"add_{row['drug_id']}"):
                            st.session_state.bookmarks.append(row['drug_id'])
                            st.success("Bookmark toegevoegd.")
                    # Add to search history
                    st.session_state.search_history.append({'term': search_term, 'timestamp': datetime.now()})
    
    elif choice == "Boekmarks":
        st.header("Uw Boekmarks")
        if st.session_state.bookmarks:
            bookmarked_drugs = drug_df[drug_df['drug_id'].isin(st.session_state.bookmarks)]
            for index, row in bookmarked_drugs.iterrows():
                with st.expander(f"{row['brand_name']} ({row['active_component']})"):
                    st.write(f"**Toedieningsweg:** {row['administration_route']}")
                    st.write(f"**Ketogene Status:** {row['ketogenic_status']}")
                    if st.button("Verwijder Bookmark", key=f"remove_bookmark_{row['drug_id']}"):
                        st.session_state.bookmarks.remove(row['drug_id'])
                        st.success("Bookmark verwijderd.")
        else:
            st.info("U heeft nog geen boekmarks.")
    
    elif choice == "Recente Zoeken":
        st.header("Recente Zoeken")
        if st.session_state.search_history:
            for entry in reversed(st.session_state.search_history[-10:]):
                st.write(f"{entry['term']} - {entry['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            st.info("Geen recente zoekopdrachten gevonden.")
    
    elif choice == "FAQ":
        st.header("Veelgestelde Vragen")
        st.write("""
        **Vraag 1:** Hoe gebruik ik de zoekfunctie?
        
        **Antwoord:** Voer de merknaam of werkzame stof in het zoekveld in en selecteer uit de suggesties.
        
        **Vraag 2:** Hoe voeg ik een geneesmiddel toe aan mijn boekmarks?
        
        **Antwoord:** Klik op de "Bookmark Toevoegen" knop naast het gewenste geneesmiddel.
        
        **Vraag 3:** Hoe kan ik mijn boekmarks beheren?
        
        **Antwoord:** Ga naar het "Boekmarks" menu om uw opgeslagen geneesmiddelen te bekijken of te verwijderen.
        """)
    
    elif choice == "Voorwaarden":
        st.header("Algemene Voorwaarden")
        st.write("""
        **Gebruik van Ketomed**
        
        Ketomed is bedoeld voor gebruik door geautoriseerde zorgprofessionals. Het is geen vervanging voor medisch advies.
        
        **Privacybeleid**
        
        Wij respecteren uw privacy en voldoen aan de GDPR-regelgeving. Uw gegevens worden veilig opgeslagen en niet gedeeld met derden.
        
        **Aansprakelijkheid**
        
        Ketomed is niet aansprakelijk voor eventuele fouten in de gegevens of het gebruik van de applicatie.
        """)
    
    elif choice == "Reset Session":
        st.session_state.bookmarks = []
        st.session_state.search_history = []
        st.session_state.last_active = datetime.now()
        st.success("Sessies zijn gereset.")

# Main Application Logic
def main():
    st.set_page_config(page_title="Ketomed", page_icon="💊", layout="wide")
    # Add logo
    logo_path = os.path.join('assets', 'logo.png')
    if os.path.exists(logo_path):
        st.sidebar.image(logo_path, use_column_width=True)
    else:
        st.sidebar.write("![Logo](https://via.placeholder.com/150)")
    main_app()

if __name__ == "__main__":
    main()