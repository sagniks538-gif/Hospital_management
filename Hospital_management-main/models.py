from extension import db
from datetime import datetime

class Department(db.Model):
    __tablename__ = 'department'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(200))
    location = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    #(Department(one) to Users(many))
    users = db.relationship(
        "User",
        back_populates="department",
        cascade="all, delete-orphan"
    )



class User(db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    phone = db.Column(db.String(15), unique=True)
    aadhar = db.Column(db.String(12), unique=True)
    address = db.Column(db.String(150))
    dob = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    gender = db.Column(db.String(10))
    status = db.Column(db.String(20), default='active')
    experience = db.Column(db.String(100))
    bio = db.Column(db.Text())

    department_id = db.Column(
        db.Integer,
        db.ForeignKey('department.id', ondelete="CASCADE")
    )

    # Many(users) to One(department)
    department = db.relationship("Department", back_populates="users")

    # One(doctor) to Many(appoinments)
    doctor_appointments = db.relationship(
        "Appointment",
        back_populates="doctor",
        foreign_keys="Appointment.doctor_id",
        cascade="all, delete-orphan"
    )

    # One(patient) to Many(appoinments) 
    patient_appointments = db.relationship(
        "Appointment",
        back_populates="patient",
        foreign_keys="Appointment.patient_id",
        cascade="all, delete-orphan"
    )

    # One(doctor) to Many(prescriptions)
    prescriptions = db.relationship(
        "Prescription",
        back_populates="doctor",
        cascade="all, delete-orphan"
    )

    # One(Doctor) to Many(availabilites)
    availabilities = db.relationship(
        "Availability",
        back_populates="doctor",
        cascade="all, delete-orphan"
    )



class Appointment(db.Model):
    __tablename__ = 'appointment'

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    time = db.Column(db.String(50))
    status = db.Column(db.String(20), default='Pending')

    doctor_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id', ondelete="CASCADE"),
        nullable=False
    )

    patient_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id', ondelete="CASCADE"),
        nullable=False
    )

    # Many(appoinments) to One(doctor)
    doctor = db.relationship(
        "User",
        back_populates="doctor_appointments",
        foreign_keys=[doctor_id]
    )

    # Many(appoinments) to One(patient)
    patient = db.relationship(
        "User",
        back_populates="patient_appointments",
        foreign_keys=[patient_id]
    )

    # One(appoinment) to One(prescription)
    prescription = db.relationship(
        "Prescription",
        back_populates="appointment",
        uselist=False,
        cascade="all, delete-orphan"
    )



class Availability(db.Model):
    __tablename__ = 'availability'

    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id', ondelete="CASCADE"),
        nullable=False
    )
    date = db.Column(db.Date, nullable=False)
    morning_time = db.Column(db.String(50))
    evening_time = db.Column(db.String(50))

    # Many(Availability) to One(doctor)
    doctor = db.relationship("User", back_populates="availabilities")



class Prescription(db.Model):
    __tablename__ = 'prescription'

    id = db.Column(db.Integer, primary_key=True)
    issue_date = db.Column(db.DateTime, default=datetime.utcnow)
    validity_days = db.Column(db.Integer, default=7)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    medicine = db.Column(db.String(200))
    dosage = db.Column(db.String(100))
    notes = db.Column(db.String(300))

    appointment_id = db.Column(
        db.Integer,
        db.ForeignKey('appointment.id', ondelete="CASCADE"),
        nullable=False
    )

    doctor_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id', ondelete="CASCADE"),
        nullable=False
    )

    # Many(prescription) to One(appoinment)
    appointment = db.relationship("Appointment", back_populates="prescription")

    # Many(prescription) to One(doctor)
    doctor = db.relationship("User", back_populates="prescriptions")
