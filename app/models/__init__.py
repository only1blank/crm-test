"""
Database models for the CRM system
"""
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db


class User(UserMixin, db.Model):
    """User model with role-based access"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(128))
    role = db.Column(db.String(20), default='manager')  # admin, manager, dealer
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    leads = db.relationship('Lead', backref='manager', lazy='dynamic', foreign_keys='Lead.manager_id')
    communications = db.relationship('Communication', backref='user', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def can_edit_lead(self, lead):
        """Check if user can edit a lead"""
        if self.role == 'admin':
            return True
        return lead.manager_id == self.id
    
    def can_view_all_leads(self):
        """Check if user can view all leads"""
        return self.role == 'admin'
    
    def __repr__(self):
        return f'<User {self.username}>'


class Lead(db.Model):
    """Lead/Customer model - main entity"""
    __tablename__ = 'leads'
    
    id = db.Column(db.Integer, primary_key=True)
    crm_id = db.Column(db.String(20), unique=True, nullable=False, index=True)  # CRM-000001
    city = db.Column(db.String(64), index=True)
    first_contact_at = db.Column(db.DateTime)
    last_contact_at = db.Column(db.DateTime)
    next_call_at = db.Column(db.DateTime, index=True)
    bot_phone = db.Column(db.String(32), index=True)  # Can be duplicated!
    client_phone = db.Column(db.String(32), index=True)
    client_name = db.Column(db.String(128), index=True)
    source_url = db.Column(db.Text)
    source_name = db.Column(db.String(128))
    car_brand = db.Column(db.String(64), index=True)
    car_model = db.Column(db.String(64), index=True)
    car_year = db.Column(db.Integer)
    communication_result = db.Column(db.Text)
    visit_at = db.Column(db.DateTime)
    status = db.Column(db.String(64), default='В работе', index=True)
    manager_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    communications = db.relationship('Communication', backref='lead', lazy='dynamic', cascade='all, delete-orphan')
    status_history = db.relationship('StatusHistory', backref='lead', lazy='dynamic', cascade='all, delete-orphan')
    appointments = db.relationship('Appointment', backref='lead', lazy='dynamic', cascade='all, delete-orphan')
    dealer_leads = db.relationship('DealerLead', backref='lead', lazy='dynamic', cascade='all, delete-orphan')
    
    @property
    def car_full(self):
        """Full car description"""
        parts = []
        if self.car_brand:
            parts.append(self.car_brand)
        if self.car_model:
            parts.append(self.car_model)
        if self.car_year:
            parts.append(str(self.car_year))
        return ' '.join(parts) if parts else None
    
    @classmethod
    def generate_crm_id(cls):
        """Generate unique CRM ID"""
        last = cls.query.order_by(cls.id.desc()).first()
        if last:
            return f"CRM-{last.id + 1:06d}"
        return "CRM-000001"
    
    def __repr__(self):
        return f'<Lead {self.crm_id} - {self.client_name}>'


class Communication(db.Model):
    """Communication history with leads"""
    __tablename__ = 'communications'
    
    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('leads.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    comm_type = db.Column(db.String(32))  # call, message, visit, etc.
    comment = db.Column(db.Text)
    result = db.Column(db.String(256))
    next_step = db.Column(db.Text)
    next_call_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f'<Communication {self.id} for Lead {self.lead_id}>'


class StatusHistory(db.Model):
    """History of status changes for leads"""
    __tablename__ = 'status_history'
    
    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('leads.id'), nullable=False, index=True)
    old_status = db.Column(db.String(64))
    new_status = db.Column(db.String(64), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f'<StatusHistory {self.lead_id}: {self.old_status} -> {self.new_status}>'


class Dealer(db.Model):
    """Dealership model"""
    __tablename__ = 'dealers'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False, index=True)
    city = db.Column(db.String(64))
    contact_person = db.Column(db.String(128))
    phone = db.Column(db.String(32))
    email = db.Column(db.String(120))
    is_active = db.Column(db.Boolean, default=True)
    integration_type = db.Column(db.String(32), default='internal')  # internal, google_sheets, api
    api_url = db.Column(db.String(256))
    api_key = db.Column(db.String(128))
    connected_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    dealer_leads = db.relationship('DealerLead', backref='dealer', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Dealer {self.name}>'


class DealerLead(db.Model):
    """Lead sent to dealership"""
    __tablename__ = 'dealer_leads'
    
    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('leads.id'), nullable=False, index=True)
    dealer_id = db.Column(db.Integer, db.ForeignKey('dealers.id'), nullable=False, index=True)
    external_id = db.Column(db.String(64), index=True)  # Dealer's lead ID
    status = db.Column(db.String(64), default='Новая заявка', index=True)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    taken_at = db.Column(db.DateTime)  # When dealer started working
    visit_at = db.Column(db.DateTime)  # Scheduled visit
    visit_result = db.Column(db.String(64))  # Приехал/Не приехал
    final_result = db.Column(db.String(64))  # Final outcome
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    history = db.relationship('DealerLeadHistory', backref='dealer_lead', lazy='dynamic', cascade='all, delete-orphan')
    
    @property
    def response_time_minutes(self):
        """Time from sent to taken in minutes"""
        if self.taken_at and self.sent_at:
            delta = self.taken_at - self.sent_at
            return int(delta.total_seconds() / 60)
        return None
    
    def __repr__(self):
        return f'<DealerLead {self.id} -> Dealer {self.dealer_id}>'


class DealerLeadHistory(db.Model):
    """History of dealer lead status changes"""
    __tablename__ = 'dealer_lead_history'
    
    id = db.Column(db.Integer, primary_key=True)
    dealer_lead_id = db.Column(db.Integer, db.ForeignKey('dealer_leads.id'), nullable=False, index=True)
    old_status = db.Column(db.String(64))
    new_status = db.Column(db.String(64), nullable=False)
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f'<DealerLeadHistory {self.dealer_lead_id}: {self.new_status}>'


class Appointment(db.Model):
    """Appointments for calls and visits"""
    __tablename__ = 'appointments'
    
    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('leads.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    app_type = db.Column(db.String(32), nullable=False)  # call, visit
    scheduled_at = db.Column(db.DateTime, nullable=False, index=True)
    completed = db.Column(db.Boolean, default=False)
    result = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Appointment {self.app_type} at {self.scheduled_at}>'
