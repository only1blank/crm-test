"""
Analytics routes for statistics and reports
"""
from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from app.extensions import db
from app.models import Lead, Dealer, DealerLead

analytics_bp = Blueprint('analytics', __name__)


@analytics_bp.route('/')
@login_required
def index():
    """Main analytics dashboard"""
    if current_user.role != 'admin':
        flash('Доступ только для администраторов', 'error')
        return redirect(url_for('main.index'))
    
    # Date range
    days = request.args.get('days', 30, type=int)
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Total stats
    total_leads = Lead.query.count()
    new_leads = Lead.query.filter(Lead.created_at >= start_date).count()
    in_work = Lead.query.filter(Lead.status == 'В работе').count()
    
    visits = Lead.query.filter(
        Lead.visit_at >= start_date,
        Lead.visit_at <= datetime.utcnow()
    ).count()
    
    deals = Lead.query.filter(
        Lead.status.like('Сделка%'),
        Lead.updated_at >= start_date
    ).count()
    
    # Deal types
    deal_commission = Lead.query.filter(Lead.status == 'Сделка — комиссия').count()
    deal_ti = Lead.query.filter(Lead.status == 'Сделка — ТИ').count()
    deal_buyout = Lead.query.filter(Lead.status == 'Сделка — выкуп').count()
    deal_credit = Lead.query.filter(Lead.status == 'Автокредит').count()
    
    no_answer = Lead.query.filter(Lead.status == 'Недозвон').count()
    declined = Lead.query.filter(Lead.status == 'Предварительный отказ').count()
    
    # Conversions
    lead_to_visit = (visits / total_leads * 100) if total_leads > 0 else 0
    visit_to_deal = (deals / visits * 100) if visits > 0 else 0
    lead_to_deal = (deals / total_leads * 100) if total_leads > 0 else 0
    
    # Dealer stats
    dealers_stats = []
    dealers = Dealer.query.filter_by(is_active=True).all()
    
    for dealer in dealers:
        sent = DealerLead.query.filter_by(dealer_id=dealer.id).count()
        taken = DealerLead.query.filter_by(dealer_id=dealer.id, status='В работе').count()
        came = DealerLead.query.filter_by(dealer_id=dealer.id, visit_result='Приехал').count()
        not_came = DealerLead.query.filter_by(dealer_id=dealer.id, visit_result='Не приехал').count()
        dealer_deals = DealerLead.query.filter_by(dealer_id=dealer.id)\
            .filter(DealerLead.final_result.like('%Сделка%')).count()
        
        dealers_stats.append({
            'dealer': dealer,
            'sent': sent,
            'taken': taken,
            'came': came,
            'not_came': not_came,
            'deals': dealer_deals,
            'conversion_sent_to_came': (came / sent * 100) if sent > 0 else 0,
            'conversion_came_to_deal': (dealer_deals / came * 100) if came > 0 else 0
        })
    
    return render_template('analytics/index.html',
                         total_leads=total_leads,
                         new_leads=new_leads,
                         in_work=in_work,
                         visits=visits,
                         deals=deals,
                         deal_commission=deal_commission,
                         deal_ti=deal_ti,
                         deal_buyout=deal_buyout,
                         deal_credit=deal_credit,
                         no_answer=no_answer,
                         declined=declined,
                         lead_to_visit=lead_to_visit,
                         visit_to_deal=visit_to_deal,
                         lead_to_deal=lead_to_deal,
                         dealers_stats=dealers_stats,
                         days=days)
