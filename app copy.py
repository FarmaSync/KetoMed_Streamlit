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
    # Filter choices that contain the query as a substring and ensure choice is a string
    results = [choice for choice in choices if isinstance(choice, str) and query in choice.lower()]
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
    # Return the emoji and description as a string
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
    update_last_active()
    check_inactivity()
    
    #st.sidebar.title("Ketomed")
    menu = ["Zoeken", 
            #"Favorieten", 
            #"Recent", 
            "FAQ", 
            "Voorwaarden", 
            #"Reset Sessies"
            ]
    st.sidebar.subheader('Menu')
    choice = st.sidebar.radio(label = 'Menu',label_visibility='hidden',options=menu)

    drug_df = load_drug_data()

    if choice == "Zoeken":
        st.header("Zoek naar een geneesmiddel")
        search_term = st.text_input("Voer merknaam, werkzame stof, ATC of HPK in")
        
        if search_term:
            # Simple search on brand name and active component
            brand_names = drug_df['NMNAAM'].fillna('').tolist()
            active_components = drug_df['ATOMS'].fillna('').tolist()
            drug_id = drug_df['HPKODE'].fillna('').tolist()
            atcode = drug_df['ATCODE'].fillna('').tolist()
            combined = brand_names + active_components + drug_id + atcode
            results = simple_search(search_term, combined)
            
            # Retrieve matching rows
            filtered_df = drug_df[
                drug_df['NMNAAM'].isin(results) |
                drug_df['ATOMS'].isin(results) |
                drug_df['HPKODE'].isin(results)|
                drug_df['ATCODE'].isin(results)
            ]
            
            # Convert 'Handelsproduct Status' to a categorical type with the specified order
            drug_df['Handelsproduct Status'] = pd.Categorical(
                drug_df['Handelsproduct Status'],
                categories=status_order,
                ordered=True
            )
            
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

                        # Optionally, display the status again inside the expander
                        # st.markdown(f"**Ketogene Status:** {row['Handelsproduct Status']}", unsafe_allow_html=True)
                        
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
            else:
                st.info("Geen resultaten gevonden voor uw zoekopdracht.")

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
    
    elif choice == "FAQ":
        st.header("Veelgestelde Vragen")
        st.write("""
        **Vraag 1:** Hoe gebruik ik de zoekfunctie?
        
        **Antwoord:** Voer de merknaam of werkzame stof in het zoekveld in en selecteer uit de suggesties.
        
        **Vraag 2:** Hoe voeg ik een geneesmiddel toe aan mijn Favorieten?
        
        **Antwoord:** Klik op de "Bookmark Toevoegen" knop naast het gewenste geneesmiddel.
        
        **Vraag 3:** Hoe kan ik mijn Favorieten beheren?
        
        **Antwoord:** Ga naar het "Favorieten" menu om uw opgeslagen geneesmiddelen te bekijken of te verwijderen.
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
    logo_path = os.path.join('assets', 'logo.svg')
    if os.path.exists(logo_path):
        st.sidebar.image(logo_path, use_column_width=True)
    else:
        st.sidebar.write("![Logo](https://via.placeholder.com/150)")
    main_app()

if __name__ == "__main__":
    main()