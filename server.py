from flask import Flask, render_template, request, redirect, url_for, session, flash
from pymongo import MongoClient
from datetime import datetime
from bson import ObjectId
import os


app = Flask(__name__)
app.secret_key = 'a_random_key' 

SERVER_HOST = os.environ.get('SERVER_HOST', 'localhost')
SERVER_PORT = int(os.environ.get('SERVER_PORT', 5000))
MONGO_DATABASE = os.environ.get('MONGO_DATABASE', 'HospitalDB')
MONGO_HOST = os.environ.get('MONGO_HOST', 'localhost')
MONGO_PORT = int(os.environ.get('MONGO_PORT', 27017))

#MongoDB Client Initialization
client = MongoClient(MONGO_HOST, MONGO_PORT)
db = client[MONGO_DATABASE]  #Database name
doctors_collection = db["doctors"]
patients_collection = db["patients"]
appointments_collection = db["appointments"]
admin_collection = db["admins"]

#Check if admin user exists, if not insert it
if admin_collection.count_documents({'username': 'admin'}) == 0:
    admin_collection.insert_one({'username': "admin", "password": "@dm1n"})  #insert admin account
    
#Routes
@app.route('/')
def home():
    if 'username' in session:
        username = session['username']
        #if username belongs to an admin
        admin = admin_collection.find_one({'username': username})
        if admin:
            return redirect(url_for('admin_home'))

        #if username belongs to a doctor
        doctor = doctors_collection.find_one({'username': username})
        if doctor:
            return redirect(url_for('doctor_home'))

        #if the username belongs to a patient
        patient = patients_collection.find_one({'username': username})
        if patient:
            return redirect(url_for('patient_home'))

    #if not logged in go to signup
    return redirect(url_for('signup'))

#Patient Sign-Up
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    error = None
    if request.method == 'POST':
        name = request.form['name']
        surname = request.form['surname']
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        amka  = request.form['amka']
        date_of_birth  = request.form['date_of_birth']
        
        if name and surname and email and username and password and amka and date_of_birth:
            #Check if username or email already exist
            if patients_collection.find_one({'$or': [{'username': username}, {'email': email}]}):
                error = 'Email or Username already in use'
            else:
                #Insert new patient if username and email are unique
                patient = {'name': name, 'surname': surname, 'email': email, 'username': username, 'password': password, 'amka': amka, 'date_of_birth': date_of_birth}
                patients_collection.insert_one(patient)
                session['username'] = username
                return redirect(url_for('patient_home'))
        else:
            error = 'All fields are required'
    return render_template('signup.html', error=error)

#Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        #if username and password belong to an admin
        admin = admin_collection.find_one({'username': username, 'password': password})
        if admin:
            session['username'] = username
            return redirect(url_for('admin_home'))

        #if username and password belong to a doctor
        doctor = doctors_collection.find_one({'username': username, 'password': password})
        if doctor:
            session['username'] = username
            return redirect(url_for('doctor_home'))

        #if username and password belong to a patient
        patient = patients_collection.find_one({'username': username, 'password': password})
        if patient:
            session['username'] = username
            return redirect(url_for('patient_home'))

        #If none of the above, credentials are invalid
        error = 'Invalid Credentials'
        
    return render_template('login.html', error=error)

@app.route('/admin_home')
def admin_home():
    if 'username' in session:
        username = session['username']
        return render_template('admin_home.html', username=username)
    else:
        return redirect(url_for('login'))


@app.route('/doctor_home')
def doctor_home():
    if 'username' in session:
        username = session['username']
        return render_template('doctor_home.html', username=username)
    else:
        return redirect(url_for('login'))

@app.route('/patient_home')
def patient_home():
    if 'username' in session:
        username = session['username']
        return render_template('patient_home.html', username=username)
    else:
        return redirect(url_for('login'))
#Logout
@app.route('/logout')
def logout():
    #Remove username from the session
    session.pop('username', None)
    return redirect(url_for('login'))

#Admin Routes
@app.route('/add_doctor', methods=['GET', 'POST'])
def add_doctor():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form['name']
        surname = request.form['surname']
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        appointment_cost  = request.form['appointment_cost']
        specialty  = request.form['specialty']

        if name and surname and email and username and password and appointment_cost and specialty:
            if specialty not in ['Radiologist', 'Hematologist', 'Allergist', 'Pathologist', 'Cardiologist']:
                flash('Specialty should be one of these: Radiologist, Hematologist, Allergist, Pathologist, Cardiologist', 'danger')
            else:
                #Check if the appointment cost is a positive number
                try:
                    appointment_cost = float(appointment_cost)
                    if appointment_cost <= 0:
                        flash('Appointment cost must be a positive number!', 'danger')
                        return render_template('add_doctor.html', doctors=list(doctors_collection.find()))
                except ValueError:
                    flash('Appointment cost must be a valid number!', 'danger')
                    return render_template('add_doctor.html', doctors=list(doctors_collection.find()))
                
                #Check if username or email already exist
                if doctors_collection.find_one({'$or': [{'username': username}, {'email': email}]}):
                    flash('Username or email already exists!', 'danger')
                else:
                    #Insert new doctor if username and email are unique
                    doctor = {'name': name, 'surname': surname, 'email': email, 'username': username, 'password': password, 'appointment_cost': appointment_cost, 'specialty': specialty}
                    doctors_collection.insert_one(doctor)
                    flash('Doctor added successfully!', 'success')
        else:
            flash('All fields are required!', 'danger')


    doctors = list(doctors_collection.find())
    return render_template('add_doctor.html', doctors=doctors)

@app.route('/change_doctor_password', methods=['GET','POST'])
def change_doctor_password():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        username = request.form['username']
        new_password = request.form['new_password']

        if doctors_collection.find_one({'username': username}):
            #Update doctor password in database
            result = doctors_collection.update_one({'username': username}, {'$set': {'password': new_password}})
            
            if result.modified_count > 0:
                flash('Doctor password changed successfully!', 'success')
            else:
                flash('Failed to change password!', 'danger')
        else:
            flash('Doctor not found!', 'danger')

    doctors = list(doctors_collection.find())
    return render_template('change_doctor_password.html', doctors=doctors)

@app.route('/delete_doctor', methods=['GET', 'POST'])
def delete_doctor():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        doctor_username = request.form['doctor_username']

        
        if doctors_collection.find_one({'username': doctor_username}):
            appointments_collection.delete_many({'doctor_username': doctor_username})   #Delete all appointments of doctor
            result = doctors_collection.delete_one({'username': doctor_username})       #Delete doctor

            if result.deleted_count > 0:
                flash('Doctor and their appointments deleted successfully!', 'success')
            else:
                flash('Failed to delete Doctor!', 'danger')
        else:
            flash('Doctor not found!', 'danger')
    
    doctors = list(doctors_collection.find())
    return render_template('delete_doctor.html', doctors=doctors)

#Delete Patient route
@app.route('/delete_patient', methods=['GET', 'POST'])
def delete_patient():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        patient_username = request.form['patient_username']
        
        if patients_collection.find_one({'username': patient_username}):
            appointments_collection.delete_many({'patient_username': patient_username}) #Delete all appointments of patient
            result = patients_collection.delete_one({'username': patient_username})     #Delete patient

            if result.deleted_count > 0:
                flash('Patient and their appointments deleted successfully!', 'success')
            else:
                flash('Failed to delete Patient!', 'danger')
        else:
            flash('Patient not found!', 'danger')
    
    patients = list(patients_collection.find())
    return render_template('delete_patient.html', patients=patients)


#Doctor routes
@app.route('/change_password', methods=['GET','POST'])
def change_password():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        username = session['username']
        new_password = request.form['new_password']

        if doctors_collection.find_one({'username': username}):
            #Update doctor password in database
            result = doctors_collection.update_one({'username': username}, {'$set': {'password': new_password}})
            
            if result.modified_count > 0:
                flash('Your password changed successfully!', 'success')
            else:
                flash('Failed to change password!', 'danger')
        else:
            flash('Username not found!', 'danger')

    return render_template('change_password.html')

@app.route('/change_appointment_cost', methods=['GET','POST'])
def change_appointment_cost():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        username = session['username']
        new_appointment_cost = request.form['new_appointment_cost']

        #Check if the new appointment cost is a positive number
        try:
            new_appointment_cost = float(new_appointment_cost)
            if new_appointment_cost <= 0:
                flash('Appointment cost must be a positive number!', 'danger')
                return render_template('change_appointment_cost.html')
        except ValueError:
            flash('Appointment cost must be a valid number!', 'danger')
            return render_template('change_appointment_cost.html')

        if doctors_collection.find_one({'username': username}):
            #Update doctor password in database
            result = doctors_collection.update_one({'username': username}, {'$set': {'appointment_cost': new_appointment_cost}})
            
            if result.modified_count > 0:
                #Update appointment cost for all appointments associated with the doctor
                appointments_collection.update_many({'doctor_username': username}, {'$set': {'appointment_cost': new_appointment_cost}})
                flash('Appointment cost changed successfully!', 'success')
            else:
                flash('Failed to change appointment cost!', 'danger')
        else:
            flash('Username not found!', 'danger')

    return render_template('change_appointment_cost.html')

#View appointments for doctor
@app.route('/doctor_view_appointments')
def doctor_view_appointments():
    if 'username' not in session:
        return redirect(url_for('login'))

    doctor_username = session['username']
    now = datetime.now()
    formatted_now = now.strftime('%Y-%m-%d')

    appointments = list(appointments_collection.find({
        'doctor_username': doctor_username,
        'date': {'$gte': formatted_now}
    }))

    return render_template('doctor_view_appointments.html', appointments=appointments)


#Appointment Routes
@app.route('/book_appointment', methods=['GET', 'POST'])
def book_appointment():
    if 'username' not in session:
        return redirect(url_for('login'))

    error = None
    success = None
    if request.method == 'POST':
        patient_username = session['username']
        date = request.form['date']
        time = request.form['time']
        specialty = request.form['specialty']
        reason = request.form['reason']

        #Check if selected date is in the future
        selected_date = datetime.strptime(date, '%Y-%m-%d')
        current_date = datetime.now()
        if selected_date < current_date:
            error = "Selected date must be valid."
            return render_template('book_appointment.html', error=error)
        
        patient = patients_collection.find_one({'username': patient_username})  #Find patient
        if not patient:
            error = "Patient not found."
            return render_template('book_appointment.html', error=error)

        #Find available doctor with selected specialty
        available_doctor = doctors_collection.find_one({
            'specialty': specialty,
            'username': {'$nin': [appointment['doctor_username'] for appointment in appointments_collection.find({'date': date, 'time': time})]}   #Find doctor who's id is not already in another appointment at set date and time
        })

        if not available_doctor:
            error = "No available doctor for the selected date and time."
            return render_template('book_appointment.html', error=error)

        #Book appointment
        appointment = {
            'patient_name': patient['name'],
            'patient_surname': patient['surname'],
            'doctor_name': available_doctor['name'],
            'doctor_surname': available_doctor['surname'],
            'date': date,
            'time': time,
            'appointment_cost': available_doctor['appointment_cost'],
            'reason': reason,
            'doctor_specialty': specialty,
            'doctor_username': available_doctor['username'],
            'patient_username': patient_username
        }

        appointments_collection.insert_one(appointment)
        success = "Appointment booked successfully."

    return render_template('book_appointment.html', error=error, success=success)

#View all future appointments for patients
@app.route('/view_appointments')
def view_appointments():
    if 'username' not in session:
        return redirect(url_for('login'))

    patient_username = session['username']
    now = datetime.now()
    formatted_now = now.strftime('%Y-%m-%d')

    appointments = list(appointments_collection.find({
        'patient_username': patient_username,
        'date': {'$gte': formatted_now}
    }))
    
    return render_template('patient_view_appointments.html', appointments=appointments)

#View appointment details for patients  
@app.route('/view_appointment_details/<appointment_id>')
def view_appointment_details(appointment_id):
    print("Received appointment ID:", appointment_id) #print for testing
    if 'username' not in session:
        return redirect(url_for('login'))

    appointment = appointments_collection.find_one({'_id': ObjectId(appointment_id)})
    if not appointment:
        flash('Appointment not found!', 'danger')
        return redirect(url_for('view_appointments'))

    return render_template('patient_view_appointment_details.html', appointment=appointment)


#Delete an appointment
@app.route('/delete_appointment/<appointment_id>', methods=['POST'])
def delete_appointment(appointment_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    result = appointments_collection.delete_one({'_id': ObjectId(appointment_id)})
    if result.deleted_count > 0:
        flash('Appointment deleted successfully!', 'success')
    else:
        flash('Failed to delete appointment!', 'danger')

    return redirect(url_for('view_appointments'))

# Run the Flask App
if __name__ == '__main__':
    app.run(debug=True, host=SERVER_HOST, port=SERVER_PORT)