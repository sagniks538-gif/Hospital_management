# Hospital_management project
👤 Student Details
Name:Sagnik Sen


# Hospital Management System (Flask + SQLite)

A full-featured, role-based Hospital Management System (HMS) built using Flask, SQLAlchemy, SQLite, Jinja2, and Bootstrap.
This system provides independent dashboards and features for Admin, Doctor, and Patient roles.

# Key Features
Admin Panel


Add / Edit / Delete Doctors

Add / Edit / Delete Patients

Add / Delete Departments

Search doctors & patients

View Pending Appointments

View Cancelled Appointments

Blacklist / Unblacklist any user

Delete any account using email

Auto-create admin during DB initialization


Doctor Panel


View upcoming appointments

View all assigned patients

Mark appointments as Completed

Cancel appointments

Provide availability for next 7 days

Prevent overlapping slots

Edit or delete availability (only if unbooked)

Add diagnosis, prescription & medical notes

View entire patient treatment history


Patient Panel


Register & Login

View Departments

View Doctors under each department

Search doctors

Book morning / evening appointments

Cancel appointments

View Completed, Cancelled & Pending appointments

View Prescriptions and history

# Technology Stack

Backend: Flask, SQLAlchemy ORM, Python
Frontend: HTML5, CSS3, Bootstrap, Jinja2
Database: SQLite
Authentication: Custom session-based login
Utilities: Python datetime, cascading deletes, time-slot validation

# Database Schema
(Department Table)

id  
name  
description  
location  
created_at 

// Relations:
One Department → Many Users (Doctors)



(User Table)

id  
name  
email  
password  
role (admin/doctor/patient)  
phone  
aadhar  
address  
dob  
gender  
status (active/blacklisted)  
experience  
bio  
created_at  
department_id (FK → department.id)

//Relations:

One Doctor → Many Appointments

One Patient → Many Appointments

One Doctor → Many Prescriptions

One Doctor → Many Availabilities



(Appointment Table)
id  
date  
time  
status (Pending/Completed/Cancelled)  
created_at  
doctor_id (FK → user.id)  
patient_id (FK → user.id)


//Relations:
One Appointment → One Prescription

(Availability Table)
id  
doctor_id (FK → user.id)  
date  
morning_time  
evening_time

//Relations:

One Doctor → Many Availability entries

(Prescription Table)
id  
issue_date  
validity_days  
created_at  
medicine  
dosage  
notes  
appointment_id (FK → appointment.id)  
doctor_id (FK → user.id)


📁 Project Structure
HOSPITAL_MAN/
│
├── __pycache__/
│   ├── app.cpython-314.pyc
│   ├── extension.cpython-314.pyc
│   └── models.cpython-314.pyc
│
├── Hospital_management/        ← (If empty, can be removed)
│
├── README.md
│
├── instance/
│   └── hospital.db              ← SQLite Database (auto-created)
│
├── templates/                   ← All HTML Templates
│   ├── about.html
│   ├── add_department.html
│   ├── add_doct.html
│   ├── admin_dash.html
│   ├── base.html
│   ├── delete_department.html
│   ├── department_details.html
│   ├── doctor_availability.html
│   ├── doctor_dash.html
│   ├── doctor_details.html
│   ├── edit_availability.html
│   ├── edit_doctor.html
│   ├── edit_patient.html
│   ├── index.html
│   ├── login.html
│   ├── patient_dash.html
│   ├── provide_availability.html
│   ├── registration.html
│   ├── update_history.html
│   └── view_history.html
│
├── venv/                        ← Virtual Environment
│   ├── Include/
│   ├── Lib/
│   ├── Scripts/
│   ├── .gitignore
│   └── pyvenv.cfg
│
├── app.py                       ← Main Flask Application
├── extension.py                 ← Database/Flask extension setup
├── models.py                    ← SQLAlchemy Models
└── requirements.txt             ← Python Dependencies
-Hospital management Documentation
### Default Login Credentials

| Role  | Username | Password | Email             |
|-------|----------|----------|-------------------|
| Admin | `admin`  | `admin`  | `ds@gmail.com`   |

→ Admin account is automatically created on first run.

Create virtual environment (recommended)
python -m venv venv

# venv\Scripts\activate         # Windows

# Install dependencies
pip install Flask Flask-SQLAlchemy

# Run the app
python app.py
