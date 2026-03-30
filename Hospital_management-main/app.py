from flask import Flask, render_template, request, redirect, url_for, flash, session
from extension import db
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime,timedelta
from sqlalchemy import or_


app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///hospital.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.secret_key = "743263"

db.init_app(app)
from models import *

#time validation fun
def validate_time_slot(slot, slot_type):
    
    if "-" not in slot:
        return False

    parts = slot.split("-")
    if len(parts) != 2:
        return False

    start, end = [s.strip().lower() for s in parts]

    # Convert hour:min in total minutes
    def convert(t):
        # must end with am/pm
        if not (t.endswith("am") or t.endswith("pm")):
            return None

        time_part = t[:-2]
        if ":" not in time_part:
            return None

        hh_mm = time_part.split(":")
        if len(hh_mm) != 2:
            return None

        # Validate numbers
        if not (hh_mm[0].isdigit() and hh_mm[1].isdigit()):
            return None

        hh = int(hh_mm[0])
        mm = int(hh_mm[1])

        # hour must be 1–12
        if hh < 1 or hh > 12:
            return None
        # minute must be 0–59
        if mm < 0 or mm > 59:
            return None

        ampm = t[-2:]
        if hh == 12:
            hh = 0

        minutes = hh * 60 + mm
        if ampm == "pm":
            minutes += 12 * 60

        return minutes

    s = convert(start)
    e = convert(end)

    # invalid time format
    if s is None or e is None:
        return False

    # end must be after start
    if e <= s:
        return False

    # Valid ranges in minutes
    ranges = {
        "morning": (6 * 60, 14 * 60),"evening": (17 * 60, 22 * 60)}
                    # 6 AM to 2 PM             # 5 PM to 10 PM
    

    if slot_type not in ranges:
        return False

    low, high = ranges[slot_type]

    # range
    return low <= s < high and low < e <= high


#h
@app.route('/')
def index():
    return render_template('index.html')

#ab
@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        p_psw = request.form.get('password')
        print("Email entered:", email)
        print("Password entered:", p_psw)

        ext_user = User.query.filter_by(email=email, password=p_psw).first()

        if ext_user:

            
            if ext_user.status == "blacklisted":
                flash("Your account has been blacklisted. Contact ds@gmail.com", "danger")
                return redirect(url_for('login'))

            
            session['user_id'] = ext_user.id
            session['role'] = ext_user.role
            session['f_name'] = ext_user.name

            if ext_user.role == "patient":
                return redirect(url_for('patient_dash'))
            elif ext_user.role == "admin":
                return redirect(url_for('admin_dash'))
            elif ext_user.role == "doctor":
                return redirect(url_for('doctor_dash'))

        else:
            print("Login failed Invalid id or pass")
            flash("Invalid email or password. try again.", "danger")
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/patient_dash')
def patient_dash():
    if 'role' not in session or session['role'] != 'patient':
        flash("Unauthorized access! Please log in as a patient.", "danger")
        return redirect(url_for('login'))
    
    today = datetime.now().date()

    # autocancel old pending appointments
    expired = Appointment.query.filter(Appointment.date < today,
        Appointment.status == "Pending"
    ).all()

    for appt in expired:
        appt.status = "Cancelled"
    db.session.commit()

    pa_id = session['user_id']
    pa_name = session['f_name']

    # all departments
    departments = Department.query.all()

    # Upcoming or pending appointments
    appointments = Appointment.query.filter(Appointment.patient_id == pa_id,
        Appointment.status == "Pending",Appointment.date >= today
    ).order_by(Appointment.date.asc()).all()

    # Cancelled appointments
    cancelled = Appointment.query.filter(Appointment.patient_id == pa_id,
        Appointment.status == "Cancelled"
    ).order_by(Appointment.date.desc()).all()

    # Completed appointments
    completed = Appointment.query.filter(
        Appointment.patient_id == pa_id,Appointment.status == "Completed"
    ).order_by(Appointment.date.desc()).all()

    return render_template(
        'patient_dash.html',
        patient_name=pa_name,
        departments=departments,
        appointments=appointments,
        cancelled=cancelled,
        completed=completed
    )


@app.route('/department/<int:id>', methods=['GET', 'POST'])
def department_details(id):
    department = Department.query.get_or_404(id)
    doct_query = User.query.filter_by(department_id=id, role='doctor')

    search_query = ""
    if request.method == "POST":
        search_query = request.form.get("search", "").strip()
        if search_query:
            doct_query = doct_query.filter(
                User.name.ilike(f"%{search_query}%")
            )

    doct = doct_query.all()

    return render_template(
        'department_details.html',
        department=department,
        doctors=doct,
        search_query=search_query
    )

@app.route('/doctor_availability/<int:doctor_id>')
def doctor_availability(doctor_id):
    if 'role' not in session or session['role'] != 'patient':
        flash("Please log in as a patient to view this page.", "danger")
        return redirect(url_for('login'))

    doctor = User.query.get_or_404(doctor_id)

    if doctor.status == "blacklisted":
        flash("This doctor is currently unavailable.", "danger")
        return redirect(url_for('patient_dash'))

    # Fetch ALL availability rows (multiple per date allowed)
    availabilities = Availability.query.filter_by(
        doctor_id=doctor_id
    ).order_by(Availability.date.asc()).all()

    for a in availabilities:
        # Morning Slot
        a.morning_booked = False
        if a.morning_time:
            a.morning_booked = Appointment.query.filter_by(
                doctor_id=doctor_id,
                date=a.date,
                time=a.morning_time
            ).filter(Appointment.status != "Cancelled").first() is not None

        # Evening Slot 
        a.evening_booked = False
        if a.evening_time:
            a.evening_booked = Appointment.query.filter_by(
                doctor_id=doctor_id,
                date=a.date,
                time=a.evening_time
            ).filter(Appointment.status != "Cancelled").first() is not None

    return render_template(
        'doctor_availability.html',
        doctor=doctor,
        availabilities=availabilities
    )
@app.route('/delete_availability/<int:id>')
def delete_availability(id):
    if 'role' not in session or session['role'] != 'doctor':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('login'))

    avai = Availability.query.get_or_404(id)

    # CHECK MORNING SLOT 
    if avai.morning_time:
        morning_appt = Appointment.query.filter_by(
            doctor_id=avai.doctor_id,
            date=avai.date,
            time=avai.morning_time
        ).filter(Appointment.status != "Cancelled").first()

        if morning_appt:
            if morning_appt.status == "Completed":
                flash("This morning slot has a completed appointment. Cannot delete.", "danger")
            else:
                flash("A patient has booked the morning slot. Cancel the appointment first.", "warning")
            return redirect(url_for('provide_availability'))

    # CHECK EVENING SLOT 
    if avai.evening_time:
        evening_appt = Appointment.query.filter_by(
            doctor_id=avai.doctor_id,
            date=avai.date,
            time=avai.evening_time
        ).filter(Appointment.status != "Cancelled").first()

        if evening_appt:
            if evening_appt.status == "Completed":
                flash("This evening slot has a completed appointment. you Cannot delete.", "danger")
            else:
                flash("A patient has booked the evening slot. Cancel the appointment first.", "warning")
            return redirect(url_for('provide_availability'))

    # NO BOOKINGS then SAFE TO DELETE 
    db.session.delete(avai)
    db.session.commit()

    flash("Availability deleted successfully!", "success")
    return redirect(url_for('provide_availability'))


# Book Appointment
@app.route('/book_appointment/<int:availability_id>/<slot>')
def book_appointment(availability_id, slot):
    if 'role' not in session or session['role'] != 'patient':
        flash("Please log in as a patient to book appointments.", "danger")
        return redirect(url_for('login'))

    patient_id = session['user_id']

    # Get availability row
    availability = Availability.query.get_or_404(availability_id)

    doctor_id = availability.doctor_id
    date_obj = availability.date

    # Determine slot
    time_slot = availability.morning_time if slot == "morning" else availability.evening_time

    # Check if already booked by ANY patient
    existing = Appointment.query.filter_by(
        doctor_id=doctor_id,
        date=date_obj,
        time=time_slot
    ).filter(Appointment.status != "Cancelled").first()

    if existing:
        flash("This slot is already booked!", "warning")
        return redirect(url_for('doctor_availability', doctor_id=doctor_id))

    # Create appointment
    new_appointment = Appointment(
        doctor_id=doctor_id,
        patient_id=patient_id,
        date=date_obj,
        time=time_slot,
        status="Pending"
    )

    db.session.add(new_appointment)
    db.session.commit()

    flash("Appointment booked successfully!", "success")
    return redirect(url_for('doctor_availability', doctor_id=doctor_id))

#if patient cancel their appointment his appointment will deleted by db
@app.route('/cancel_appointment/<int:id>')
def cancel_appointment(id):
    if 'role' not in session or session['role'] != 'patient':
        flash("Please log in as a patient to cancel appointments.", "danger")
        return redirect(url_for('login'))

    appointment = Appointment.query.get_or_404(id)
    db.session.delete(appointment)
    db.session.commit()

    flash("Appointment cancelled successfully!", "info")
    return redirect(url_for('patient_dash'))

#admin
@app.route('/admin_dash', methods=['GET','post'])
def admin_dash():
    if 'role' not in session or session['role'] != 'admin':
        flash("Unauthorized access! Please log in as an admin.", "danger")
        return redirect(url_for('login'))
    #make 2 seperate search
    search_query = request.form.get('search', '').strip()

    # for doctor search
    if search_query:
        reg_doctor = (
            User.query
            .outerjoin(Department)
            .filter(
                User.role == 'doctor',
                or_(
                    User.name.ilike(f"%{search_query}%"),User.email.ilike(f"%{search_query}%"),
                    User.phone.ilike(f"%{search_query}%"),Department.name.ilike(f"%{search_query}%")
                )
            )
            .all()
        )
        if not reg_doctor:
            reg_doctor = User.query.filter_by(role='doctor').all()
    else:
        reg_doctor = User.query.filter_by(role='doctor').all()

    #search
    if search_query:
        reg_patient = User.query.filter(
            User.role == 'patient',
            or_(
                User.name.ilike(f"%{search_query}%"),User.email.ilike(f"%{search_query}%"),
                User.phone.ilike(f"%{search_query}%")
            )
        ).all()
        if not reg_patient:
            reg_patient = User.query.filter_by(role='patient').all()
    else:
        reg_patient = User.query.filter_by(role='patient').all()

    #upcoming
    active_appointments = (
        Appointment.query
        .filter(Appointment.patient.has(status='active'))
        .filter(Appointment.doctor.has(status='active'))
        .filter(Appointment.status == "Pending")
        .filter(Appointment.status.notin_(["Cancelled"]))
        .order_by(Appointment.date.desc())
        .limit(20)
        .all()
    )

    # Build appointment list WITH date and time
    appointments = []
    for appt in active_appointments:
        appointments.append({
            "id": appt.id,
            "patient_name": appt.patient.name if appt.patient else "Unknown",
            "doctor_name": appt.doctor.name if appt.doctor else "Unknown",
            "department": (
                appt.doctor.department.name
                if appt.doctor and appt.doctor.department
                else "General"
            ),
            "patient_id": appt.patient_id,
            "date": appt.date.strftime("%d-%m-%Y") if appt.date else "N/A",
            "time": appt.time if appt.time else "N/A"
        })

    # Canceled appointment by doctor
    cancelled_by_doctor = (
        Appointment.query
        .filter(Appointment.status == "Cancelled")
        .order_by(Appointment.date.desc())
        .all()
    )

    
    departments = Department.query.order_by(Department.name.asc()).all()

    
    return render_template(
        'admin_dash.html',
        reg_patient=reg_patient,
        reg_doctor=reg_doctor,
        departments=departments,
        appointments=appointments,
        cancelled_by_doctor=cancelled_by_doctor
    )


@app.route('/add_department', methods=['GET', 'POST'])
def add_department():
    
    if 'role' not in session or session['role'] != 'admin':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        location = request.form.get('location')

        # Prevent duplicates
        if Department.query.filter_by(name=name).first():
            flash("Department already exists!", "warning")
            return redirect(url_for('add_department'))

        new_dept = Department(name=name, description=description, location=location)
        db.session.add(new_dept)
        db.session.commit()
        flash("Department added successfully!", "success")
        return redirect(url_for('admin_dash'))

    return render_template('add_department.html')
#delete department
@app.route('/delete_department/<int:dept_id>', methods=['POST'])
def delete_department(dept_id):

    if 'role' not in session or session['role'] != 'admin':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('login'))

    department = Department.query.get_or_404(dept_id)

    db.session.delete(department)
    db.session.commit()

    flash("Department deleted successfully!", "success")
    return redirect(url_for('delete_department_pg'))

@app.route('/delete_department_pg')
def delete_department_pg():

    if 'role' not in session or session['role'] != 'admin':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('login'))

    departs = Department.query.all()
    return render_template("delete_department.html", departments=departs)



@app.route('/add_doctor', methods=['GET', 'POST'])
def add_doctor():
    if 'role' not in session or session['role'] != 'admin':
        flash("Unauthorized access.", "danger")
        return redirect(url_for('login'))

    departments = Department.query.order_by(Department.name.asc()).all()

    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        gender = request.form.get('gender')
        phone = request.form.get('phone')
        department_id = request.form.get('department_id')
        experience = request.form.get('experience')
        bio=request.form.get('bio')


        existing_user = User.query.filter(
    or_(User.email == email, User.phone == phone)
    ).first()
        if existing_user:
            flash("A user with this email or phone already exists.", "warning")
            return redirect(url_for('add_doctor'))

        new_doctor = User(
            name=name,email=email,password=password,
            gender=gender,phone=phone,
            experience=experience,bio=bio,
            department_id=department_id if department_id else None,
            role='doctor'
        )
        db.session.add(new_doctor)
        db.session.commit()
        flash("Doctor added successfully!", "success")
        return redirect(url_for('admin_dash'))

    return render_template('add_doct.html', departments=departments)

@app.route('/edit_patient/<int:id>', methods=['GET', 'POST'])
def edit_patient(id):
    patient = User.query.get_or_404(id)

    if request.method == 'POST':
        patient.name = request.form.get('name')
        patient.email = request.form.get('email')
        patient.phone = request.form.get('phone')
        patient.gender = request.form.get('gender')
        db.session.commit()
        flash("Patient updated successfully!", "success")
        if session.get("role") == "admin":
            return redirect(url_for('admin_dash'))
        else:
            return redirect(url_for('patient_dash'))

    return render_template('edit_patient.html', patient=patient)



@app.route('/delete_patient/<int:id>')
def delete_patient(id):
    patient = User.query.get_or_404(id)
    db.session.delete(patient)
    db.session.commit()
    flash("Patient deleted successfully!", "success")
    return redirect(url_for('admin_dash'))


@app.route('/blacklist_patient/<int:id>')
def blacklist_patient(id):
    patient = User.query.get_or_404(id)
    patient.status = "blacklisted"
    db.session.commit()
    flash("Patient has been blacklisted.", "warning")
    return redirect(url_for('admin_dash'))


@app.route('/unblacklist_patient/<int:id>')
def unblacklist_patient(id):
    patient = User.query.get_or_404(id)
    patient.status = 'active'
    db.session.commit()
    return redirect(url_for('admin_dash'))


@app.route('/edit_doctor/<int:id>', methods=['GET', 'POST'])
def edit_doctor(id):
    doctor = User.query.get_or_404(id)

    if request.method == 'POST':
        doctor.email = request.form.get('email')
        doctor.password = request.form.get('password')   
        doctor.gender = request.form.get('gender')
        doctor.phone = request.form.get('phone')
        doctor.department_id = request.form.get('department_id')
        doctor.experience = request.form.get('experience')
        doctor.bio = request.form.get('bio')
        db.session.commit()
        flash("Doctor updated successfully!", "success")
        return redirect(url_for('admin_dash'))
    departments = Department.query.all()

    return render_template('edit_doctor.html', doctor=doctor,departments=departments)


@app.route('/delete_doctor/<int:id>')
def delete_doctor(id):
    doctor = User.query.get_or_404(id)
    db.session.delete(doctor)
    db.session.commit()
    flash("Doctor deleted successfully!", "success")
    return redirect(url_for('admin_dash'))


@app.route('/blacklist_doctor/<int:id>')
def blacklist_doctor(id):
    doctor = User.query.get_or_404(id)
    doctor.status = "blacklisted" 
    db.session.commit()
    flash("Doctor blacklisted successfully!", "warning")
    return redirect(url_for('admin_dash'))


@app.route('/unblacklist_doctor/<int:id>')
def unblacklist_doctor(id):
    doct = User.query.get_or_404(id)
    doct.status = 'active'
    db.session.commit()
    return redirect(url_for('admin_dash'))

#logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))




#register
@app.route('/registration', methods=['GET', 'POST'])
def registration():
    if request.method == 'POST':
        f_name = request.form.get('username')
        p_psw = request.form.get('password')
        e_mail = request.form.get('email')
        gen_der = request.form.get('gender')
        ph = request.form.get('phone')
        aa = request.form.get('aadhar')
        address = request.form.get('address')
        dob_str = request.form.get('dob')
        dob = datetime.strptime(dob_str, "%Y-%m-%d").date()

        if User.query.filter_by(email=e_mail).first():
            flash("Email already registered! Please use another email.", "danger")
            return render_template('registration.html')

        if User.query.filter_by(phone=ph).first():
            flash("Phone number already registered! Please use another number.", "danger")
            return render_template('registration.html')

        if User.query.filter_by(aadhar=aa).first():
            flash("Aadhar number already registered! Please use another one.", "danger")
            return render_template('registration.html')

        new_user = User(name=f_name,email=e_mail,password=p_psw,gender=gen_der,phone=ph,aadhar=aa,address=address,dob=dob,role='patient')
        db.session.add(new_user)
        db.session.commit()

        return render_template('registration.html', message='Registration successful! You can now login.')

    return render_template('registration.html')


@app.route('/doctor_dash')
def doctor_dash():
    if 'role' not in session or session['role'] != 'doctor':
        flash("Unauthorized access! Please log in as a doctor.", "danger")
        return redirect(url_for('login'))

    doctor_id = session['user_id']
    doctor_name = session['f_name']
    today = datetime.now().date()

    # autocancel old pending appointments
    expired = Appointment.query.filter(
        Appointment.date < today,
        Appointment.status == "Pending"
    ).all()
    for appt in expired:
        appt.status = "Cancelled"
    db.session.commit()

    search_query = request.args.get('search', '').strip()

    # Upcoming appointments (only pending)
    appointments = (
        Appointment.query
        .join(User, Appointment.patient_id == User.id)
        .filter(
            Appointment.doctor_id == doctor_id,User.status == 'active',
            Appointment.status == "Pending",Appointment.date >= today
        )
        .order_by(Appointment.date.asc())
        .all()
    )

    # ALL PATIENTS FOR THIS DOCTOR 
    patient_query = (
        User.query.join(Appointment, Appointment.patient_id == User.id)
        .filter(Appointment.doctor_id == doctor_id)
        .filter(User.status == "active")
    )

    # Search by patient name
    if search_query:
        patient_query = patient_query.filter(User.name.ilike(f"%{search_query}%"))

    patients = patient_query.distinct().all()

    return render_template(
        'doctor_dash.html',
        doctor_name=doctor_name,
        appointments=appointments,
        patients=patients,
        search_query=search_query
    )


@app.route('/update_history/<int:appointment_id>', methods=['GET', 'POST'])
def update_history(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    patient = appointment.patient
    doctor = appointment.doctor

    if request.method == 'POST':
        diagnosis = request.form.get('diagnosis')
        medicine = request.form.get('medicine')
        notes = request.form.get('notes')
        prescription_text = request.form.get('prescription')

        new_prescription = Prescription(
            doctor_id=doctor.id,
            appointment_id=appointment.id,
            medicine=medicine,
            notes=notes,
            dosage=prescription_text
        )
        db.session.add(new_prescription)
        db.session.commit()

        flash("Patient history updated successfully!", "success")
        return redirect(url_for('doctor_dash'))

    return render_template('update_history.html', patient=patient, appointment=appointment)



@app.route('/view_history/<int:patient_id>')
def view_history(patient_id):
    patient = User.query.get_or_404(patient_id)
    prescriptions = Prescription.query.join(Appointment).filter(Appointment.patient_id == patient_id).all()
    return render_template('view_history.html', patient=patient, prescriptions=prescriptions)



#doctor side complete appointment
@app.route('/complete_appointment/<int:id>', methods=['POST'])
def complete_appointment(id):
    appt = Appointment.query.get_or_404(id)
    appt.status = 'Completed'
    db.session.commit()
    print("appointment completed")
    flash("Appointment marked as completed.", "success")
    return redirect(url_for('doctor_dash'))




@app.route('/cancel_appointment_doctor/<int:id>')
def cancel_appointment_doctor(id):
    appt = Appointment.query.get_or_404(id)
    appt.status = "Cancelled"
    db.session.commit()
    print("appointment canceled")
    flash("Appointment cancelled successfully!", "warning")
    return redirect(url_for('doctor_dash'))


@app.route('/provide_availability', methods=['GET', 'POST'])
def provide_availability():
    if 'role' not in session or session['role'] != 'doctor':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('login'))

    doctor_id = session['user_id']
    doctor = User.query.get_or_404(doctor_id)

    today = datetime.now().date()
    next_week = today + timedelta(days=7)

    if request.method == 'POST':

        date_str = request.form.get('date')
        morning_slot = request.form.get('morning_slot') or None
        evening_slot = request.form.get('evening_slot') or None

        date = datetime.strptime(date_str, "%Y-%m-%d").date()

        # Validate slot formats
        if morning_slot and not validate_time_slot(morning_slot, "morning"):
            flash("Invalid morning time format!", "danger")
            return redirect(url_for('provide_availability'))

        if evening_slot and not validate_time_slot(evening_slot, "evening"):
            flash("Invalid evening time format!", "danger")
            return redirect(url_for('provide_availability'))

        #overlap
        existing = Availability.query.filter_by(
            doctor_id=doctor_id,
            date=date
        ).all()

        
        def convert_time(t):
            t = t.lower().strip()
            ampm = t[-2:]
            h, m = map(int, t[:-2].split(":"))
            if h == 12: h = 0
            minutes = h*60 + m
            if ampm == "pm": 
                minutes += 12*60
            return minutes

        def slot_to_minutes(slot):
            s, e = slot.split("-")
            return convert_time(s.strip()), convert_time(e.strip())

        def overlaps(s1, e1, s2, e2):
            return max(s1, s2) < min(e1, e2)

        # New slot times to compare
        new_slots = []

        if morning_slot:
            ms, me = slot_to_minutes(morning_slot)
            new_slots.append(("morning", ms, me))

        if evening_slot:
            es, ee = slot_to_minutes(evening_slot)
            new_slots.append(("evening", es, ee))

        # Compare with existing slots
        for av in existing:

            if av.morning_time:
                s1, e1 = slot_to_minutes(av.morning_time)
                for _, s2, e2 in new_slots:
                    if overlaps(s1, e1, s2, e2):
                        flash("Overlap with existing morning slot!", "danger")
                        return redirect(url_for('provide_availability'))

            if av.evening_time:
                s1, e1 = slot_to_minutes(av.evening_time)
                for _, s2, e2 in new_slots:
                    if overlaps(s1, e1, s2, e2):
                        flash("Overlap with existing evening slot!", "danger")
                        return redirect(url_for('provide_availability'))

        
        new_avail = Availability(
            doctor_id=doctor_id,
            date=date,
            morning_time=morning_slot,
            evening_time=evening_slot
        )
        db.session.add(new_avail)
        db.session.commit()

        flash("Availability added successfully!", "success")
        return redirect(url_for('provide_availability'))

    
    availabilities = Availability.query.filter(
        Availability.doctor_id == doctor_id,
        Availability.date >= today,
        Availability.date <= next_week
    ).order_by(Availability.date.asc()).all()

    # Add booking status
    for a in availabilities:

        # Morning
        if a.morning_time:
            appt = Appointment.query.filter_by(
                doctor_id=doctor_id,
                date=a.date,
                time=a.morning_time
            ).filter(Appointment.status != "Cancelled").first()
            a.morning_book_status = appt.status if appt else None
        else:
            a.morning_book_status = None

        # Evening
        if a.evening_time:
            appt = Appointment.query.filter_by(
                doctor_id=doctor_id,
                date=a.date,
                time=a.evening_time
            ).filter(Appointment.status != "Cancelled").first()
            a.evening_book_status = appt.status if appt else None
        else:
            a.evening_book_status = None

    return render_template(
        'provide_availability.html',
        doctor=doctor,
        availabilities=availabilities,today=today,next_week=next_week)

@app.route('/edit_availability/<int:id>', methods=['GET', 'POST'])
def edit_availability(id):
    if 'role' not in session or session['role'] != 'doctor':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('login'))

    avai = Availability.query.get_or_404(id)

    today = datetime.now().date()
    next_week = today + timedelta(days=7)



    # slot wise booking check 
    morning_appt = None
    if avai.morning_time:
        morning_appt = Appointment.query.filter_by(
            doctor_id=avai.doctor_id,
            date=avai.date,
            time=avai.morning_time
        ).filter(Appointment.status != "Cancelled").first()

    evening_appt = None
    if avai.evening_time:
        evening_appt = Appointment.query.filter_by(
            doctor_id=avai.doctor_id,
            date=avai.date,
            time=avai.evening_time
        ).filter(Appointment.status != "Cancelled").first()

    # GET 
    if request.method == "GET":
        return render_template(
            'edit_availability.html',
            avail=avai,
            morning_appointment_id = morning_appt.id if morning_appt else None,
            evening_appointment_id = evening_appt.id if evening_appt else None
        )

    # POST
    raw_morning = request.form.get("morning_slot")
    raw_evening = request.form.get("evening_slot")

    morning_slot = None if raw_morning in ["", "None", None] else raw_morning
    evening_slot = None if raw_evening in ["", "None", None] else raw_evening

    if morning_appt:
        flash("Morning slot is already booked! Cancel appointment first.", "danger")
        return redirect(url_for('edit_availability', id=id))

    if evening_appt:
        flash("Evening slot is already booked! Cancel appointment first.", "danger")
        return redirect(url_for('edit_availability', id=id))

    # Validate
    if morning_slot and not validate_time_slot(morning_slot, "morning"):
        flash("Invalid morning slot!", "danger")
        return redirect(url_for('edit_availability', id=id))

    if evening_slot and not validate_time_slot(evening_slot, "evening"):
        flash("Invalid evening slot!", "danger")
        return redirect(url_for('edit_availability', id=id))

    avai.morning_time = morning_slot
    avai.evening_time = evening_slot
    db.session.commit()

    flash("Availability updated!", "success")
    return redirect(url_for('provide_availability'))


@app.route('/doctor_details/<int:doctor_id>')
def doctor_details(doctor_id):
    doctor = User.query.get_or_404(doctor_id)
    return render_template('doctor_details.html', doctor=doctor)



if __name__ == '__main__': 
    with app.app_context():
        db.create_all()
        admin = User.query.filter_by(email="ds@gmail.com").first()

        # If admin exists then delete it
        if admin:
            db.session.delete(admin)
            db.session.commit()
            print("Old ad deleted.")

        # Create new admin
        new_admin = User(
            name="admin",
            email="ds@gmail.com",
            password="admin",
            role="admin"
        )
        db.session.add(new_admin)
        db.session.commit()
        print("New admin created.")

    app.run(debug=True)
