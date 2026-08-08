"""
Main routes for the CRM application
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime, timedelta
from app.extensions import db
from app.models import User, Lead, Communication, StatusHistory, Appointment, Dealer, DealerLead

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
@login_required
def index():
    """Main dashboard"""
    today = datetime.utcnow().date()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())
    
    # Dashboard stats
    total_leads = Lead.query.count()
    new_leads_today = Lead.query.filter(Lead.created_at >= today_start).count()
    
    calls_today = Lead.query.filter(
        Lead.next_call_at >= today_start,
        Lead.next_call_at <= today_end
    ).count()
    
    overdue_calls = Lead.query.filter(
        Lead.next_call_at < today_start,
        Lead.status.notin_(['Сделка — комиссия', 'Сделка — ТИ', 'Сделка — выкуп', 
                           'Автокредит', 'Перекуп', 'Площадка'])
    ).count()
    
    visits_today = Lead.query.filter(
        Lead.visit_at >= today_start,
        Lead.visit_at <= today_end
    ).count()
    
    deals = Lead.query.filter(
        Lead.status.like('Сделка%')
    ).count()
    
    # Get leads with filters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 25, type=int)
    
    query = Lead.query
    
    # Filter by user role
    if not current_user.can_view_all_leads():
        query = query.filter(Lead.manager_id == current_user.id)
    
    # Search
    search = request.args.get('search', '')
    if search:
        search_filter = (
            Lead.client_name.ilike(f'%{search}%') |
            Lead.client_phone.ilike(f'%{search}%') |
            Lead.bot_phone.ilike(f'%{search}%') |
            Lead.car_brand.ilike(f'%{search}%') |
            Lead.car_model.ilike(f'%{search}%') |
            Lead.city.ilike(f'%{search}%') |
            Lead.crm_id.ilike(f'%{search}%') |
            Lead.source_url.ilike(f'%{search}%')
        )
        try:
            year_search = int(search)
            search_filter |= (Lead.car_year == year_search)
        except ValueError:
            pass
        query = query.filter(search_filter)
    
    # Filters
    city = request.args.get('city', '')
    if city:
        query = query.filter(Lead.city == city)
    
    status = request.args.get('status', '')
    if status:
        query = query.filter(Lead.status == status)
    
    # Quick filters
    quick_filter = request.args.get('quick_filter', '')
    if quick_filter == 'today':
        query = query.filter(
            Lead.next_call_at >= today_start,
            Lead.next_call_at <= today_end
        )
    elif quick_filter == 'overdue':
        query = query.filter(
            Lead.next_call_at < today_start,
            Lead.status.notin_(['Сделка — комиссия', 'Сделка — ТИ', 'Сделка — выкуп', 
                               'Автокредит', 'Перекуп', 'Площадка'])
        )
    elif quick_filter == 'visits':
        query = query.filter(
            Lead.visit_at >= today_start,
            Lead.visit_at <= today_end
        )
    elif quick_filter == 'in_work':
        query = query.filter(Lead.status == 'В работе')
    elif quick_filter == 'no_answer':
        query = query.filter(Lead.status == 'Недозвон')
    elif quick_filter == 'declined':
        query = query.filter(Lead.status == 'Предварительный отказ')
    elif quick_filter == 'deals':
        query = query.filter(Lead.status.like('Сделка%'))
    elif quick_filter == 'no_action':
        query = query.filter(
            Lead.next_call_at.is_(None),
            Lead.visit_at.is_(None),
            Lead.status.notin_(['Сделка — комиссия', 'Сделка — ТИ', 'Сделка — выкуп',
                               'Автокредит', 'Перекуп', 'Площадка'])
        )
    
    # Sort
    sort_by = request.args.get('sort', 'created_at')
    sort_order = request.args.get('order', 'desc')
    if sort_order == 'desc':
        query = query.order_by(getattr(Lead, sort_by, Lead.created_at).desc())
    else:
        query = query.order_by(getattr(Lead, sort_by, Lead.created_at).asc())
    
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    leads = pagination.items
    
    # Get unique cities for filter
    cities = db.session.query(Lead.city).filter(Lead.city.isnot(None)).distinct().all()
    cities = [c[0] for c in cities if c[0]]
    
    # Available statuses
    statuses = [
        'В работе', 'Недозвон', 'Предварительный отказ', 'Визит',
        'Сделка — комиссия', 'Сделка — ТИ', 'Сделка — выкуп',
        'Автокредит', 'Перекуп', 'Площадка'
    ]
    
    return render_template('main/index.html',
                         leads=leads,
                         pagination=pagination,
                         total_leads=total_leads,
                         new_leads=new_leads_today,
                         calls_today=calls_today,
                         overdue_calls=overdue_calls,
                         visits_today=visits_today,
                         deals=deals,
                         cities=cities,
                         statuses=statuses,
                         search=search,
                         current_city=city,
                         current_status=status,
                         quick_filter=quick_filter)


@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember', False)
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.index'))
        else:
            flash('Неверное имя пользователя или пароль', 'error')
    
    return render_template('main/login.html')


@main_bp.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    return redirect(url_for('main.login'))


@main_bp.route('/lead/new', methods=['GET', 'POST'])
@login_required
def create_lead():
    """Create new lead"""
    if request.method == 'POST':
        crm_id = Lead.generate_crm_id()
        
        lead = Lead(
            crm_id=crm_id,
            city=request.form.get('city'),
            client_name=request.form.get('client_name'),
            client_phone=request.form.get('client_phone'),
            bot_phone=request.form.get('bot_phone'),
            source_url=request.form.get('source_url'),
            source_name=request.form.get('source_name'),
            car_brand=request.form.get('car_brand'),
            car_model=request.form.get('car_model'),
            car_year=int(request.form.get('car_year')) if request.form.get('car_year') else None,
            status=request.form.get('status', 'В работе'),
            manager_id=current_user.id,
            communication_result=request.form.get('communication_result')
        )
        
        # Set first contact date
        if request.form.get('first_contact_at'):
            lead.first_contact_at = datetime.strptime(request.form.get('first_contact_at'), '%Y-%m-%dT%H:%M')
        else:
            lead.first_contact_at = datetime.utcnow()
        
        # Set next call
        if request.form.get('next_call_at'):
            lead.next_call_at = datetime.strptime(request.form.get('next_call_at'), '%Y-%m-%dT%H:%M')
        
        # Set visit
        if request.form.get('visit_at'):
            lead.visit_at = datetime.strptime(request.form.get('visit_at'), '%Y-%m-%dT%H:%M')
        
        db.session.add(lead)
        
        # Add status history
        status_history = StatusHistory(
            lead=lead,
            old_status=None,
            new_status=lead.status,
            user_id=current_user.id,
            comment='Создан новый лид'
        )
        db.session.add(status_history)
        
        db.session.commit()
        flash(f'Лид {crm_id} успешно создан', 'success')
        return redirect(url_for('main.index'))
    
    return render_template('main/lead_form.html', lead=None, action='create')


@main_bp.route('/lead/<int:id>', methods=['GET', 'POST'])
@login_required
def view_lead(id):
    """View lead details"""
    lead = Lead.query.get_or_404(id)
    
    if not current_user.can_edit_lead(lead):
        flash('У вас нет прав для просмотра этого лида', 'error')
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        # Update lead
        lead.client_name = request.form.get('client_name')
        lead.client_phone = request.form.get('client_phone')
        lead.bot_phone = request.form.get('bot_phone')
        lead.city = request.form.get('city')
        lead.source_url = request.form.get('source_url')
        lead.source_name = request.form.get('source_name')
        lead.car_brand = request.form.get('car_brand')
        lead.car_model = request.form.get('car_model')
        lead.car_year = int(request.form.get('car_year')) if request.form.get('car_year') else None
        lead.communication_result = request.form.get('communication_result')
        
        old_status = lead.status
        lead.status = request.form.get('status')
        
        if request.form.get('next_call_at'):
            lead.next_call_at = datetime.strptime(request.form.get('next_call_at'), '%Y-%m-%dT%H:%M')
        
        if request.form.get('visit_at'):
            lead.visit_at = datetime.strptime(request.form.get('visit_at'), '%Y-%m-%dT%H:%M')
        
        # Update last contact
        lead.last_contact_at = datetime.utcnow()
        
        # Status history
        if old_status != lead.status:
            status_history = StatusHistory(
                lead=lead,
                old_status=old_status,
                new_status=lead.status,
                user_id=current_user.id
            )
            db.session.add(status_history)
        
        db.session.commit()
        flash('Лид обновлен', 'success')
        return redirect(url_for('main.view_lead', id=lead.id))
    
    # Get communications
    communications = lead.communications.order_by(Communication.created_at.desc()).all()
    
    # Get status history
    status_history = lead.status_history.order_by(StatusHistory.created_at.desc()).all()
    
    # Get dealer leads
    dealer_leads = lead.dealer_leads.all()
    
    dealers = Dealer.query.filter_by(is_active=True).all()
    
    return render_template('main/lead_detail.html',
                         lead=lead,
                         communications=communications,
                         status_history=status_history,
                         dealer_leads=dealer_leads,
                         dealers=dealers)


@main_bp.route('/lead/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_lead(id):
    """Edit lead"""
    lead = Lead.query.get_or_404(id)
    
    if not current_user.can_edit_lead(lead):
        flash('У вас нет прав для редактирования этого лида', 'error')
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        old_status = lead.status
        
        lead.client_name = request.form.get('client_name')
        lead.client_phone = request.form.get('client_phone')
        lead.bot_phone = request.form.get('bot_phone')
        lead.city = request.form.get('city')
        lead.source_url = request.form.get('source_url')
        lead.source_name = request.form.get('source_name')
        lead.car_brand = request.form.get('car_brand')
        lead.car_model = request.form.get('car_model')
        lead.car_year = int(request.form.get('car_year')) if request.form.get('car_year') else None
        lead.communication_result = request.form.get('communication_result')
        lead.status = request.form.get('status')
        
        if request.form.get('next_call_at'):
            lead.next_call_at = datetime.strptime(request.form.get('next_call_at'), '%Y-%m-%dT%H:%M')
        else:
            lead.next_call_at = None
            
        if request.form.get('visit_at'):
            lead.visit_at = datetime.strptime(request.form.get('visit_at'), '%Y-%m-%dT%H:%M')
        else:
            lead.visit_at = None
        
        lead.last_contact_at = datetime.utcnow()
        
        if old_status != lead.status:
            status_history = StatusHistory(
                lead=lead,
                old_status=old_status,
                new_status=lead.status,
                user_id=current_user.id
            )
            db.session.add(status_history)
        
        db.session.commit()
        flash('Лид обновлен', 'success')
        return redirect(url_for('main.view_lead', id=lead.id))
    
    return render_template('main/lead_form.html', lead=lead, action='edit')


@main_bp.route('/lead/<int:id>/add-communication', methods=['POST'])
@login_required
def add_communication(id):
    """Add communication to lead"""
    lead = Lead.query.get_or_404(id)
    
    if not current_user.can_edit_lead(lead):
        return jsonify({'error': 'Нет прав'}), 403
    
    comm = Communication(
        lead_id=lead.id,
        user_id=current_user.id,
        comm_type=request.form.get('comm_type', 'call'),
        comment=request.form.get('comment'),
        result=request.form.get('result'),
        next_step=request.form.get('next_step')
    )
    
    if request.form.get('next_call_at'):
        comm.next_call_at = datetime.strptime(request.form.get('next_call_at'), '%Y-%m-%dT%H:%M')
        lead.next_call_at = comm.next_call_at
    
    lead.last_contact_at = datetime.utcnow()
    lead.communication_result = request.form.get('result')
    
    db.session.add(comm)
    db.session.commit()
    
    flash('Коммуникация добавлена', 'success')
    return redirect(url_for('main.view_lead', id=lead.id))


@main_bp.route('/lead/<int:id>/send-to-dealer', methods=['POST'])
@login_required
def send_to_dealer(id):
    """Send lead to dealer"""
    lead = Lead.query.get_or_404(id)
    dealer_id = request.form.get('dealer_id')
    
    if not dealer_id:
        flash('Выберите автосалон', 'error')
        return redirect(url_for('main.view_lead', id=lead.id))
    
    dealer = Dealer.query.get_or_404(dealer_id)
    
    dealer_lead = DealerLead(
        lead_id=lead.id,
        dealer_id=dealer.id,
        external_id=f"{lead.crm_id}-{dealer.id}"
    )
    
    db.session.add(dealer_lead)
    
    # Add history
    history = DealerLeadHistory(
        dealer_lead=dealer_lead,
        old_status=None,
        new_status='Новая заявка',
        comment=f'Отправлен в {dealer.name}'
    )
    db.session.add(history)
    
    db.session.commit()
    
    flash(f'Лид отправлен в {dealer.name}', 'success')
    return redirect(url_for('main.view_lead', id=lead.id))


@main_bp.route('/profile')
@login_required
def profile():
    """User profile"""
    return render_template('main/profile.html')
