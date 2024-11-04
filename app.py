# app.py
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader


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


# Function to perform multi-keyword search (exact and substring matches with AND condition)
def multi_keyword_search(query, choices):
    # Split the query into individual keywords and convert to lowercase for case-insensitive search
    keywords = query.lower().split()
    # Filter choices that contain all keywords as substrings
    results = [
        choice for choice in choices 
        if isinstance(choice, str) and all(keyword in choice.lower() for keyword in keywords)
    ]
    return results

# Define the desired order for Handelsproduct Status
status_order = ['Yes', 'Unknown', 'No']

# Function to map status to colored indicators using emojis
def get_status_indicator(status):
    status = str(status).strip()  # Ensure the status is a string and remove any leading/trailing whitespace
    if status == 'Yes':
        emoji = '🟢'
        description = 'Ketoproof'
    elif status == 'No':
        emoji = '🔴'
        description = 'Niet Ketoproof'
    else:
        emoji = '🟠'
        description = 'Onbekend'
    # Return the emoji as a string
    return f"{emoji}"

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
    #st.switch_page("app.py") #So that the login modal disappears

    update_last_active()
    check_inactivity()


    # st.sidebar.title("Ketomed")
    menu = ["Zoeken", 
            #"Favorieten", 
            #"Recent", 
            "FAQ", 
            "Voorwaarden", 
            "Help",
            #"Reset Sessies"
            ]
    st.sidebar.subheader('Menu')
    
    # Replace the selectbox with a radio button for vertical listing
    choice = st.sidebar.radio(label='Menu', label_visibility='hidden', options=menu)

    drug_df = load_drug_data()
    
    # Data Cleaning and Standardization
    # a. Standardize 'Handelsproduct Status'
    drug_df['Handelsproduct Status'] = drug_df['Handelsproduct Status'].astype(str).str.strip().str.title()
    
    # b. Map inconsistent statuses to standardized categories
    status_mapping = {
        'Yes': 'Yes',
        'No': 'No',
        'Unknown': 'Unknown',
        # Add more mappings if necessary
    }
    drug_df['Handelsproduct Status'] = drug_df['Handelsproduct Status'].map(status_mapping).fillna('Unknown')
    
    # c. Define sorting order
    # Already defined above as status_order = ['Yes', 'Unknown', 'No']
    
    # d. Convert to categorical with order
    drug_df['Handelsproduct Status'] = pd.Categorical(
        drug_df['Handelsproduct Status'],
        categories=status_order,
        ordered=True
    )
    
    # Debugging: Display unique 'Handelsproduct Status' values
    # st.write("Unique 'Handelsproduct Status' values after cleaning:", drug_df['Handelsproduct Status'].unique())
    
    if choice == "Zoeken":
        st.header("Zoek naar een geneesmiddel")

        search_term = st.text_input("Voer merknaam, werkzame stof, ATC of HPK in")
        minimal_number_of_characters = 3

        
        if search_term and (len(search_term)>=minimal_number_of_characters):
            with st.spinner('Zoeken...'):
                # Simple search on brand name, active component, drug ID, and ATC code
                brand_names = drug_df['NMNAAM'].fillna('').tolist()
                active_components = drug_df['ATOMS'].fillna('').tolist()
                drug_id = drug_df['HPKODE'].fillna('').tolist()
                atcode = drug_df['ATCODE'].fillna('').tolist()
                combined = brand_names + active_components + drug_id + atcode
                results = multi_keyword_search(search_term, combined)
                
                # Retrieve matching rows
                filtered_df = drug_df[
                    drug_df['NMNAAM'].isin(results) |
                    drug_df['ATOMS'].isin(results) |
                    drug_df['HPKODE'].isin(results) |
                    drug_df['ATCODE'].isin(results)
                ].copy()  # Use .copy() to avoid SettingWithCopyWarning
                
                # Sort the filtered DataFrame based on 'Handelsproduct Status'
                filtered_df = filtered_df.sort_values('Handelsproduct Status')
                
                # Filters placed side by side using columns
                st.subheader("Filters")
                col1, col2 = st.columns(2)

                with col1:
                    admin_route = st.multiselect(
                        "Toedieningsweg",
                        options=drug_df['THNM50'].dropna().unique(),
                        key="admin_route"
                    )

                with col2:
                    keto_status = st.multiselect(
                        "Ketogene Status",
                        options=drug_df['Handelsproduct Status'].dropna().unique(),
                        key="keto_status"
                    )
                
                if admin_route:
                    filtered_df = filtered_df[filtered_df['THNM50'].isin(admin_route)]
                if keto_status:
                    filtered_df = filtered_df[filtered_df['Handelsproduct Status'].isin(keto_status)]
                
                st.write(f"Aantal resultaten: {len(filtered_df)}")
                if len(filtered_df) > 0:
                    for index, row in filtered_df.iterrows():
                        # Get the status indicator
                        status_indicator = get_status_indicator(row['Handelsproduct Status'])
                        
                        # Create the expander with the status indicator in the label
                        with st.expander(f"{status_indicator} {row['NMNAAM']} (HPK: {row['HPKODE']})"):
                            col1, col2, col3 = st.columns(3)

                            with col1:
                                st.write(f"**Werkzame stof:** {row['ATOMS']}")
                                

                            with col2:
                                st.write(f"**ATC:** {row['ATCODE']}")
                                
                            
                            with col3:
                                st.write(f"**Toedieningsweg:** {row['THNM50']}")
                            
                            st.write(f"**Alle hulpstoffen:** {row['Generieke naam']}")
                            st.write(f"**Niet-ketogene hulpstoffen:** {row['Non-Ketoproof Excipients']}")
                            st.write(f"**Onbekende status hulpstoffen:** {row['Unknown Excipients']}")


                            # Bookmark button
                            #if row['HPKODE'] in st.session_state.bookmarks:
                            #    if st.button("Verwijder Bookmark", key=f"remove_{row['HPKODE']}"):
                            #        st.session_state.bookmarks.remove(row['HPKODE'])
                            #        st.success("Bookmark verwijderd.")
                            #else:
                            #    if st.button("Bookmark Toevoegen", key=f"add_{row['HPKODE']}"):
                            #        st.session_state.bookmarks.append(row['HPKODE'])
                            #        st.success("Bookmark toegevoegd.")

                    # Add to search history after all results are processed
                    st.session_state.search_history.append({'term': search_term, 'timestamp': datetime.now()})
                else:
                    st.info("Geen resultaten gevonden voor uw zoekopdracht.")         
        else:
            st.info(f"Voer minimaal {str(minimal_number_of_characters)} tekens in.")

    elif choice == "Favorieten":
        st.header("Uw Favorieten")
        if st.session_state.bookmarks:
            bookmarked_drugs = drug_df[drug_df['HPKODE'].isin(st.session_state.bookmarks)]
            for index, row in bookmarked_drugs.iterrows():
                # Get the status indicator
                status_indicator = get_status_indicator(row['Handelsproduct Status'])
                
                with st.expander(f"{status_indicator} {row['NMNAAM']} ({row['ATOMS']})"):
                    st.write(f"**Toedieningsweg:** {row['THNM50']}")
                    # Optionally, display the status again inside the expander
                    # st.markdown(f"**Ketogene Status:** {row['Handelsproduct Status']}", unsafe_allow_html=True)
                    
                    if row['HPKODE'] in st.session_state.bookmarks:
                        if st.button("Verwijder Bookmark", key=f"remove_bookmark_{row['HPKODE']}"):
                            st.session_state.bookmarks.remove(row['HPKODE'])
                            st.success("Bookmark verwijderd.")
        else:
            st.info("U heeft nog geen Favorieten.")
    
    elif choice == "Recent":
        st.header("Recent")
        if st.session_state.search_history:
            for entry in reversed(st.session_state.search_history[-10:]):
                st.write(f"{entry['term']} - {entry['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            st.info("Geen recente zoekopdrachten gevonden.")
    
    elif choice == "Help":
        st.header("📖 Help & Ondersteuning")
        
        st.markdown("""
        ### Welkom bij Ketomed!
        
        **Ketomed** helpt u bij het zoeken naar geneesmiddelen op basis van hun ketogene status. Deze Help-pagina is ontworpen om u te begeleiden bij het optimaal benutten van alle functies van onze applicatie.
        """)
                
        st.markdown("""
        ---
        
        ### 🔍 Hoe te Gebruiken
        
        #### 1. Zoeken naar Geneesmiddelen
        - Gebruik de zoekbalk om te zoeken op **merknaam**, **werkzame stof**, **ATC-code** of **HPK-code**.
        - Typ een zoekterm en druk op Enter om resultaten te bekijken.
        
        #### 2. Filters Toepassen
        - Na het invoeren van een zoekterm verschijnen er twee filteropties:
            - **Toedieningsweg**: Selecteer één of meerdere toedieningswegen om de zoekresultaten te verfijnen.
            - **Ketogene Status**: Filter op **Ketoproof**, **Niet Ketoproof** of **Onbekend**.
        - Kies de gewenste filters om de resultaten aan te passen aan uw behoeften.
        
        #### 3. Favorieten Beheren
        - Klik op **"Favoriet Toevoegen"** naast een geneesmiddel om het op te slaan.
        - Ga naar de **"Favorieten"** sectie in de sidebar om uw opgeslagen geneesmiddelen te bekijken of te verwijderen.

        
        ### 📞 Contactinformatie
        
        Heeft u nog vragen of ondervindt u problemen? Neem gerust contact met ons op!
        
        - **E-mail:** s.elabdouni@erasmusmc.nl
        
        ### 💡 Feedback Geven
        
        Uw feedback is waardevol voor ons! Laat ons weten hoe we **Ketomed** kunnen verbeteren.
        
        """)
    
    elif choice == "FAQ":
        st.header("❓ Veelgestelde Vragen")
        
        with st.expander("🔹 Hoe kan ik een geneesmiddel toevoegen aan mijn Favorieten?"):
            st.write("""
            Zoek naar het gewenste geneesmiddel, klik op de expander om de details te zien en klik vervolgens op **"Bookmark Toevoegen"**.
            """)
        
        with st.expander("🔹 Hoe verwijder ik een geneesmiddel uit mijn Favorieten?"):
            st.write("""
            Ga naar de **"Favorieten"** sectie, open de gewenste favoriet en klik op **"Verwijder Bookmark"**.
            """)
        
        with st.expander("🔹 Wat gebeurt er na 30 minuten inactiviteit?"):
            st.write("""
            Na 30 minuten inactiviteit worden uw favorieten en zoekgeschiedenis automatisch gereset voor uw privacy en veiligheid.
            """)


    elif choice == "Voorwaarden":
        st.header("📜 Algemene Voorwaarden")
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
    logo_path = os.path.join('assets', 'logo.svg')  # Changed to .svg as per user's code
    if os.path.exists(logo_path):
        st.sidebar.image(logo_path, use_column_width=True)
    else:
        st.sidebar.write("![Logo](https://via.placeholder.com/150)")
    

    # Load configuration
    with open('config.yaml') as file:
        config = yaml.load(file, Loader=SafeLoader)
    
    # Initialize the authenticator
    authenticator = stauth.Authenticate(
        config['credentials'],
        config['cookie']['name'],
        config['cookie']['key'],
        config['cookie']['expiry_days']
    )
    
    
    if st.session_state['authentication_status'] is None:
        authenticator.login(location='sidebar')
        
    elif st.session_state['authentication_status'] is False:
        st.sidebar.error('Gebruikersnaam/wachtwoord is incorrect')
        authenticator.login(location='sidebar')   

    elif st.session_state['authentication_status']:
        st.success(f'Welkom *{st.session_state["name"]}*')
        main_app()
        authenticator.logout('Uitloggen', 'sidebar')
    
        # Optionally, save the config if needed
        with open('config.yaml', 'w') as file:
            yaml.dump(config, file, default_flow_style=False)

if __name__ == "__main__":
    main()
