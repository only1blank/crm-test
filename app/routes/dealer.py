"""
Dealer routes for managing dealerships
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from datetime import datetime
from app.extensions import db
from app.models import Dealer, DealerLead, Lead

dealer_bp = Blueprint('dealer', __name__)


@dealer_bp.route('/')
@login_required
def index():
    """List all dealers"""
    if current_user.role != 'admin':
        flash('Доступ только для администраторов', 'error')
        return redirect(url_for('main.index'))
    
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    pagination = Dealer.query.paginate(page=page, per_page=per_page, error_out=False)
    dealers = pagination.items
    
    return render_template('dealer/index.html', dealers=dealers, pagination=pagination)


@dealer_bp.route('/new', methods=['GET', 'POST'])
@login_required
def create_dealer():
    """Create new dealer"""
    if current_user.role != 'admin':
        flash('Доступ только для администраторов', 'error')
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        dealer = Dealer(
            name=request.form.get('name'),
            city=request.form.get('city'),
            contact_person=request.form.get('contact_person'),
            phone=request.form.get('phone'),
            email=request.form.get('email'),
            integration_type=request.form.get('integration_type', 'internal'),
            api_url=request.form.get('api_url'),
            is_active=True
        )
        
        db.session.add(dealer)
        db.session.commit()
        
        flash(f'Автосалон {dealer.name} добавлен', 'success')
        return redirect(url_for('dealer.index'))
    
    return render_template('dealer/form.html', dealer=None)


@dealer_bp.route('/<int:id>', methods=['GET', 'POST'])
@login_required
def view_dealer(id):
    """View dealer details and leads"""
    dealer = Dealer.query.get_or_404(id)
    
    page = request.args.get('page', 1, type=int)
    pagination = DealerLead.query.filter_by(dealer_id=dealer.id)\
        .order_by(DealerLead.sent_at.desc())\
        .paginate(page=page, per_page=25, error_out=False)
    
    # Stats
    total_sent = DealerLead.query.filter_by(dealer_id=dealer.id).count()
    taken_in_work = DealerLead.query.filter_by(dealer_id=dealer.id, status='В работе').count()
    visits_scheduled = DealerLead.query.filter_by(dealer_id=dealer.id)\
        .filter(DealerLead.status.like('%визит%')).count()
    clients_came = DealerLead.query.filter_by(dealer_id=dealer.id, visit_result='Приехал').count()
    deals = DealerLead.query.filter_by(dealer_id=dealer.id)\
        .filter(DealerLead.final_result.like('%Сделка%')).count()
    
    return render_template('dealer/detail.html', 
                         dealer=dealer, 
                         pagination=pagination,
                         stats={
                             'total_sent': total_sent,
                             'taken_in_work': taken_in_work,
                             'visits_scheduled': visits_scheduled,
                             'clients_came': clients_came,
                             'deals': deals
                         })


@dealer_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_dealer(id):
    """Edit dealer"""
    dealer = Dealer.query.get_or_404(id)
    
    if current_user.role != 'admin':
        flash('Доступ только для администраторов', 'error')
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        dealer.name = request.form.get('name')
        dealer.city = request.form.get('city')
        dealer.contact_person = request.form.get('contact_person')
        dealer.phone = request.form.get('phone')
        dealer.email = request.form.get('email')
        dealer.integration_type = request.form.get('integration_type')
        dealer.api_url = request.form.get('api_url')
        dealer.is_active = request.form.get('is_active') == 'on'
        
        db.session.commit()
        flash('Автосалон обновлен', 'success')
        return redirect(url_for('dealer.view_dealer', id=dealer.id))
    
    return render_template('dealer/form.html', dealer=dealer)


@dealer_bp.route('/sent-leads')
@login_required
def sent_leads():
    """View all sent leads to dealers"""
    page = request.args.get('page', 1, type=int)
    
    query = DealerLead.query
    
    # Filters
    dealer_id = request.args.get('dealer_id', type=int)
    if dealer_id:
        query = query.filter_by(dealer_id=dealer_id)
    
    status = request.args.get('status', '')
    if status:
        query = query.filter_by(status=status)
    
    visit_result = request.args.get('visit_result', '')
    if visit_result:
        query = query.filter_by(visit_result=visit_result)
    
    query = query.order_by(DealerLead.sent_at.desc())
    pagination = query.paginate(page=page, per_page=25, error_out=False)
    
    dealers = Dealer.query.filter_by(is_active=True).all()
    
    return render_template('dealer/sent_leads.html', 
                         pagination=pagination,
                         dealers=dealers,
                         current_dealer=dealer_id,
                         current_status=status,
                         current_visit_result=visit_result)


@dealer_bp.route('/lead/<int:id>/take-in-work', methods=['POST'])
@login_required
def take_in_work(id):
    """Dealer takes lead in work"""
    dealer_lead = DealerLead.query.get_or_404(id)
    
    old_status = dealer_lead.status
    dealer_lead.status = 'В работе'
    dealer_lead.taken_at = datetime.utcnow()
    
    from app.models import DealerLeadHistory
    history = DealerLeadHistory(
        dealer_lead=dealer_lead,
        old_status=old_status,
        new_status='В работе',
        comment='Взято в работу'
    )
    db.session.add(history)
    db.session.commit()
    
    flash('Заявка взята в работу', 'success')
    return redirect(url_for('dealer.sent_leads'))


@dealer_bp.route('/lead/<int:id>/update-status', methods=['POST'])
@login_required
def update_status(id):
    """Update dealer lead status"""
    dealer_lead = DealerLead.query.get_or_404(id)
    
    old_status = dealer_lead.status
    new_status = request.form.get('status')
    
    dealer_lead.status = new_status
    
    if new_status == 'В работе' and not dealer_lead.taken_at:
        dealer_lead.taken_at = datetime.utcnow()
    
    from app.models import DealerLeadHistory
    history = DealerLeadHistory(
        dealer_lead=dealer_lead,
        old_status=old_status,
        new_status=new_status,
        comment=request.form.get('comment')
    )
    db.session.add(history)
    db.session.commit()
    
    flash('Статус обновлен', 'success')
    return redirect(url_for('dealer.sent_leads'))
