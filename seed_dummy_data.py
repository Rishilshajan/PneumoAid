import os
from datetime import datetime, timedelta
from pymongo import MongoClient
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash
import cloudinary
import cloudinary.uploader

# ============================================================
# ENVIRONMENT
# ============================================================
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    print("Error: MONGO_URI is not set in the .env file.")
    exit(1)

# ============================================================
# DATABASE
# ============================================================
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000)
    client.admin.command("ping")
    db = client.get_default_database()
    print(f"Connected to database: {db.name}")
except Exception as e:
    print("MongoDB connection failed.")
    print(e)
    exit(1)

# ============================================================
# CLOUDINARY
# ============================================================
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")

if not all([CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET]):
    print("Warning: Cloudinary environment variables are not completely configured.")

cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET
)

# ============================================================
# REAL HOSPITAL DATA
# ============================================================
hospitals = [
    {
        "name": "Amrita Hospital",
        "identifier": "AMRITA-KOCHI",
        "location": "Kochi, Kerala",
        "type": "private",
        "status": "active",
        "image_source": "https://upload.wikimedia.org/wikipedia/commons/f/f5/Amrita_Hospital_Kochi.jpg",
        "image_author": "Mujeebcpy",
        "image_license": "CC BY-SA 4.0"
    },
    {
        "name": "Aster Medcity",
        "identifier": "ASTER-KOCHI",
        "location": "Kochi, Kerala",
        "type": "private",
        "status": "active",
        "image_source": "https://upload.wikimedia.org/wikipedia/commons/f/f9/Aster_Medcity_Hospital_Entrance.jpg",
        "image_author": "Tachs",
        "image_license": "CC BY-SA 4.0"
    },
    {
        "name": "KIMS Hospital",
        "identifier": "KIMS-TVPM",
        "location": "Thiruvananthapuram, Kerala",
        "type": "private",
        "status": "active",
        "image_source": "https://upload.wikimedia.org/wikipedia/commons/1/19/KIMS_Hospital_Thiruvananthapuram.jpg",
        "image_author": "Adnan Haleem",
        "image_license": "CC BY-SA 3.0"
    },
    {
        "name": "Rajagiri Hospital",
        "identifier": "RAJAGIRI-ALUVA",
        "location": "Aluva, Kerala",
        "type": "private",
        "status": "active",
        "image_source": "https://upload.wikimedia.org/wikipedia/commons/6/65/Rajagiri_Hospital_Kerala.jpg",
        "image_author": "Rajagiri Hospital",
        "image_license": "CC BY-SA 4.0"
    },
    {
        "name": "VPS Lakeshore Hospital",
        "identifier": "LAKESHORE-KOCHI",
        "location": "Kochi, Kerala",
        "type": "private",
        "status": "active",
        "image_source": "https://upload.wikimedia.org/wikipedia/commons/b/b6/Lakeshore_Hospital_Kochi.jpg",
        "image_author": "Shady59",
        "image_license": "CC BY-SA 4.0"
    },
    {
        "name": "Lourdes Hospital",
        "identifier": "LOURDES-KOCHI",
        "location": "Ernakulam, Kerala",
        "type": "private",
        "status": "active",
        "image_source": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a2/Lourdes_Hospital%2C_Ernakulam.jpg/1280px-Lourdes_Hospital%2C_Ernakulam.jpg",
        "image_author": "Vis M",
        "image_license": "CC BY-SA 4.0"
    },
    {
        "name": "Medical Trust Hospital",
        "identifier": "MEDICAL-TRUST-KOCHI",
        "location": "Ernakulam, Kerala",
        "type": "private",
        "status": "active",
        "image_source": "https://upload.wikimedia.org/wikipedia/commons/f/f8/Medical_trust_hospital%2C_Ekm.jpg",
        "image_author": "Challiyan",
        "image_license": "CC BY-SA 2.5"
    },
    {
        "name": "Government Medical College Ernakulam",
        "identifier": "GMC-ERNAKULAM",
        "location": "Kalamassery, Kerala",
        "type": "government",
        "status": "active",
        "image_source": "https://upload.wikimedia.org/wikipedia/commons/5/5b/Govt%2C_Medical_College%2C_Ernakulam.jpg",
        "image_author": "Shady59",
        "image_license": "CC BY-SA"
    },
    {
        "name": "A.P. Varkey Mission Hospital",
        "identifier": "APV-ANGAMALY",
        "location": "Angamaly, Kerala",
        "type": "private",
        "status": "active",
        "image_source": "https://upload.wikimedia.org/wikipedia/commons/7/77/A_P_Varkey_Mission_Hospital.jpg",
        "image_author": "Sivahari",
        "image_license": "CC BY-SA 3.0"
    },
    {
        "name": "Amala Institute of Medical Sciences",
        "identifier": "AMALA-THRISSUR",
        "location": "Thrissur, Kerala",
        "type": "private",
        "status": "active",
        "image_source": "https://upload.wikimedia.org/wikipedia/commons/7/7b/AmalaMedicalCollege%2CThrissur.JPG",
        "image_author": "Aruna",
        "image_license": "CC BY-SA 3.0"
    }
]

# ============================================================
# FICTIONAL PATIENT DATA
# ============================================================
patient_names = [
    ("Arjun Nair", 34, "Male"),
    ("Ananya Menon", 27, "Female"),
    ("Rahul Krishnan", 46, "Male"),
    ("Meera Thomas", 39, "Female"),
    ("Vivek Kumar", 51, "Male"),
    ("Sneha Joseph", 31, "Female"),
    ("Aditya Raj", 23, "Male"),
    ("Lakshmi Suresh", 58, "Female"),
    ("Nikhil Varma", 42, "Male"),
    ("Devika Nair", 29, "Female")
]

appointment_reasons = [
    "Routine Checkup",
    "Respiratory Consultation",
    "Follow-up Consultation",
    "Pulmonary Function Review",
    "Chest Pain Evaluation",
    "General Consultation",
    "Fever and Cough",
    "Asthma Follow-up",
    "Medication Review",
    "Diagnostic Consultation"
]

def seed_data():
    print("\n==========================================")
    print("PneumoAid Demo Data Seeder")
    print("==========================================\n")

    print("Removing previous demo data...")
    db.clinics.delete_many({"is_dummy": True})
    db.patients.delete_many({"is_dummy": True})
    db.appointments.delete_many({"is_dummy": True})
    db.users.delete_many({"is_dummy": True})

    # 1. CREATE HOSPITALS / CLINICS
    print("\nUploading hospital images and creating clinics...\n")
    clinics_data = []

    for index, hospital in enumerate(hospitals, start=1):
        print(f"[{index}/{len(hospitals)}] {hospital['name']}")
        image_url = None
        try:
            upload_result = cloudinary.uploader.upload(
                hospital["image_source"],
                folder="pneumoaid_clinics",
                public_id=hospital["identifier"].lower()
            )
            image_url = upload_result["secure_url"]
            print("   Image uploaded successfully.")
        except Exception as image_error:
            print("   Image upload failed:", image_error)

        clinic = {
            "name": hospital["name"],
            "identifier": hospital["identifier"],
            "location": hospital["location"],
            "type": hospital["type"],
            "status": hospital["status"],
            "username": hospital["identifier"].lower().replace("-", "_"),
            "password": generate_password_hash("password123"),
            "image_url": image_url,
            "image_source": hospital["image_source"],
            "image_author": hospital["image_author"],
            "image_license": hospital["image_license"],
            "is_dummy": True,
            "created_at": datetime.now() - timedelta(days=index)
        }
        clinics_data.append(clinic)

    if clinics_data:
        db.clinics.insert_many(clinics_data)
        print(f"\nInserted {len(clinics_data)} hospitals.")

    # 2. CREATE PATIENTS
    print("\nCreating patient records...")
    patients_data = []
    daily_patient_distribution = [5, 2, 4, 1, 6, 3, 2, 4, 1, 2]
    patient_index = 0

    for days_ago, count in enumerate(daily_patient_distribution):
        for _ in range(count):
            name, age, gender = patient_names[patient_index % len(patient_names)]
            created_date = datetime.now() - timedelta(days=days_ago)
            patients_data.append({
                "name": name,
                "age": age,
                "gender": gender,
                "created_at": created_date,
                "is_dummy": True
            })
            patient_index += 1

    if patients_data:
        db.patients.insert_many(patients_data)
        print(f"Inserted {len(patients_data)} fictional patients.")

    # 3. CREATE APPOINTMENTS
    print("\nCreating appointments...")
    appointments_data = []
    appointment_clinics = [h["name"] for h in hospitals]
    appointment_patient_names = [p[0] for p in patient_names]
    today = datetime.today()

    for i in range(10):
        appointments_data.append({
            "patient_name": appointment_patient_names[i % len(appointment_patient_names)],
            "clinic_name": appointment_clinics[i % len(appointment_clinics)],
            "date": today.strftime("%Y-%m-%d") if i < 5 else (today - timedelta(days=1)).strftime("%Y-%m-%d"),
            "booking_date": datetime.now() - timedelta(days=(i + 1)),
            "status": "pending" if i < 5 else "completed",
            "reason": appointment_reasons[i % len(appointment_reasons)],
            "is_dummy": True
        })

    if appointments_data:
        db.appointments.insert_many(appointments_data)
        print(f"Inserted {len(appointments_data)} appointments.")

    # 4. CREATE USERS
    print("\nCreating users...")
    users_data = [
        {
            "name": "Qwertn",
            "username": "Qwertn",
            "email": "qwertn@example.com",
            "password": generate_password_hash("Qwert@123"),
            "role": "user",
            "is_dummy": True
        }
    ]
    
    # Fill in remaining users to make 10
    for i in range(1, 10):
        users_data.append({
            "name": f"Dummy User {i}",
            "username": f"dummyuser{i}",
            "email": f"user{i}@example.com",
            "password": generate_password_hash("password123"),
            "role": "user",
            "is_dummy": True
        })

    if users_data:
        db.users.insert_many(users_data)
        print(f"Inserted {len(users_data)} users.")

    print("\n==========================================")
    print("SEEDING COMPLETED SUCCESSFULLY")
    print("==========================================\n")

if __name__ == "__main__":
    try:
        seed_data()
    except Exception as e:
        print(f"An error occurred: {e}")