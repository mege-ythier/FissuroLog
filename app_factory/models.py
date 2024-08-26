"""Database models."""

from flask_login import UserMixin
from sqlalchemy.dialects.mysql import LONGBLOB
from werkzeug.security import check_password_hash, generate_password_hash

from app_factory import db


class User(UserMixin, db.Model):
    """User account model."""

    __tablename__ = "flasklogin_users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(40), unique=True, nullable=False)
    role = db.Column(db.String(10), nullable=False)
    password = db.Column(db.String(200), primary_key=False, unique=False, nullable=False)
    created_on = db.Column(db.DateTime, index=False, unique=False, nullable=True)
    last_login = db.Column(db.DateTime, index=False, unique=False, nullable=True)

    def set_password(self, password):
        """Create hashed password."""
        self.password = generate_password_hash(password)

    def set_role(self, role):
        """Create hashed password."""
        self.role = role

    def check_password(self, password):
        """Check hashed password."""
        return check_password_hash(self.password, password)

    def __repr__(self):
        return f"<User id={self.id}, email={self.email},role={self.role}, >"


class SensorInfo(db.Model):
    """sensor model."""

    __tablename__ = "sensors_info_tb"

    Id = db.Column(db.Integer, primary_key=True)
    Num = db.Column(db.String(10))
    Modele = db.Column(db.String(10))
    Reseau = db.Column(db.String(5))
    Ligne = db.Column(db.String(4))
    Zone = db.Column(db.String(20))
    Lieu = db.Column(db.String(20))
    pk = db.Column(db.Float)
    Latitude = db.Column(db.Float)
    Longitude = db.Column(db.Float)
    Date_pose = db.Column(db.DateTime, nullable=False)
    Date_depose = db.Column(db.DateTime)
    Ouverture_pose = db.Column(db.Float)
    Divers = db.Column(db.String(1000))
    Date_collecte = db.Column(db.DateTime)

    # Relation avec SensorImage
    Images = db.relationship('SensorImage', backref='sensor', lazy=True)


class SensorImage(db.Model):
    __tablename__ = "sensors_image_tb"
    id = db.Column(db.Integer, primary_key=True)
    sensor_id = db.Column(db.Integer, db.ForeignKey('sensors_info_tb.Id'), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    data = db.Column(LONGBLOB, nullable=False) if db.engine.name == 'mysql' else db.Column(db.LargeBinary, nullable=False)
    card_id = db.Column(db.Integer)
