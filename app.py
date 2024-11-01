# app.py
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os

# Constants
DRUGS_CSV = 'data/labeled_drugs.csv'
INACTIVITY_TIMEOUT = 30  # in minutes

# Initialize session state
if 'bookmarks' not in st.session_state:
    st.session_state.bookmarks = []
if 'search_history' not in st.session_state:
    st.session_state.search_history = []
if 'last_active' not in st.session_state:
    st.session_state.last_active = datetime.now()

# Function to load drug data
@st.cache_data
def load_drug_data():
    df = pd.read_csv(DRUGS_CSV, encoding='latin-1')
    return df

# Function to perform simple search (exact and substring matches)
def simple_search(query, choices):
    # Convert query to lowercase for case-insensitive search
    query = query.lower()
    # Filter choices that contain the query as a substring
    results = [choice for choice in choices if query in choice.lower()]
    return results

# Function to update last active timestamp
def update_last_active():
    st.session_state.last_active = datetime.now()

# Function to check inactivity
def check_inactivity():
    now = datetime.now()
    if now - st.session_state.last_active > timedelta(minutes=INACTIVITY_TIMEOUT):
        st.session_state.bookmarks = []
        st.session_state.search_history = []
        st.warning("Sessies zijn gereset vanwege inactiviteit.")
        st.session_state.last_active = datetime.now()

# UI Components
def main_app():
    update_last_active()
    check_inactivity()
    
    st.sidebar.title("Ketomed")
    menu = ["Zoeken", "Boekmarks", "Recente Zoeken", "FAQ", "Voorwaarden", "Reset Sessies"]
    choice = st.sidebar.selectbox("Menu", menu)

    drug_df = load_drug_data()

    if choice == "Zoeken":
        st.header("Zoek naar een geneesmiddel")
        search_term = st.text_input("Voer merknaam of werkzame stof in")
        if search_term:
            # Simple search on brand name and active component
            brand_names = drug_df['NMNAAM'].tolist()
            active_components = drug_df['ATOMS'].tolist()
            combined = brand_names + active_components
            results = simple_search(search_term, combined)
            
            # Retrieve matching rows
            filtered_df = drug_df[
                drug_df['NMNAAM'].isin(results) |
                drug_df['ATOMS'].isin(results)
            ]
            
            # Apply filters
            st.sidebar.subheader("Filters")
            admin_route = st.sidebar.multiselect("Toedieningsweg", options=drug_df['THNM50'].unique())
            keto_status = st.sidebar.multiselect("Ketogene Status", options=drug_df['Handelsproduct Status'].unique())
            if admin_route:
                filtered_df = filtered_df[filtered_df['THNM50'].isin(admin_route)]
            if keto_status:
                filtered_df = filtered_df[filtered_df['Handelsproduct Status'].isin(keto_status)]
            
            st.write(f"Aantal resultaten: {len(filtered_df)}")
            for index, row in filtered_df.iterrows():
                with st.expander(f"{row['NMNAAM']} ({row['ATOMS']})"):
                    st.write(f"**Toedieningsweg:** {row['THNM50']}")
                    st.write(f"**Ketogene Status:** {row['Handelsproduct Status']}")
                    # Bookmark button
                    if row['HPKODE'] in st.session_state.bookmarks:
                        if st.button("Verwijder Bookmark", key=f"remove_{row['HPKODE']}"):
                            st.session_state.bookmarks.remove(row['HPKODE'])
                            st.success("Bookmark verwijderd.")
                    else:
                        if st.button("Bookmark Toevoegen", key=f"add_{row['HPKODE']}"):
                            st.session_state.bookmarks.append(row['HPKODE'])
                            st.success("Bookmark toegevoegd.")
                    # Add to search history
                    st.session_state.search_history.append({'term': search_term, 'timestamp': datetime.now()})
    
    elif choice == "Boekmarks":
        st.header("Uw Boekmarks")
        if st.session_state.bookmarks:
            bookmarked_drugs = drug_df[drug_df['HPKODE'].isin(st.session_state.bookmarks)]
            for index, row in bookmarked_drugs.iterrows():
                with st.expander(f"{row['NMNAAM']} ({row['ATOMS']})"):
                    st.write(f"**Toedieningsweg:** {row['THNM50']}")
                    st.write(f"**Ketogene Status:** {row['Handelsproduct Status']}")
                    if st.button("Verwijder Bookmark", key=f"remove_bookmark_{row['HPKODE']}"):
                        st.session_state.bookmarks.remove(row['HPKODE'])
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
    
    elif choice == "Reset Sessies":
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
