# app.py
import streamlit as st
import pandas as pd
import sqlite3
import bcrypt
from fuzzywuzzy import process
from datetime import datetime, timedelta

# Constants
DB_PATH = 'database/ketomed.db'
DRUGS_CSV = 'data/drugs.csv'
INACTIVITY_TIMEOUT = 30  # in minutes

# Initialize session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'last_active' not in st.session_state:
    st.session_state.last_active = datetime.now()
if 'bookmarks' not in st.session_state:
    st.session_state.bookmarks = []
if 'search_history' not in st.session_state:
    st.session_state.search_history = []

# Function to connect to the database
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Function to authenticate user
def authenticate(username, password):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = cursor.fetchone()
    conn.close()
    if user and bcrypt.checkpw(password.encode('utf-8'), user['password']):
        return user['id']
    return None

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
    if st.session_state.logged_in:
        now = datetime.now()
        if now - st.session_state.last_active > timedelta(minutes=INACTIVITY_TIMEOUT):
            st.session_state.logged_in = False
            st.session_state.user_id = None
            st.session_state.bookmarks = []
            st.session_state.search_history = []
            st.warning("You have been logged out due to inactivity.")

# Function to add to search history
def add_search_history(user_id, search_term):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO search_history (user_id, search_term) VALUES (?, ?)', (user_id, search_term))
    conn.commit()
    conn.close()

# Function to add to analytics
def add_analytics(user_id, action, drug_id=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO analytics (user_id, action, drug_id) VALUES (?, ?, ?)', (user_id, action, drug_id))
    conn.commit()
    conn.close()

# Function to get user bookmarks
def get_user_bookmarks(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT drug_id FROM bookmarks WHERE user_id = ?', (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [row['drug_id'] for row in rows]

# Function to add a bookmark
def add_bookmark(user_id, drug_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO bookmarks (user_id, drug_id) VALUES (?, ?)', (user_id, drug_id))
    conn.commit()
    conn.close()

# Function to remove a bookmark
def remove_bookmark(user_id, drug_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM bookmarks WHERE user_id = ? AND drug_id = ?', (user_id, drug_id))
    conn.commit()
    conn.close()

# UI Components
def login():
    st.title("Ketomed Login")
    username = st.text_input("Gebruikersnaam")
    password = st.text_input("Wachtwoord", type="password")
    if st.button("Inloggen"):
        user_id = authenticate(username, password)
        if user_id:
            st.session_state.logged_in = True
            st.session_state.user_id = user_id
            st.session_state.bookmarks = get_user_bookmarks(user_id)
            st.success("Inloggen succesvol!")
            add_analytics(user_id, "login")
        else:
            st.error("Ongeldige gebruikersnaam of wachtwoord.")

def main_app():
    update_last_active()
    check_inactivity()
    st.sidebar.title("Ketomed")
    menu = ["Zoeken", "Boekmarks", "Recente Zoeken", "FAQ", "Voorwaarden", "Uitloggen"]
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
            st.write(f"**Aantal resultaten: {len(results)}**")
            for index, row in results.iterrows():
                with st.expander(f"{row['brand_name']} ({row['active_component']})"):
                    st.write(f"**Toedieningsweg:** {row['administration_route']}")
                    st.write(f"**Ketogene Status:** {row['ketogenic_status']}")
                    # Bookmark button
                    if row['drug_id'] in st.session_state.bookmarks:
                        if st.button("Verwijder Bookmark", key=f"remove_{row['drug_id']}"):
                            remove_bookmark(st.session_state.user_id, row['drug_id'])
                            st.session_state.bookmarks.remove(row['drug_id'])
                            st.success("Bookmark verwijderd.")
                    else:
                        if st.button("Bookmark Toevoegen", key=f"add_{row['drug_id']}"):
                            add_bookmark(st.session_state.user_id, row['drug_id'])
                            st.session_state.bookmarks.append(row['drug_id'])
                            st.success("Bookmark toegevoegd.")
                    # Add to analytics
                    add_analytics(st.session_state.user_id, "view_drug", row['drug_id'])
            # Add to search history and analytics
            add_search_history(st.session_state.user_id, search_term)
            add_analytics(st.session_state.user_id, "search", None)

    elif choice == "Boekmarks":
        st.header("Uw Boekmarks")
        if st.session_state.bookmarks:
            bookmarked_drugs = drug_df[drug_df['drug_id'].isin(st.session_state.bookmarks)]
            for index, row in bookmarked_drugs.iterrows():
                with st.expander(f"{row['brand_name']} ({row['active_component']})"):
                    st.write(f"**Toedieningsweg:** {row['administration_route']}")
                    st.write(f"**Ketogene Status:** {row['ketogenic_status']}")
                    if st.button("Verwijder Bookmark", key=f"remove_bookmark_{row['drug_id']}"):
                        remove_bookmark(st.session_state.user_id, row['drug_id'])
                        st.session_state.bookmarks.remove(row['drug_id'])
                        st.success("Bookmark verwijderd.")
        else:
            st.info("U heeft nog geen boekmarks.")

    elif choice == "Recente Zoeken":
        st.header("Recente Zoeken")
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT search_term, timestamp FROM search_history WHERE user_id = ? ORDER BY timestamp DESC LIMIT 10', (st.session_state.user_id,))
        rows = cursor.fetchall()
        conn.close()
        if rows:
            for row in rows:
                st.write(f"{row['search_term']} - {row['timestamp']}")
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

    elif choice == "Uitloggen":
        st.session_state.logged_in = False
        st.session_state.user_id = None
        st.session_state.bookmarks = []
        st.session_state.search_history = []
        st.success("U bent succesvol uitgelogd.")
        add_analytics(st.session_state.user_id, "logout")

def logout():
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.bookmarks = []
    st.session_state.search_history = []
    st.success("U bent succesvol uitgelogd.")

# Main Application Logic
def main():
    st.set_page_config(page_title="Ketomed", page_icon="💊", layout="wide")
    # Add logo
    st.sidebar.image("assets/logo.png", use_column_width=True)
    if not st.session_state.logged_in:
        login()
    else:
        main_app()

if __name__ == "__main__":
    main()


'''
Explanation of app.py
Imports and Constants: Import necessary libraries and define constants like database paths and inactivity timeout.

Session State Initialization: Initialize session state variables to manage user login status, bookmarks, and search history.

Database Functions:

get_connection(): Connects to the SQLite database.
authenticate(): Authenticates user credentials.
load_drug_data(): Loads the drug database using Pandas with caching for performance.
fuzzy_search(): Implements fuzzy matching using fuzzywuzzy.
update_last_active() and check_inactivity(): Manage user session inactivity and auto-logout.
add_search_history() and add_analytics(): Log user actions for analytics.
get_user_bookmarks(), add_bookmark(), remove_bookmark(): Manage user bookmarks.
UI Components:

login(): Handles user login.
main_app(): Main application interface with navigation menu for searching drugs, managing bookmarks, viewing recent searches, FAQ, terms, and logout.
Each section handles its specific functionality, such as performing searches with fuzzy matching, displaying drug information, managing bookmarks, and logging user actions.
Main Function: Sets up the Streamlit page and determines whether to show the login screen or the main application based on the user's login status.
'''