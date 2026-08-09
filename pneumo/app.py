from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, make_response
from flask_pymongo import PyMongo
from werkzeug.security import generate_password_hash, check_password_hash
import os
import csv
from datetime import datetime, timedelta
from io import StringIO
from dotenv import load_dotenv
from bson import Binary
from werkzeug.utils import secure_filename
import base64
from bson import ObjectId
import numpy as np
from base64 import b64encode
from flask import Flask, render_template, request, jsonify
from flask_mail import Mail, Message
from pymongo import MongoClient
import random
import re
import openai
import google.generativeai as genai
from collections import defaultdict
from dateutil.relativedelta import relativedelta
from bson.errors import InvalidId  
from flask_cors import CORS
import google.generativeai as genai
import tensorflow as tf
from PIL import Image
from tensorflow.keras.preprocessing.image import load_img, img_to_array
import numpy as np



# Load environment variables
load_dotenv()

app = Flask(__name__ , template_folder='templates')
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key')  # Set a proper secret in production
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'rishilshajan1@gmail.com'
app.config['MAIL_PASSWORD'] = 'sfgh ulpp jlhh khoy'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
mail = Mail(app)
CORS(app)

# MongoDB configuration
app.config["MONGO_URI"] = os.getenv("MONGO_URI")

mongo = PyMongo(app)
db = mongo.db
# Collection names 
CLINICS_COL = 'clinics'
USERS_COLLECTION = 'users'
PATIENTS_COL = 'patients'
APPOINTMENTS_COL = 'appointments'
ASSESSMENTS_COL = 'assessments'
DOCTORS_COL = 'doctors'
HOSPITALS_COL = 'hospitals'
HOSPITAL_ACCESS_CODE = "QWERTYUIOP"

# ... (keep previous imports and configurations)

# Configure upload folder
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # Ensure upload directory exists

# Load VGG19 model
MODEL_PATH = r'F:\Pneumo_work\PNEUMOAID\pneumo\vgg19_trained_model.h5'
vggmodel = tf.keras.models.load_model(MODEL_PATH)
CLASS_LABELS = ['Bacterial Pneumonia', 'Viral Pneumonia', 'Normal']

def preprocess_image(image_path):
    img = load_img(image_path, target_size=(224, 224))
    img_array = img_to_array(img)
    img_array = img_array / 255.0  # Normalize
    return np.expand_dims(img_array, axis=0)

@app.route('/check_xray', methods=['GET', 'POST'])
def check_xray():
    if request.method == 'POST':
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400

        try:
            # Secure filename and save temporarily
            filename = secure_filename(file.filename)
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(save_path)

            # Process and predict
            img_array = preprocess_image(save_path)
            prediction = vggmodel.predict(img_array)
            class_index = np.argmax(prediction, axis=1)[0]
            result = CLASS_LABELS[class_index]

            return jsonify({
                'result': result,
                'confidence': float(np.max(prediction)),
                'probabilities': prediction.tolist()[0]
            })

        except Exception as e:
            app.logger.error(f"Prediction error: {str(e)}")
            return jsonify({'error': 'Failed to process image'}), 500

        finally:
            # Cleanup uploaded file
            if os.path.exists(save_path):
                os.remove(save_path)

    # GET request - render upload page
    return render_template('check_xray.html')

# ... (keep other routes and configurations)
    
# Configure Gemini API
genai.configure(api_key="AIzaSyCFPPL4wfyJpCt4jDzwr2LNolVC0p8GQIc")
model = genai.GenerativeModel(
    model_name="gemini-1.5-pro-latest",
    generation_config={
        "max_output_tokens": 50,  # Keep responses short
        "temperature": 0.7
    }
)

# Session storage with auto-cleaning
sessions = defaultdict(dict)
RELEVANT_KEYWORDS = {
    'pneumonia', 'lung', 'breath', 'asthma', 'cough', 'x-ray',
    'respiratory', 'bronchitis', 'tuberculosis', 'copd', 'pulmonary',
    'chest pain', 'wheezing', 'sputum', 'oxygen', 'inhaler'
}

##################### CHATBOT ######################
@app.route('/chatbot')
def chatbot():
    # Start new session when accessing chatbot
    session.clear()
    return render_template('chatbot.html')

@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        user_input = data.get("message", "").strip()
        
        # Initialize session if not exists
        if 'chat_history' not in session:
            session['chat_history'] = []
            session['first_message'] = True

        # Handle empty input
        if not user_input:
            return jsonify({"response": "Please provide symptoms or ask a question."})

        # Initial greeting
        if session['first_message']:
            session['first_message'] = False
            return jsonify({
                "response": "Hello I am Pneumo, your personal Healthcare Companion. How can I assist with lung health today?"
            })

        # Validate medical relevance
        if not any(keyword in user_input.lower() for keyword in RELEVANT_KEYWORDS):
            return jsonify({
                "response": "I specialize in pneumonia and lung health. Ask about symptoms, treatments, or prevention."
            })

        # Generate response
        prompt = f"As Pneumo the lung health specialist, answer in 25 words max: {user_input}"
        response = model.generate_content(prompt)
        
        # Format response
        cleaned_response = ' '.join(response.text.split()[:25]).rstrip('.,') + '.'
        
        # Store conversation history
        session['chat_history'].append({
            'user': user_input,
            'bot': cleaned_response
        })

        return jsonify({"response": cleaned_response})

    except Exception as e:
        return jsonify({
            "response": "Apologies, I'm experiencing technical difficulties. Please try again.",
            "error": str(e)
        }), 500

###################### VOICE ASSISTANT ####################
@app.route('/voice_assistant')
def voice_assistant():
    return render_template('voice_bot.html') 

@app.route('/voice', methods=['POST'])
def voice_reply():
    data = request.get_json()
    user_message = data.get("message", "").strip()

    if not user_message:
        return jsonify(reply="Sorry, I didn't catch that. Please try again.")

    # ✅ Updated prompt for shorter responses
    prompt = f"You are Pneumo, a respiratory health assistant. Answer clearly and briefly in 1–2 sentences: '{user_message}'"

    try:
        response = model.generate_content(prompt)
        reply_text = response.text.strip()
        return jsonify(reply=reply_text)
    except Exception as e:
        print("Gemini Error:", e)
        return jsonify(reply="Sorry, there was an error processing your request.")


# Route for booking page
@app.route('/booking')
def booking():
    return render_template('booking.html')

@app.route('/api/hospitals')
def get_hospitals():
    hospitals = list(db.hospitals.find({}, {'name': 1}))
    return jsonify([{'_id': str(h['_id']), 'name': h['name']} for h in hospitals])

@app.route('/api/doctors/<hospital_id>')
def get_doctors(hospital_id):
    try:
        hospital = db.hospitals.find_one({'_id': ObjectId(hospital_id)})
        if not hospital:
            return jsonify({'error': 'Hospital not found'}), 404

        # Include specialization in projection
        doctors = list(db.doctors.find(
            {'hospital_id': ObjectId(hospital_id)},
            {'name': 1, 'specialization': 1, '_id': 1}
        ))
        
        return jsonify([{
            'id': str(d['_id']),
            'name': d['name'],
            'specialization': d.get('specialization', 'General Medicine')
        } for d in doctors])

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/api/sessions/<doctor_id>')
def get_doctor_sessions(doctor_id):
    try:
        if not doctor_id or doctor_id == "undefined":
            return jsonify({"error": "Doctor ID required"}), 400

        now = datetime.utcnow()
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)

        sessions = list(db.sessions.find({
            "doctor_id": ObjectId(doctor_id),
            "date": {"$gte": start_of_day, "$lt": end_of_day}
        }))

        return jsonify([{
            "id": str(s["_id"]),
            "date": s["date"].strftime("%Y-%m-%d"),
            "start_time": s["start_time"],
            "end_time": s["end_time"],
            "session_type": s["session_type"]
        } for s in sessions])
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/api/bookings', methods=['POST'])
def book_appointment():
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No data received'}), 400

        # Validate required fields
        required_fields = ['name', 'age', 'gender', 'email', 'phone', 'hospital', 'doctor', 'time']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400

        # Ensure collections exist
        if 'appointments' not in db.list_collection_names():
            db.create_collection('appointments')
        if 'sessions' not in db.list_collection_names():
            db.create_collection('sessions')

        session_id = ObjectId(data['time'])

        # Fetch current session to get current number of booked patients
        current_session = db.sessions.find_one({'_id': session_id})
        if not current_session:
            return jsonify({'error': 'Session not found'}), 404

        booked_patients = current_session.get('booked_patients', 0)
        max_patients = current_session.get('max_patients', 0)

        # Check if booking is allowed
        if booked_patients >= max_patients:
            return jsonify({'error': 'No slots available for this session'}), 400

        # Token is booked_patients + 1
        token = booked_patients + 1

        # Create appointment document
        appointment = {
            'patient_name': data['name'],
            'age': int(data['age']),
            'gender': data['gender'],
            'email': data['email'],
            'phone': data['phone'],
            'hospital_id': ObjectId(data['hospital']),
            'doctor_id': ObjectId(data['doctor']),
            'session_id': session_id,
            'token': token,
            'status': 'pending',
            'booking_date': datetime.now()
        }

        # Database operations
        with db.client.start_session() as session:
            with session.start_transaction():
                db.appointments.insert_one(appointment, session=session)

                update_result = db.sessions.update_one(
                    {'_id': session_id},
                    {'$inc': {'booked_patients': 1}},
                    session=session
                )

                if update_result.matched_count == 0:
                    raise ValueError('Session not found during update')

        # Send email
        doctor = db.doctors.find_one({'_id': ObjectId(data['doctor'])}, {'name': 1, 'specialization': 1})
        hospital = db.hospitals.find_one({'_id': ObjectId(data['hospital'])}, {'name': 1})
        session_time = current_session.get('time', 'N/A')
        formatted_time = session_time.strftime("%A, %d %B %Y at %I:%M %p") if isinstance(session_time, datetime) else session_time

        msg = Message('Appointment Confirmation',
                     sender='noreply@hospital.com',
                     recipients=[data['email']])
        msg.body = f"""Dear {data['name']},

        Your appointment has been successfully confirmed. Here are the details:

        Patient Name     : {data['name']}
        Age              : {data['age']}
        Gender           : {data['gender']}
        Hospital         : {hospital.get('name', 'N/A')}
        Doctor           : Dr. {doctor.get('name', 'N/A')} ({doctor.get('specialization', 'General')})
        Token Number     : {token}

        Please arrive at the hospital at least 15 minutes before your scheduled time.

        Thank you for choosing our services.

        Warm regards,  
        {hospital.get('name', 'N/A')}
        """
        mail.send(msg)

        return jsonify({'message': 'Booking confirmed!', 'token': token})

    except InvalidId as e:
        return jsonify({'error': 'Invalid ID format'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def b64encode_filter(data):
    if data:
        return b64encode(data).decode('utf-8')
    return None

app.jinja_env.filters['b64encode'] = b64encode_filter

@app.route('/manage_doctors', methods=['GET', 'POST'])
def manage_doctors():
    if request.method == 'POST':
        hospital_name = request.form.get('hospital_name')
        access_code = request.form.get('access_code')
        
        hospital = db.hospitals.find_one({'name': hospital_name})
        if not hospital or access_code != HOSPITAL_ACCESS_CODE:
            flash('Invalid credentials', 'error')
            return redirect(url_for('manage_doctors'))
        
        session['hospital_id'] = str(hospital['_id'])
        session['hospital_name'] = hospital['name']
        return redirect(url_for('doctors_dashboard'))
    
    return render_template('access_code.html')

@app.route('/doctors_dashboard')
def doctors_dashboard():
    if 'hospital_id' not in session:
        return redirect(url_for('manage_doctors'))
    
    try:
        doctors = list(db.doctors.find({
            'hospital_id': ObjectId(session['hospital_id'])
        }))
        return render_template('doctors_dashboard.html',
                             doctors=doctors,
                             hospital_name=session['hospital_name'])
    
    except Exception as e:
        flash(f'Error loading doctors: {str(e)}', 'error')
        return redirect(url_for('manage_doctors'))

@app.route('/get_doctor/<doctor_id>')
def get_doctor(doctor_id):
    try:
        doctor = db.doctors.find_one({
            '_id': ObjectId(doctor_id),
            'hospital_id': ObjectId(session['hospital_id'])
        })
        if not doctor:
            return jsonify({'error': 'Doctor not found'}), 404
            
        # Debugging output
        print("Doctor data from DB:", doctor)
        
        return jsonify({
            '_id': str(doctor['_id']),
            'name': doctor['name'],
            'specialization': doctor.get('specialization', ''),
            'qualification': doctor.get('qualification', ''),
            'experience': doctor.get('experience', 0)
        })
    except Exception as e:
        print("Error in get_doctor:", str(e))
        return jsonify({'error': str(e)}), 500

@app.route('/add_doctor', methods=['POST'])
def add_doctor():
    if 'hospital_id' not in session:
        flash('Access denied', 'error')
        return redirect(url_for('manage_doctors'))
    
    try:
        doctor_data = {
            'name': request.form.get('name'),
            'specialization': request.form.get('specialization'),
            'qualification': request.form.get('qualification'),
            'experience': int(request.form.get('experience')),
            'hospital_id': ObjectId(session['hospital_id']),
            'hospital_name': session['hospital_name'],
            'created_at': datetime.utcnow()
        }

        if 'photo' in request.files:
            photo = request.files['photo']
            if photo.filename != '':
                doctor_data['photo'] = Binary(photo.read())

        doctor_id = request.form.get('doctor_id')
        if doctor_id:
            result = db.doctors.update_one(
                {'_id': ObjectId(doctor_id)},
                {'$set': doctor_data}
            )
            if result.modified_count == 0:
                raise Exception('Doctor update failed')
            flash('Doctor updated successfully', 'success')
        else:
            result = db.doctors.insert_one(doctor_data)
            if not result.inserted_id:
                raise Exception('Doctor creation failed')
            flash('Doctor added successfully', 'success')

        return redirect(url_for('doctors_dashboard'))
    
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('doctors_dashboard'))

@app.route('/delete_doctor/<doctor_id>')
def delete_doctor(doctor_id):
    try:
        result = db.doctors.delete_one({
            '_id': ObjectId(doctor_id),
            'hospital_id': ObjectId(session['hospital_id'])
        })
        
        if result.deleted_count == 0:
            flash('Doctor not found', 'error')
        else:
            flash('Doctor deleted successfully', 'success')
            
    except Exception as e:
        flash(f'Error deleting doctor: {str(e)}', 'error')
    
    return redirect(url_for('doctors_dashboard'))



   

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/hospital-login', methods=['GET', 'POST'])
def hospital_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        hospital = mongo.db.hospitals.find_one({'username': username})
        
        if hospital and check_password_hash(hospital['password'], password):
            session['hospital_logged_in'] = True
            session['hospital_id'] = str(hospital['_id'])
            session['hospital_name'] = hospital.get('name', 'Clinic')  # Store clinic name
            return redirect(url_for('clinic_dashboard'))
        
        flash('Invalid credentials', 'error')
    return render_template('hospital_login.html')


# Add allowed extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/api/clinics/metrics')
def clinic_metrics():
    if 'hospital_logged_in' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    hospital_id = session['hospital_id']

    try:
        today = datetime.utcnow().date()
        start = datetime.combine(today, datetime.min.time())
        end = datetime.combine(today + timedelta(days=1), datetime.min.time())

        today_patients = mongo.db.appointments.count_documents({
            'hospital_id': ObjectId(hospital_id),
            'booking_date': {'$gte': start, '$lt': end}
        })

        pending_appointments = mongo.db.appointments.count_documents({
            'hospital_id': ObjectId(hospital_id),
            'status': 'pending',
            'booking_date': {'$gte': start, '$lt': end}
        })

        completed_appointments = mongo.db.appointments.count_documents({
            'hospital_id': ObjectId(hospital_id),
            'status': 'completed'
        })

        metrics = {
            'today_patients': today_patients,
            'pending_appointments': pending_appointments,
            'completed_appointments': completed_appointments
        }

        return jsonify(metrics)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/clinic-dashboard')
def clinic_dashboard():
    if 'hospital_logged_in' not in session:
        return redirect(url_for('hospital_login'))
    
    try:
        # Get metrics from API endpoint
        metrics_response = clinic_metrics().get_json()
        if 'error' in metrics_response:
            raise Exception(metrics_response['error'])

        return render_template('dashboard.html', metrics=metrics_response)
    
    except Exception as e:
        print(f"Dashboard error: {str(e)}")
        return render_template('error.html', message="Failed to load dashboard data"), 500

@app.route('/xray/<assessment_id>')
def view_xray(assessment_id):
    assessment = mongo.db.assessments.find_one({'_id': ObjectId(assessment_id)})
    if not assessment or 'xray_image' not in assessment:
        return "Image not found", 404
    
    response = make_response(assessment['xray_image'])
    response.headers.set('Content-Type', 'image/jpeg')
    response.headers.set('Content-Disposition', 'inline', filename='xray.jpg')
    return response


@app.route('/patient-assessment', methods=['GET', 'POST'])
def patient_assessment():
    if 'hospital_logged_in' not in session:
        return redirect(url_for('hospital_login'))

    hospital_id = ObjectId(session['hospital_id'])

    # Get today's appointments for this hospital
    today = datetime.utcnow().date()
    start = datetime.combine(today, datetime.min.time())
    end = datetime.combine(today + timedelta(days=1), datetime.min.time())

    todays_patients = list(mongo.db.appointments.aggregate([
        {
            '$match': {
                'hospital_id': hospital_id,
                'booking_date': {'$gte': start, '$lt': end},
                'status': 'pending'
            }
        },
        {
            '$group': {
                '_id': '$patient_name'
            }
        },
        {
            '$project': {
                'name': '$_id',
                '_id': 0
            }
        }
    ]))

    patient_names = [p['name'] for p in todays_patients]

    # Handle form submission
    if request.method == 'POST':
        try:
            # Check and read uploaded file
            if 'xray_image' not in request.files:
                flash('No X-ray image uploaded', 'danger')
                return redirect(request.url)

            file = request.files['xray_image']
            if file.filename == '':
                flash('No selected file', 'danger')
                return redirect(request.url)

            if file and allowed_file(file.filename):
                xray_data = Binary(file.read())
            else:
                flash('Allowed file types are png, jpg, jpeg, gif', 'danger')
                return redirect(request.url)

            # Ensure the 'assessments' collection exists
            if 'assessments' not in mongo.db.list_collection_names():
                mongo.db.create_collection('assessments')

            # Prepare assessment data
            assessment_data = {
                'hospital_id': hospital_id,
                'patient_name': request.form.get('patient'),
                'date': datetime.strptime(request.form.get('date'), '%Y-%m-%d'),
                'symptoms': request.form.getlist('symptoms'),
                'vitals': {
                    'temperature': float(request.form.get('temperature')),
                    'heart_rate': int(request.form.get('heart_rate')),
                    'respiratory_rate': int(request.form.get('respiratory_rate')),
                    'oxygen_saturation': int(request.form.get('oxygen_saturation')),
                    'blood_pressure': request.form.get('blood_pressure')
                },
                'diagnosis': request.form.get('diagnosis'),
                'notes': request.form.get('notes'),
                'xray_image': xray_data,
                'status': 'Pending Review',
                'created_at': datetime.utcnow()
            }
            # Add status to assessment explicitly
            assessment_data['status'] = 'Completed'  # Change assessment status
            mongo.db.assessments.insert_one(assessment_data)
            mongo.db.appointments.update_many(
    {
        'hospital_id': hospital_id,
        'patient_name': assessment_data['patient_name'],
        'booking_date': {'$gte': start, '$lt': end},
        'status': 'pending'
    },
    {
        '$set': {'status': 'completed'}
    }
)

            flash('Assessment submitted successfully!', 'success')

        except Exception as e:
            flash(f'Error submitting assessment: {str(e)}', 'danger')

        return redirect(url_for('patient_assessment'))

    # Fetch recent assessments
    assessments = list(mongo.db.assessments.find({'hospital_id': hospital_id}).sort('created_at', -1).limit(10))

    return render_template('patient_assessment.html',
                           patient_names=patient_names,
                           assessments=assessments,
                           datetime=datetime)


@app.route('/api/cases')
def get_case_data():
    if 'hospital_logged_in' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    hospital_id = session['hospital_id']
    
    cases = {
        'bacterial': mongo.db.assessments.count_documents({
            'hospital_id': hospital_id,
            'diagnosis': 'Bacterial Pneumonia'
        }),
        'viral': mongo.db.assessments.count_documents({
            'hospital_id': hospital_id,
            'diagnosis': 'Viral Pneumonia'
        }),
        'normal': mongo.db.assessments.count_documents({
            'hospital_id': hospital_id,
            'diagnosis': 'Normal'
        })
    }
    
    total = sum(cases.values()) or 1  # Prevent division by zero
    percentages = {k: (v/total)*100 for k, v in cases.items()}
    
    return jsonify({
        'counts': cases,
        'percentages': percentages,
        'total': total
    })

@app.route('/export/<collection>')
def export_data(collection):
    if 'hospital_logged_in' not in session:
        return redirect(url_for('hospital_login'))
    
    hospital_id = session['hospital_id']
    data = list(mongo.db[collection].find({'hospital_id': hospital_id}, {'_id': 0}))
    
    if not data:
        flash('No data available to export', 'error')
        return redirect(request.referrer)
    
    output = StringIO()
    writer = csv.writer(output)
    
    # Write header
    if data:
        writer.writerow(data[0].keys())
    
    # Write data
    for row in data:
        writer.writerow(row.values())
    
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = f"attachment; filename={collection}_export.csv"
    response.headers["Content-type"] = "text/csv"
    return response

@app.route('/user-login', methods=['GET', 'POST'])
def user_login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = mongo.db[USERS_COLLECTION].find_one({'email': email}) 
        
        if user and check_password_hash(user['password'], password):
            session['user_logged_in'] = True
            session['user_id'] = str(user['_id'])
            session['user_name'] = user.get('name', 'User')
            session['user_color'] = "#FFA500"  # Always Orange
            return redirect(url_for('user_dashboard'))
        
        flash('Invalid email or password', 'error')
        return redirect(url_for('user_login'))
    
    return render_template('user_login.html')

@app.route('/user-dashboard')
def user_dashboard():
    if 'user_logged_in' in session:
        return render_template('user_dashboard.html')
    return redirect(url_for('user_login'))

@app.route('/user-register', methods=['GET', 'POST'])
def user_register():
    if request.method == 'POST':
        # Get form data with proper validation
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').lower().strip()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '').strip()
        
        # Validate required fields
        if not all([name, email, phone, password]):
            flash('All fields are required', 'error')
            return redirect(url_for('user_register'))
        
        # Validate email format
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            flash('Invalid email format', 'error')
            return redirect(url_for('user_register'))
        
        # Check if email exists
        if db.users.find_one({'email': email}):
            flash('Email already registered', 'error')
            return redirect(url_for('user_register'))
        
        # Create new user
        try:
            db.users.insert_one({
                'name': name,
                'email': email,
                'phone': phone,
                'password': generate_password_hash(password),
                'created_at': datetime.utcnow()
            })
            flash('Registration successful! Please login', 'success')
            return redirect(url_for('user_login'))
        
        except Exception as e:
            flash('Registration failed. Please try again.', 'error')
            return redirect(url_for('user_register'))
    
    return render_template('user_register.html')

@app.route('/schedule_session', methods=['GET'])
def schedule_session():
    if 'hospital_id' not in session:
        return redirect(url_for('access_code'))
    
    # Get hospital's doctors
    doctors = list(db.doctors.find(
        {'hospital_id': ObjectId(session['hospital_id'])},
        {'name': 1, 'specialization': 1}
    ))
    
    return render_template('schedule_session.html',
                         doctors=doctors,
                         hospital_name=session.get('hospital_name'),
                         datetime = datetime)

@app.route('/api/sessions', methods=['GET'])
def get_sessions():
    if 'hospital_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        month = int(request.args.get('month', datetime.now().month))
        year = int(request.args.get('year', datetime.now().year))
        
        start_date = datetime(year, month, 1)
        end_date = start_date + relativedelta(months=1, day=1)

        pipeline = [
            {'$match': {
                'hospital_id': ObjectId(session['hospital_id']),
                'date': {'$gte': start_date, '$lt': end_date}
            }},
            {'$lookup': {
                'from': 'doctors',
                'localField': 'doctor_id',
                'foreignField': '_id',
                'as': 'doctor'
            }},
            {'$unwind': '$doctor'},
            {'$project': {
                '_id': 0,
                'session_id': {'$toString': '$_id'},
                'date': {'$dateToString': {'format': '%Y-%m-%d', 'date': '$date'}},
                'start_time': 1,
                'end_time': 1,
                'session_type': 1,
                'doctor_name': '$doctor.name',
                'max_patients': 1,
                'booked_patients': 1
            }}
        ]
        
        sessions = list(db.sessions.aggregate(pipeline))
        return jsonify(sessions)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/sessions', methods=['POST'])
def create_session():
    if 'hospital_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        data = request.get_json()
        
        # Validate doctor exists in hospital
        doctor = db.doctors.find_one({
            '_id': ObjectId(data['doctor_id']),
            'hospital_id': ObjectId(session['hospital_id'])
        })
        if not doctor:
            return jsonify({'error': 'Doctor not found'}), 404

        # Validate session data
        session_date = datetime.strptime(data['date'], '%Y-%m-%d')
        start_time = datetime.strptime(data['start_time'], '%H:%M')
        end_time = datetime.strptime(data['end_time'], '%H:%M')
        
        if start_time >= end_time:
            return jsonify({'error': 'Invalid time range'}), 400

        # Check for overlapping sessions
        existing = db.sessions.find_one({
            'doctor_id': ObjectId(data['doctor_id']),
            'date': session_date,
            '$or': [
                {'start_time': {'$lt': data['end_time']},
                 'end_time': {'$gt': data['start_time']}}
            ]
        })
        if existing:
            return jsonify({'error': 'Time slot conflict'}), 409

        # Create session document
        session_data = {
            'hospital_id': ObjectId(session['hospital_id']),
            'doctor_id': ObjectId(data['doctor_id']),
            'date': session_date,
            'start_time': data['start_time'],
            'end_time': data['end_time'],
            'session_type': data['session_type'],
            'duration': int(data['duration']),
            'max_patients': int(data['max_patients']),
            'booked_patients': 0,
            'created_at': datetime.utcnow()
        }

        result = db.sessions.insert_one(session_data)
        return jsonify({
            'message': 'Session created',
            'session_id': str(result.inserted_id)
        }), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))
   

if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(debug=True, port=5000)
