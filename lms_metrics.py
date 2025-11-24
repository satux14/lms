"""
Metrics collection module for LMS
Uses same database, different tables for metrics storage
"""
import json
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy import Column, Integer, String, Text, DateTime, Numeric, Date, Index, func
from sqlalchemy.ext.declarative import declarative_base

MetricsBase = declarative_base()

class SystemMetrics(MetricsBase):
    """Store aggregated metrics for admin dashboard - separate table in same DB"""
    __tablename__ = 'system_metrics'
    
    id = Column(Integer, primary_key=True)
    metric_name = Column(String(100), nullable=False)  # 'logins', 'payments', 'api_requests'
    metric_value = Column(Numeric(15, 2), nullable=False)
    username = Column(String(80), nullable=True)
    period = Column(String(20), nullable=False)  # 'today', 'week', 'month'
    period_date = Column(Date, nullable=False)
    metadata_json = Column(Text, nullable=True)  # JSON string (renamed from 'metadata' - reserved in SQLAlchemy)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Indexes for faster queries
    __table_args__ = (
        Index('idx_metric_period', 'metric_name', 'period', 'period_date'),
        Index('idx_username_period', 'username', 'period', 'period_date'),
        Index('idx_created_at', 'created_at'),
    )


class MetricsManager:
    """Manages metrics collection using same database, different tables"""
    
    def __init__(self, db_engine, instance_name):
        """
        Initialize metrics manager
        
        Args:
            db_engine: SQLAlchemy engine from main database
            instance_name: Instance name (prod, dev, testing)
        """
        self.engine = db_engine
        self.instance_name = instance_name
        
        # Create metrics tables in the same database
        MetricsBase.metadata.create_all(self.engine)
    
    def record_login(self, username, success=True):
        """Record login metric"""
        status = 'success' if success else 'failed'
        self._record_metric('logins', username, 1, {'status': status})
    
    def record_logout(self, username):
        """Record logout metric"""
        self._record_metric('logouts', username, 1)
    
    def record_payment(self, username, amount, status='pending'):
        """Record payment metric"""
        self._record_metric('payments', username, float(amount), {'status': status})
    
    def record_api_request(self, method, endpoint, username='anonymous', duration=None):
        """Record API request metric"""
        metadata = {'method': method, 'endpoint': endpoint}
        if duration:
            metadata['duration'] = duration
        self._record_metric('api_requests', username, 1, metadata)
    
    def record_admin_action(self, action, username):
        """Record admin action metric"""
        self._record_metric('admin_actions', username, 1, {'action': action})
    
    def record_moderator_action(self, action, username):
        """Record moderator action metric"""
        self._record_metric('moderator_actions', username, 1, {'action': action})
    
    def record_tracker_entry(self, tracker_id, username, amount=0):
        """Record tracker entry metric"""
        self._record_metric('tracker_entries', username, amount, {'tracker_id': tracker_id})
    
    def _record_metric(self, metric_name, username, value, metadata=None):
        """Record a metric to database"""
        from sqlalchemy.orm import sessionmaker
        Session = sessionmaker(bind=self.engine)
        session = Session()
        
        try:
            today = date.today()
            
            # Check if metric exists for today
            metric = session.query(SystemMetrics).filter_by(
                metric_name=metric_name,
                username=username or 'anonymous',
                period='today',
                period_date=today
            ).first()
            
            if metric:
                metric.metric_value += Decimal(str(value))
                if metadata:
                    existing_meta = json.loads(metric.metadata_json) if metric.metadata_json else {}
                    existing_meta.update(metadata)
                    metric.metadata_json = json.dumps(existing_meta)
            else:
                metric = SystemMetrics(
                    metric_name=metric_name,
                    metric_value=Decimal(str(value)),
                    username=username or 'anonymous',
                    period='today',
                    period_date=today,
                    metadata_json=json.dumps(metadata) if metadata else None
                )
                session.add(metric)
            
            session.commit()
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    
    def get_metrics(self, metric_name, period='today', username=None, start_date=None, end_date=None):
        """Get metrics for a period"""
        from sqlalchemy.orm import sessionmaker
        Session = sessionmaker(bind=self.engine)
        session = Session()
        
        try:
            query = session.query(SystemMetrics).filter_by(metric_name=metric_name, period=period)
            
            if username:
                query = query.filter_by(username=username)
            
            if start_date:
                query = query.filter(SystemMetrics.period_date >= start_date)
            if end_date:
                query = query.filter(SystemMetrics.period_date <= end_date)
            
            return query.all()
        finally:
            session.close()
    
    def get_aggregated_metrics(self, metric_name, period='today'):
        """Get aggregated metrics (sum, count) for a period"""
        from sqlalchemy.orm import sessionmaker
        Session = sessionmaker(bind=self.engine)
        session = Session()
        
        try:
            result = session.query(
                func.sum(SystemMetrics.metric_value).label('total'),
                func.count(SystemMetrics.id).label('count')
            ).filter_by(
                metric_name=metric_name,
                period=period
            ).first()
            
            return {
                'total': float(result.total) if result.total else 0.0,
                'count': result.count or 0
            }
        finally:
            session.close()
    
    def get_payment_metrics(self, period='today'):
        """Get payment metrics (pending and verified)"""
        from sqlalchemy.orm import sessionmaker
        Session = sessionmaker(bind=self.engine)
        session = Session()
        
        try:
            # Get pending payments
            pending = session.query(
                func.sum(SystemMetrics.metric_value).label('total'),
                func.count(SystemMetrics.id).label('count')
            ).filter_by(
                metric_name='payments',
                period=period
            ).filter(
                SystemMetrics.metadata_json.like('%pending%')
            ).first()
            
            # Get verified payments
            verified = session.query(
                func.sum(SystemMetrics.metric_value).label('total'),
                func.count(SystemMetrics.id).label('count')
            ).filter_by(
                metric_name='payments',
                period=period
            ).filter(
                SystemMetrics.metadata_json.like('%verified%')
            ).first()
            
            return {
                'pending': {
                    'total': float(pending.total) if pending.total else 0.0,
                    'count': pending.count or 0
                },
                'verified': {
                    'total': float(verified.total) if verified.total else 0.0,
                    'count': verified.count or 0
                }
            }
        finally:
            session.close()
    
    def get_user_activity_summary(self, username, period='today'):
        """Get activity summary for a user"""
        from sqlalchemy.orm import sessionmaker
        Session = sessionmaker(bind=self.engine)
        session = Session()
        
        try:
            metrics = session.query(SystemMetrics).filter_by(
                username=username,
                period=period
            ).all()
            
            summary = {}
            for metric in metrics:
                if metric.metric_name not in summary:
                    summary[metric.metric_name] = {
                        'total': 0.0,
                        'count': 0
                    }
                summary[metric.metric_name]['total'] += float(metric.metric_value)
                summary[metric.metric_name]['count'] += 1
            
            return summary
        finally:
            session.close()


# Global metrics managers per instance
_metrics_managers = {}

def init_metrics(instance_name, db_engine):
    """Initialize metrics for an instance"""
    _metrics_managers[instance_name] = MetricsManager(db_engine, instance_name)
    return _metrics_managers[instance_name]

def get_metrics_manager(instance_name):
    """Get the metrics manager for an instance"""
    if instance_name not in _metrics_managers:
        raise RuntimeError(f"Metrics not initialized for instance '{instance_name}'. Call init_metrics() first.")
    return _metrics_managers[instance_name]

