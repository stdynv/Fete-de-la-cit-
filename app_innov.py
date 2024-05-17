import re
import streamlit as st
import pandas as pd
from pymongo import MongoClient

# Connexion à MongoDB
client = MongoClient("mongodb+srv://yassinemedessamadi:y8NaR9oLJbb2wfiG@cluster0.ctew7yq.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client["CIUP_FETE"]
collection = db["roles"]

# Fonction de validation d'adresse e-mail
def is_valid_email(email):
    regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(regex, email) is not None

# Lecture du fichier CSV contenant les noms de maison
@st.cache_data
def load_house_names(csv_file):
    df = pd.read_csv(csv_file)
    return df['house_name'].tolist()

# Charger les noms de maison depuis le fichier CSV
house_names = load_house_names('houses.csv')

# Fonction pour vérifier si l'utilisateur est déjà inscrit pour le même rôle et créneau
def is_already_registered(email, role_selected, creneau_selected):
    existing_registration = db.inscriptions.find_one({
        "email": email,
        "role": role_selected,
        "heure": creneau_selected
    })
    return existing_registration is not None

# Fonction pour obtenir les rôles et créneaux déjà choisis par l'utilisateur
def get_registered_roles(email):
    registrations = db.inscriptions.find({"email": email})
    registered_roles = {(reg["role"], reg["heure"]) for reg in registrations}
    return registered_roles

# Titre de l'application
st.title('Disponibilité des Rôles')

# CSS pour centrer le formulaire
st.markdown(
    """
    <style>
    .centered-form {
        display: flex;
        justify-content: center;
        align-items: center;
        flex-direction: column;
        text-align: center;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Initialize session state for form fields if not already initialized
if 'full_name' not in st.session_state:
    st.session_state.full_name = ''
if 'email' not in st.session_state:
    st.session_state.email = ''
if 'house_name' not in st.session_state:
    st.session_state.house_name = house_names[0]
if 'role_selected' not in st.session_state:
    st.session_state.role_selected = ''
if 'creneau_selected' not in st.session_state:
    st.session_state.creneau_selected = ''

# Conteneur centralisé pour le formulaire
with st.container():
    st.markdown('<div class="centered-form">', unsafe_allow_html=True)
    
    st.header('Choisissez un rôle et un créneau horaire')

    # Champs supplémentaires
    full_name = st.text_input('Full Name', value=st.session_state.full_name)
    email = st.text_input('Email Address', value=st.session_state.email)
    house_name = st.selectbox('House Name', house_names, index=house_names.index(st.session_state.house_name))

    if email:
        # Obtenir les rôles et créneaux déjà choisis par l'utilisateur
        registered_roles = get_registered_roles(email)
    else:
        registered_roles = set()

    # Récupération des rôles disponibles
    roles = list(collection.find())

    # Sélection des rôles ayant des créneaux disponibles et non choisis par l'utilisateur
    roles_disponibles = []
    for role in roles:
        task = role['task']
        for creneau in role['creneaux']:
            if creneau['places_disponibles'] > 0 and (task, creneau['heure']) not in registered_roles:
                roles_disponibles.append(task)
                break

    if roles_disponibles:
        role_selected = st.selectbox('Sélectionnez un rôle', roles_disponibles)
    else:
        role_selected = None
        st.error('Aucun rôle disponible pour votre sélection.')

    if role_selected:
        # Récupérer les créneaux horaires pour le rôle sélectionné et non choisis par l'utilisateur
        creneaux_disponibles = []
        for role in roles:
            if role['task'] == role_selected:
                for creneau in role['creneaux']:
                    if creneau['places_disponibles'] > 0 and (role_selected, creneau['heure']) not in registered_roles:
                        creneaux_disponibles.append(creneau['heure'])

        # Affichage dynamique des créneaux horaires
        creneau_selected = st.selectbox('Sélectionnez un créneau horaire', creneaux_disponibles)

        if st.button('Confirmer'):
            if not full_name or not email or not house_name:
                st.error('Veuillez remplir tous les champs du formulaire.')
            elif not is_valid_email(email):
                st.error('Veuillez entrer une adresse e-mail valide.')
            elif is_already_registered(email, role_selected, creneau_selected):
                st.error('Vous êtes déjà inscrit pour ce rôle et ce créneau.')
            else:
                for role in roles:
                    if role['task'] == role_selected:
                        for creneau in role['creneaux']:
                            if creneau['heure'] == creneau_selected:
                                date = creneau['date']
                                heure = creneau['heure']
                                result = collection.update_one(
                                    {"task": role_selected, "creneaux.date": date, "creneaux.heure": heure},
                                    {"$inc": {"creneaux.$.places_disponibles": -1}}
                                )
                                if result.modified_count > 0:
                                    # Sauvegarder les informations de l'utilisateur
                                    db.inscriptions.insert_one({
                                        "full_name": full_name,
                                        "email": email,
                                        "house_name": house_name,
                                        "role": role_selected,
                                        "date": date,
                                        "heure": heure
                                    })
                                    st.success(f'Inscription confirmée pour le rôle: {role_selected} à {creneau_selected}')
                                    # Clear the form fields
                                    st.session_state.full_name = ''
                                    st.session_state.email = ''
                                    st.session_state.house_name = house_names[0]
                                    st.session_state.role_selected = ''
                                    st.session_state.creneau_selected = ''
                                    # Redirect to confirmation page
                                    st.experimental_set_query_params(page="confirmation")
                                    st.experimental_rerun()
                                else:
                                    st.error('Une erreur s\'est produite. Veuillez réessayer.')
                                break

    st.markdown('</div>', unsafe_allow_html=True)
