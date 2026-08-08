"""
Configuration settings for the CRM application
"""
import os
from datetime import timedelta


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'crm-auto-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///crm.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session settings
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    
    # Pagination
    LEADS_PER_PAGE = 25
    DEALERS_PER_PAGE = 10
    
    # File upload
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload
    
    # Dealer integration
    DEALER_API_TIMEOUT = 30
    
    # Reminder settings (minutes before appointment)
    REMINDER_MINUTES_BEFORE = 30
