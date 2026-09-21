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
@app.route('/', methods=['GET', 'POST'])
def login():
    if session.get('logged_in'):
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        ADMIN_USERNAME = os.getenv("Admin_Username")
        ADMIN_PASSWORD = os.getenv("Admin_Password")

        print(f"DEBUG: ADMIN_USERNAME = '{ADMIN_USERNAME}'")
        print(f"DEBUG: ADMIN_PASSWORD = '{ADMIN_PASSWORD}'")

        # Check if environment variables were loaded correctly
        if ADMIN_USERNAME is None or ADMIN_PASSWORD is None:
            print("Error: Admin credentials not found in environment variables.")
            flash('Login service error. Please try again later.', 'error')
            return redirect(url_for('login'))

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials', 'error')
            return redirect(url_for('login'))
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

# ======================== DASHBOARD ROUTES ========================
@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('index.html')

# ======================== CLINIC MANAGEMENT ROUTES ========================
@app.route('/clinics')
def clinics_page():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('clinics.html')

@app.route('/api/clinics', methods=['GET', 'POST', 'PUT', 'DELETE'])
def handle_clinics():
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        # ============================================================
        # GET - Fetch all clinics
        # ============================================================
        if request.method == 'GET':

            clinics = list(
                mongo.db.clinics.find(
                    {},
                    {'password': 0}
                )
            )

            for clinic in clinics:
                clinic['_id'] = str(clinic['_id'])

                if 'image_url' not in clinic:
                    clinic['image_url'] = None

            return jsonify(clinics), 200

        # ============================================================
        # POST - Create a new clinic
        # ============================================================
        elif request.method == 'POST':

            if 'image' not in request.files:
                return jsonify({
                    "error": "No image provided"
                }), 400

            file = request.files['image']

            if file.filename == '':
                return jsonify({
                    "error": "No selected image"
                }), 400

            # Upload image to Cloudinary
            upload_result = cloudinary.uploader.upload(
                file,
                folder="pneumoaid_clinics"
            )

            image_url = upload_result['secure_url']

            clinic_data = {
                "name": request.form.get('name'),
                "identifier": request.form.get('identifier'),
                "location": request.form.get('location'),
                "type": request.form.get('type', 'other'),
                "status": request.form.get('status', 'active'),
                "image_url": image_url,
                "username": request.form.get('username'),
                "password": generate_password_hash(
                    request.form.get('password')
                )
            }

            required_fields = [
                "name",
                "identifier",
                "location",
                "username",
                "password"
            ]

            missing_fields = [
                field
                for field in required_fields
                if not clinic_data.get(field)
            ]

            if missing_fields:
                return jsonify({
                    "error": f"Missing required fields: {', '.join(missing_fields)}"
                }), 400

            # Check duplicate username
            if mongo.db.clinics.find_one({
                "username": clinic_data['username']
            }):
                return jsonify({
                    "error": "Username already exists"
                }), 409

            result = mongo.db.clinics.insert_one(clinic_data)

            return jsonify({
                "message": "Clinic created successfully",
                "id": str(result.inserted_id),
                "image_url": image_url
            }), 201

        # ============================================================
        # PUT - Update an existing clinic
        # ============================================================
        elif request.method == 'PUT':

            clinic_id = request.form.get('clinic_id')

            if not clinic_id:
                return jsonify({
                    "error": "Clinic ID is required"
                }), 400

            try:
                object_id = ObjectId(clinic_id)
            except Exception:
                return jsonify({
                    "error": "Invalid clinic ID"
                }), 400

            # Check if clinic exists
            existing_clinic = mongo.db.clinics.find_one({
                "_id": object_id
            })

            if not existing_clinic:
                return jsonify({
                    "error": "Clinic not found"
                }), 404

            # --------------------------------------------------------
            # Check username uniqueness
            # --------------------------------------------------------
            username = request.form.get('username')

            if username:
                existing_username = mongo.db.clinics.find_one({
                    "username": username,
                    "_id": {"$ne": object_id}
                })

                if existing_username:
                    return jsonify({
                        "error": "Username already exists"
                    }), 409

            # --------------------------------------------------------
            # Prepare fields to update
            # --------------------------------------------------------
            update_data = {
                "name": request.form.get('name'),
                "identifier": request.form.get('identifier'),
                "location": request.form.get('location'),
                "type": request.form.get('type', 'other'),
                "status": request.form.get('status', 'active'),
                "username": username
            }

            # --------------------------------------------------------
            # Password
            # Only update password if user entered a new password
            # --------------------------------------------------------
            new_password = request.form.get('password')

            if new_password and new_password.strip():
                update_data["password"] = generate_password_hash(
                    new_password
                )

            # --------------------------------------------------------
            # Image
            # Only upload if a new image was selected
            # --------------------------------------------------------
            if 'image' in request.files:

                file = request.files['image']

                if file and file.filename:

                    upload_result = cloudinary.uploader.upload(
                        file,
                        folder="pneumoaid_clinics"
                    )

                    update_data["image_url"] = upload_result['secure_url']

            # --------------------------------------------------------
            # Update MongoDB
            # --------------------------------------------------------
            mongo.db.clinics.update_one(
                {"_id": object_id},
                {"$set": update_data}
            )

            return jsonify({
                "message": "Clinic updated successfully"
            }), 200

        # ============================================================
        # DELETE - Delete an existing clinic
        # ============================================================
        elif request.method == 'DELETE':
            clinic_id = request.args.get('clinic_id')
            
            if not clinic_id:
                return jsonify({
                    "error": "Clinic ID is required"
                }), 400
                
            try:
                object_id = ObjectId(clinic_id)
            except Exception:
                return jsonify({
                    "error": "Invalid clinic ID"
                }), 400
                
            mongo.db.clinics.delete_one({"_id": object_id})
            
            return jsonify({
                "message": "Clinic deleted successfully"
            }), 200

    except Exception as e:
        print(f"Clinic API error: {e}")

        return jsonify({
            "error": str(e)
        }), 500

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
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401

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
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401

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