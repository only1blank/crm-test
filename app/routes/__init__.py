"""
Routes package
"""
from .main import main_bp
from .api import api_bp
from .dealer import dealer_bp
from .analytics import analytics_bp

__all__ = ['main_bp', 'api_bp', 'dealer_bp', 'analytics_bp']
