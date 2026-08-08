"""
API routes for integrations
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from app.extensions import db
from app.models import Lead, Dealer, DealerLead, DealerLeadHistory

api_bp = Blueprint('api', __name__)


@api_bp.route('/leads', methods=['GET'])
@login_required
def get_leads():
    """Get all leads (API)"""
    if not current_user.can_view_all_leads():
        return jsonify({'error': 'Access denied'}), 403
    
    leads = Lead.query.all()
    return jsonify([{
        'id': lead.id,
        'crm_id': lead.crm_id,
        'client_name': lead.client_name,
        'client_phone': lead.client_phone,
        'bot_phone': lead.bot_phone,
        'city': lead.city,
        'car': lead.car_full,
        'status': lead.status,
        'created_at': lead.created_at.isoformat() if lead.created_at else None
    } for lead in leads])


@api_bp.route('/leads/<int:id>', methods=['GET'])
@login_required
def get_lead(id):
    """Get single lead (API)"""
    lead = Lead.query.get_or_404(id)
    
    if not current_user.can_edit_lead(lead):
        return jsonify({'error': 'Access denied'}), 403
    
    return jsonify({
        'id': lead.id,
        'crm_id': lead.crm_id,
        'client_name': lead.client_name,
        'client_phone': lead.client_phone,
        'bot_phone': lead.bot_phone,
        'city': lead.city,
        'source_url': lead.source_url,
        'car_brand': lead.car_brand,
        'car_model': lead.car_model,
        'car_year': lead.car_year,
        'status': lead.status,
        'communication_result': lead.communication_result,
        'next_call_at': lead.next_call_at.isoformat() if lead.next_call_at else None,
        'visit_at': lead.visit_at.isoformat() if lead.visit_at else None,
        'created_at': lead.created_at.isoformat() if lead.created_at else None
    })


@api_bp.route('/leads', methods=['POST'])
@login_required
def create_lead_api():
    """Create new lead (API)"""
    data = request.get_json()
    
    crm_id = Lead.generate_crm_id()
    
    lead = Lead(
        crm_id=crm_id,
        city=data.get('city'),
        client_name=data.get('client_name'),
        client_phone=data.get('client_phone'),
        bot_phone=data.get('bot_phone'),
        source_url=data.get('source_url'),
        source_name=data.get('source_name'),
        car_brand=data.get('car_brand'),
        car_model=data.get('car_model'),
        car_year=data.get('car_year'),
        status=data.get('status', 'В работе'),
        manager_id=current_user.id,
        communication_result=data.get('communication_result')
    )
    
    if data.get('first_contact_at'):
        lead.first_contact_at = datetime.fromisoformat(data['first_contact_at'])
    else:
        lead.first_contact_at = datetime.utcnow()
    
    if data.get('next_call_at'):
        lead.next_call_at = datetime.fromisoformat(data['next_call_at'])
    
    if data.get('visit_at'):
        lead.visit_at = datetime.fromisoformat(data['visit_at'])
    
    db.session.add(lead)
    db.session.commit()
    
    return jsonify({'id': lead.id, 'crm_id': lead.crm_id}), 201


@api_bp.route('/dealers', methods=['GET'])
@login_required
def get_dealers():
    """Get all dealers (API)"""
    dealers = Dealer.query.filter_by(is_active=True).all()
    return jsonify([{
        'id': dealer.id,
        'name': dealer.name,
        'city': dealer.city,
        'contact_person': dealer.contact_person,
        'phone': dealer.phone,
        'email': dealer.email
    } for dealer in dealers])


@api_bp.route('/dealers/<int:dealer_id>/leads', methods=['POST'])
@login_required
def send_to_dealer_api(dealer_id):
    """Send lead to dealer (API)"""
    data = request.get_json()
    lead_id = data.get('lead_id')
    
    lead = Lead.query.get_or_404(lead_id)
    dealer = Dealer.query.get_or_404(dealer_id)
    
    dealer_lead = DealerLead(
        lead_id=lead.id,
        dealer_id=dealer.id,
        external_id=f"{lead.crm_id}-{dealer.id}"
    )
    
    db.session.add(dealer_lead)
    
    history = DealerLeadHistory(
        dealer_lead=dealer_lead,
        old_status=None,
        new_status='Новая заявка',
        comment=f'Отправлен через API'
    )
    db.session.add(history)
    
    db.session.commit()
    
    return jsonify({
        'id': dealer_lead.id,
        'external_id': dealer_lead.external_id,
        'status': dealer_lead.status
    }), 201


@api_bp.route('/dealer-leads/<int:id>/status', methods=['POST'])
def update_dealer_lead_status(id):
    """Update dealer lead status (API - for dealers)"""
    dealer_lead = DealerLead.query.get_or_404(id)
    data = request.get_json()
    
    old_status = dealer_lead.status
    dealer_lead.status = data.get('status')
    
    if data.get('status') == 'В работе' and not dealer_lead.taken_at:
        dealer_lead.taken_at = datetime.utcnow()
    
    history = DealerLeadHistory(
        dealer_lead=dealer_lead,
        old_status=old_status,
        new_status=dealer_lead.status,
        comment=data.get('comment')
    )
    db.session.add(history)
    db.session.commit()
    
    return jsonify({'status': 'ok'})


@api_bp.route('/dealer-leads/<int:id>/visit', methods=['POST'])
def update_dealer_lead_visit(id):
    """Update dealer lead visit (API - for dealers)"""
    dealer_lead = DealerLead.query.get_or_404(id)
    data = request.get_json()
    
    if data.get('visit_at'):
        dealer_lead.visit_at = datetime.fromisoformat(data['visit_at'])
    
    dealer_lead.status = 'Назначен визит'
    
    history = DealerLeadHistory(
        dealer_lead=dealer_lead,
        old_status=dealer_lead.status,
        new_status='Назначен визит',
        comment=data.get('comment')
    )
    db.session.add(history)
    db.session.commit()
    
    return jsonify({'status': 'ok'})


@api_bp.route('/dealer-leads/<int:id>/result', methods=['POST'])
def update_dealer_lead_result(id):
    """Update dealer lead result (API - for dealers)"""
    dealer_lead = DealerLead.query.get_or_404(id)
    data = request.get_json()
    
    dealer_lead.visit_result = data.get('visit_result')
    dealer_lead.final_result = data.get('final_result')
    dealer_lead.comment = data.get('comment')
    
    if data.get('visit_result') == 'Приехал':
        # Update main lead
        lead = Lead.query.get(dealer_lead.lead_id)
        if lead:
            lead.visit_at = dealer_lead.visit_at
            lead.status = 'Визит'
    
    history = DealerLeadHistory(
        dealer_lead=dealer_lead,
        old_status=dealer_lead.status,
        new_status=dealer_lead.status,
        comment=f"Результат: {data.get('visit_result') or data.get('final_result')}"
    )
    db.session.add(history)
    db.session.commit()
    
    return jsonify({'status': 'ok'})
