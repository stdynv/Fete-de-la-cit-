import streamlit as st
from pymongo import MongoClient
import time

# MongoDB setup
client = MongoClient("mongodb+srv://yassinemedessamadi:y8NaR9oLJbb2wfiG@cluster0.ctew7yq.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client["CIUP_FETE"]
collection = db["Volonteers_FETE"]

# Rôles initiaux avec leurs créneaux horaires disponibles
roles_and_times = {
    "Admin": ["9:00 AM - 10:00 AM", "10:00 AM - 11:00 AM", "1:00 PM - 2:00 PM"],
    "User": ["10:00 AM - 11:00 AM", "2:00 PM - 3:00 PM"],
    "Guest": ["11:00 AM - 12:00 PM", "3:00 PM - 4:00 PM"],
    "Manager": ["9:30 AM - 10:30 AM", "1:30 PM - 2:30 PM"],
    "Visitor": ["12:00 PM - 1:00 PM", "4:00 PM - 5:00 PM"]
}

country_codes = {
    "France (+33)": "+33",
    "Romania (+40)": "+40",
    "Germany (+49)": "+49",
    "United States (+1)": "+1",
    "United Kingdom (+44)": "+44"
}

# Fonction pour compter le nombre d'inscriptions dans un créneau spécifique
def count_enrollments(role, timeslot):
    return collection.count_documents({"role": role, "selected_time": timeslot})

# Fonction pour récupérer les créneaux horaires déjà sélectionnés pour un rôle spécifique
def get_existing_times(first_name, last_name, role):
    cursor = collection.find({"first_name": first_name, "last_name": last_name, "role": role})
    return [doc["selected_time"] for doc in cursor]

# Fonction pour récupérer les rôles déjà sélectionnés par l'utilisateur
def get_existing_roles(first_name, last_name):
    cursor = collection.find({"first_name": first_name, "last_name": last_name})
    return [doc["role"] for doc in cursor]
def write_to_mongo(data):
    collection.insert_one(data)


repeatable_roles = {"User", "Admin"}
max_slots_per_timeslot = 5


# Start of the form
with st.form(key='my_form',clear_on_submit=True):
    first_name = st.text_input("First Name")
    last_name = st.text_input("Last Name")
    country = st.selectbox("Select your country", [
        "France (+33)", "Romania (+40)", "Germany (+49)", 
        "United States (+1)", "United Kingdom (+44)"
    ])
    phone_number = st.text_input("Phone Number (without country code)")
    
    # Getting current state of entries for role and timeslot
    existing_roles = get_existing_roles(first_name, last_name)
    filtered_roles = [role for role in roles_and_times if role in repeatable_roles or role not in existing_roles]
    
    if filtered_roles:
        selected_role = st.selectbox("Choose your role", filtered_roles)
        selected_times = get_existing_times(first_name, last_name, selected_role)
        available_times = [
            time for time in roles_and_times[selected_role]
            if time not in selected_times and count_enrollments(selected_role, time) < max_slots_per_timeslot
        ]
    else:
        selected_role = None
        available_times = []
        st.write("No roles available. You have already selected all available non-repeatable roles.")

    if available_times:
        selected_time = st.selectbox(f"Available times for {selected_role}", available_times)
    else:
        selected_time = None
        st.write("No available times remaining for the role {selected_role}.")
    
    # Submit button for the form
    submitted = st.form_submit_button("Submit")
    if submitted:
        if first_name and last_name and phone_number and selected_role and selected_time:
            full_phone_number = country_codes[country] + phone_number
            data = {
                "first_name": first_name,
                "last_name": last_name,
                "full_phone_number": full_phone_number,
                "role": selected_role,
                "selected_time": selected_time
            }
            write_to_mongo(data)
            st.success("Data successfully written to MongoDB.")
            time.sleep(2)
        else:
            st.warning("Please fill out all fields.")

