import re
import time
import streamlit as st
import pandas as pd
from pymongo import MongoClient

# Connexion à MongoDB
client = MongoClient(
    "mongodb+srv://yassinemedessamadi:y8NaR9oLJbb2wfiG@cluster0.ctew7yq.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client["CIUP_FETE"]
collection = db["roles"]


# Fonction de validation d'adresse e-mail
def is_valid_email(mail):
    regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(regex, mail) is not None


# Lecture du fichier CSV contenant les noms de maison
@st.cache_data
def load_house_names(csv_file):
    df = pd.read_csv(csv_file)
    return df['house_name'].tolist()


# load data from house.csv file
house_names = load_house_names('houses.csv')


# check if the user has already booked this time slot for the same role
def is_already_registered(mail, selected_role, selected_timeslot):
    existing_registration = db.inscriptions.find_one({
        "email": mail,
        "role": selected_role,
        "heure": selected_timeslot
    })
    return existing_registration is not None


# Fonction pour obtenir les rôles et créneaux déjà choisis par l'utilisateur
def get_registered_roles(email):
    registrations = db.inscriptions.find({"email": email})
    registered_roles = {(reg["role"], reg["heure"]) for reg in registrations}
    return registered_roles


# Function to get available roles
def get_roles_disponibles(roles, registered_roles):
    roles_disponibles = []
    for role in roles:
        task = role['task']
        for creneau in role['creneaux']:
            if creneau['places_disponibles'] > 0 and (task, creneau['heure']) not in registered_roles:
                roles_disponibles.append(task)
                break
    return roles_disponibles


# Function to get available time slots for a selected role
def get_creneaux_disponibles(roles, role_selected, registered_roles):
    creneaux_disponibles = []
    for role in roles:
        if role['task'] == role_selected:
            for creneau in role['creneaux']:
                if creneau['places_disponibles'] > 0 and (role_selected, creneau['heure']) not in registered_roles:
                    creneaux_disponibles.append(creneau['heure'])
    return creneaux_disponibles


st.title('fête de la Cité - Call for Volunteers')

# Initial session state
if 'role_selected' not in st.session_state:
    st.session_state.role_selected = None

if 'creneaux_disponibles' not in st.session_state:
    st.session_state.creneaux_disponibles = []

# Initialize input values in session state
if 'full_name' not in st.session_state:
    st.session_state.full_name = ""

if 'email' not in st.session_state:
    st.session_state.email = ""

# Load roles from the database
roles = list(collection.find())

# Container for the form
form_container = st.container()

# Display form for user input inside the container
with form_container:
    

    full_name = st.text_input('Full Name', value=st.session_state.full_name, key='full_name_input')
    email = st.text_input('Email Address', value=st.session_state.email, key='email_input')
    house_name = st.selectbox('House Name', house_names)

    if email:
        # get role and time slot based on user mail
        registered_roles = get_registered_roles(email)
    else:
        registered_roles = set()

    # Select role and dynamically update time slots
    roles_disponibles = get_roles_disponibles(roles, registered_roles)
    role_selected = st.selectbox('Sélectionnez un rôle', roles_disponibles, key='role_selectbox')

    # Container to dynamically update time slots
    creneaux_container = st.container()
    if role_selected != st.session_state.role_selected:
        st.session_state.role_selected = role_selected
        st.session_state.creneaux_disponibles = get_creneaux_disponibles(roles, role_selected, registered_roles)

    with creneaux_container:
        creneaux_disponibles = st.session_state.creneaux_disponibles
        creneau_selected = st.selectbox('Sélectionnez un créneau horaire', creneaux_disponibles,
                                        key='creneau_selectbox')

    if st.button("Submit"):
        if not full_name or not email or not house_name:
            st.error('Veuillez remplir tous les champs du formulaire.')
        elif not is_valid_email(email):
            st.error('Veuillez entrer une adresse e-mail valide.')
        elif is_already_registered(email, st.session_state.role_selected, creneau_selected):
            st.error('Vous êtes déjà inscrit pour ce rôle et ce créneau.')
        else:
            for role in roles:
                if role['task'] == st.session_state.role_selected:
                    for creneau in role['creneaux']:
                        if creneau['heure'] == creneau_selected:
                            date = creneau['date']
                            heure = creneau['heure']
                            result = collection.update_one(
                                {"task": st.session_state.role_selected, "creneaux.date": date,
                                 "creneaux.heure": heure},
                                {"$inc": {"creneaux.$.places_disponibles": -1}}
                            )
                            if result.modified_count > 0:
                                # Sauvegarder les informations de l'utilisateur
                                db.inscriptions.insert_one({
                                    "full_name": full_name,
                                    "email": email,
                                    "house_name": house_name,
                                    "role": st.session_state.role_selected,
                                    "date": date,
                                    "heure": heure
                                })
                                st.success(
                                    f'Inscription confirmée pour le rôle: {st.session_state.role_selected} à {creneau_selected}')

                                # Clear the input fields

                                time.sleep(1)
                                # Reload the page
                                st.experimental_rerun()
                            else:
                                st.error('Une erreur s\'est produite. Veuillez réessayer.')
                            break

