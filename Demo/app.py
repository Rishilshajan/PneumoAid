from flask import Flask, jsonify, request, render_template, redirect, url_for, session, flash, send_from_directory
from flask_pymongo import PyMongo
from flask_cors import CORS
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash
from datetime import datetime
from bson import ObjectId
import os
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader
import json

load_dotenv()

app = Flask(__name__)
CORS(app)
app.secret_key = os.environ.get('SECRET_KEY', 'fallback_secret_key_123!')

# MongoDB Configuration
app.config["MONGO_URI"] = os.getenv("MONGO_URI")
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB file size limit
mongo = PyMongo(app)

# Configure Cloudinary using environment variables
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET')
)


# ======================== AUTHENTICATION ROUTES ========================
@app.route('/logout')
def logout():
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

# ======================== DASHBOARD ROUTES ========================
@app.route('/')
def dashboard():
    return render_template('index.html')

@app.route('/dashboard')
def dash_board():
    return render_template('index.html')    

# ======================== CLINIC MANAGEMENT ROUTES ========================
@app.route('/clinics')
def clinics_page():
    return render_template('clinics.html')

@app.route('/api/clinics', methods=['GET', 'POST'])
def handle_clinics():    
    try:
        if request.method == 'POST':
            # Handle file upload to Cloudinary
            if 'image' not in request.files:
                return jsonify({"error": "No image provided"}), 400
                
            file = request.files['image']
            if file.filename == '':
                return jsonify({"error": "No selected image"}), 400
                
            # Note: We can skip the allowed_file check as Cloudinary handles many formats
            # and you can configure allowed types on their dashboard.

            # Upload the image file to Cloudinary
            # The 'folder' parameter organizes your uploads in Cloudinary
            upload_result = cloudinary.uploader.upload(file, folder="pneumoaid_clinics")
            
            # Get the secure URL from the Cloudinary response
            image_url = upload_result['secure_url']

            # Get form data
            clinic_data = {
                "name": request.form.get('name'),
                "identifier": request.form.get('identifier'),
                "location": request.form.get('location'),
                "status": request.form.get('status', 'active'),
                "image_url": image_url, # Store the Cloudinary URL
                "username": request.form.get('username'),
                "password": generate_password_hash(request.form.get('password'))
            }

            # Validate required fields
            required_fields = ["name", "identifier", "location", "username", "password"]
            missing_fields = [field for field in required_fields if not clinic_data.get(field)]
            if missing_fields:
                return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400

            # Check for existing username
            if mongo.db.clinics.find_one({"username": clinic_data['username']}):
                return jsonify({"error": "Username already exists"}), 409

            # Insert into database
            result = mongo.db.clinics.insert_one(clinic_data)
            
            return jsonify({
                "message": "Clinic created successfully",
                "id": str(result.inserted_id),
                "image_url": image_url
            }), 201

        elif request.method == 'GET':
            # Retrieve all clinics from the database
            clinics = list(mongo.db.clinics.find({}, {'password': 0}))
            
            # Prepare data for the frontend
            for clinic in clinics:
                clinic['_id'] = str(clinic['_id'])
                # The image URL is now a direct property, so no construction is needed
                # Ensure it exists before trying to access it
                if 'image_url' not in clinic:
                    clinic['image_url'] = None
                    
            return jsonify(clinics), 200

    except Exception as e:
        # A simple error response if something goes wrong
        return jsonify({'error': str(e)}), 500


# ======================== DATA ENDPOINTS ========================
@app.route("/api/stats")
def get_stats():
    try:
        total_hospitals = mongo.db.clinics.count_documents({})
        patients_logged = mongo.db.patients.count_documents({})
        total_places = len(mongo.db.clinics.distinct("location"))
        todays_appointments = mongo.db.appointments.count_documents({
            "date": datetime.today().strftime("%Y-%m-%d")
        })

        return jsonify({
            "totalHospitals": total_hospitals,
            "patientsLoggedIn": patients_logged,
            "totalPlaces": total_places,
            "todaysAppointments": todays_appointments
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/patient-analytics')
def get_patient_analytics():
    try:
        # Aggregate patient count by date
        pipeline = [
            {
                "$group": {
                    "_id": {
                        "$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}
                    },
                    "newPatients": {"$sum": 1}
                }
            },
            {"$sort": {"_id": 1}}
        ]

        results = list(mongo.db.patients.aggregate(pipeline))

        # Format result for frontend
        analytics = [
            {"day": r["_id"], "newPatients": r["newPatients"]}
            for r in results
        ]

        return jsonify(analytics), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/hospital-distribution')
def get_hospital_distribution():
    try:
        pipeline = [
            {
                "$project": {
                    "city": { 
                        "$arrayElemAt": [{ "$split": ["$location", ","] }, 0] 
                    }
                }
            },
            {
                "$group": {
                    "_id": "$city",
                    "count": {"$sum": 1}
                }
            },
            {"$sort": {"count": -1}}
        ]

        results = list(mongo.db.clinics.aggregate(pipeline))

        total = sum(r["count"] for r in results) or 1  # avoid division by zero

        distribution = [
            {"type": r["_id"].strip(), "percentage": round((r["count"] / total) * 100, 2)}
            for r in results
        ]

        return jsonify(distribution), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)