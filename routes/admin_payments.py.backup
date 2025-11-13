"""
Admin Payments Management Routes
Handles payment tracking, refunds, and financial analytics
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
import uuid
import logging
from config.aws_rds_database import rds_db
from config.auth_config import AuthConfig
from middleware.validation import require_admin_auth, add_security_headers, validate_json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

admin_payments_bp = Blueprint('admin_payments', __name__)

@admin_payments_bp.route('', methods=['GET'])
@add_security_headers
@require_admin_auth
def get_payments():
    """
    Get paginated list of payments with filtering
    GET /api/admin/payments%spage=1&per_page=20&status=&method=&search=
    """
    try:
        # Get query parameters
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 20)), 100)
        status_filter = request.args.get('status', '').strip()
        method_filter = request.args.get('method', '').strip()
        search_query = request.args.get('search', '').strip()
        
        # Build base query
        base_query = """
        SELECT p.*, u.email as user_email, u.name as user_name
        FROM admin_payments p
        LEFT JOIN users u ON p.user_id = u.id
        WHERE 1=1
        """
        
        count_query = """
        SELECT COUNT(*) as total
        FROM admin_payments p
        LEFT JOIN users u ON p.user_id = u.id
        WHERE 1=1
        """
        
        params = []
        
        # Add filters
        if status_filter:
            base_query += " AND p.status = %s"
            count_query += " AND p.status = %s"
            params.append(status_filter)
            
        if method_filter:
            base_query += " AND p.payment_method = %s"
            count_query += " AND p.payment_method = %s"
            params.append(method_filter)
            
        if search_query:
            base_query += " AND (p.transaction_id ILIKE %s OR p.description ILIKE %s OR u.email ILIKE %s)"
            count_query += " AND (p.transaction_id ILIKE %s OR p.description ILIKE %s OR u.email ILIKE %s)"
            search_param = f"%{search_query}%"
            params.extend([search_param, search_param, search_param])
        
        # Get total count
        total_result = rds_db.execute_query(count_query, params)
        total = total_result[0]['total'] if total_result else 0
        
        # Calculate pagination
        pages = (total + per_page - 1) // per_page
        offset = (page - 1) * per_page
        
        # Add ordering and pagination
        base_query += " ORDER BY p.created_at DESC LIMIT %s OFFSET %s"
        params.extend([per_page, offset])
        
        # Execute query
        payments = rds_db.execute_query(base_query, params)
        
        # Get payment statistics
        stats_query = """
        SELECT 
            COUNT(*) as total_payments,
            COUNT(CASE WHEN status = 'completed' THEN 1 END) as successful_payments,
            COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_payments,
            COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_payments,
            COUNT(CASE WHEN status = 'refunded' THEN 1 END) as refunded_payments,
            COALESCE(SUM(CASE WHEN status = 'completed' THEN amount ELSE 0 END), 0) as total_revenue
        FROM admin_payments
        """
        
        stats_result = rds_db.execute_query(stats_query)
        stats = stats_result[0] if stats_result else {}
        
        # Format payments
        formatted_payments = []
        for payment in payments:
            formatted_payments.append({
                'id': payment['id'],
                'user_id': payment['user_id'],
                'user_email': payment.get('user_email'),
                'user_name': payment.get('user_name'),
                'amount': float(payment['amount']),
                'currency': payment['currency'],
                'status': payment['status'],
                'payment_method': payment['payment_method'],
                'transaction_id': payment['transaction_id'],
                'stripe_payment_intent_id': payment.get('stripe_payment_intent_id'),
                'description': payment['description'],
                'metadata': payment.get('metadata'),
                'created_at': payment['created_at'].isoformat() if payment['created_at'] else None,
                'updated_at': payment['updated_at'].isoformat() if payment['updated_at'] else None
            })
        
        return jsonify({
            'success': True,
            'message': 'Payments retrieved successfully',
            'data': {
                'items': formatted_payments,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total,
                    'pages': pages,
                    'has_next': page < pages,
                    'has_prev': page > 1
                },
                'statistics': {
                    'total_payments': stats.get('total_payments', 0),
                    'successful_payments': stats.get('successful_payments', 0),
                    'pending_payments': stats.get('pending_payments', 0),
                    'failed_payments': stats.get('failed_payments', 0),
                    'refunded_payments': stats.get('refunded_payments', 0),
                    'total_revenue': float(stats.get('total_revenue', 0))
                }
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Get payments error: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to retrieve payments',
            'error': str(e)
        }), 500

@admin_payments_bp.route('/stats', methods=['GET'])
@add_security_headers
@require_admin_auth
def get_payment_stats():
    """
    Get payment statistics and analytics
    GET /api/admin/payments/stats
    """
    try:
        # Overview statistics
        overview_query = """
        SELECT 
            COUNT(*) as total_payments,
            COUNT(CASE WHEN status = 'completed' THEN 1 END) as successful_payments,
            COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_payments,
            COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_payments,
            COUNT(CASE WHEN status = 'refunded' THEN 1 END) as refunded_payments,
            COALESCE(SUM(CASE WHEN status = 'completed' THEN amount ELSE 0 END), 0) as total_revenue,
            COALESCE(SUM(CASE WHEN status = 'completed' AND created_at >= %s THEN amount ELSE 0 END), 0) as monthly_revenue
        FROM admin_payments
        """
        
        # Calculate start of current month
        now = datetime.utcnow()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        overview_result = rds_db.execute_query(overview_query, (month_start,), fetch_one=True)
        overview = overview_result[0] if overview_result else {}
        
        # Payment method breakdown
        method_query = """
        SELECT payment_method, COUNT(*) as count, COALESCE(SUM(amount), 0) as total_amount
        FROM admin_payments 
        WHERE status = 'completed'
        GROUP BY payment_method
        ORDER BY count DESC
        """
        
        method_result = rds_db.execute_query(method_query)
        method_breakdown = [
            {
                'method': row['payment_method'],
                'count': row['count'],
                'total_amount': float(row['total_amount'])
            }
            for row in method_result
        ]
        
        return jsonify({
            'success': True,
            'message': 'Payment statistics retrieved successfully',
            'data': {
                'overview': {
                    'total_payments': overview.get('total_payments', 0),
                    'successful_payments': overview.get('successful_payments', 0),
                    'pending_payments': overview.get('pending_payments', 0),
                    'failed_payments': overview.get('failed_payments', 0),
                    'refunded_payments': overview.get('refunded_payments', 0),
                    'total_revenue': float(overview.get('total_revenue', 0)),
                    'monthly_revenue': float(overview.get('monthly_revenue', 0))
                },
                'method_breakdown': method_breakdown
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Get payment stats error: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to retrieve payment statistics',
            'error': str(e)
        }), 500

@admin_payments_bp.route('/revenue-chart', methods=['GET'])
@add_security_headers
@require_admin_auth
def get_revenue_chart():
    """
    Get revenue chart data for specified period
    GET /api/admin/payments/revenue-chart%speriod=7d
    """
    try:
        period = request.args.get('period', '7d')
        
        # Calculate date range based on period
        now = datetime.utcnow()
        if period == '7d':
            start_date = now - timedelta(days=7)
            date_format = 'Day'
        elif period == '30d':
            start_date = now - timedelta(days=30)
            date_format = 'Day'
        elif period == '12m':
            start_date = now - timedelta(days=365)
            date_format = 'Month'
        else:
            start_date = now - timedelta(days=7)
            date_format = 'Day'
        
        # Query for chart data
        if date_format == 'Day':
            chart_query = """
            SELECT 
                DATE(created_at) as date,
                COALESCE(SUM(CASE WHEN status = 'completed' THEN amount ELSE 0 END), 0) as value
            FROM admin_payments 
            WHERE created_at >= %s
            GROUP BY DATE(created_at)
            ORDER BY date
            """
        else:
            chart_query = """
            SELECT 
                DATE_TRUNC('month', created_at) as date,
                COALESCE(SUM(CASE WHEN status = 'completed' THEN amount ELSE 0 END), 0) as value
            FROM admin_payments 
            WHERE created_at >= %s
            GROUP BY DATE_TRUNC('month', created_at)
            ORDER BY date
            """
        
        chart_result = rds_db.execute_query(chart_query, (start_date,), fetch_one=True)
        if not chart_result:
            return jsonify({"error": "Resource not found"}), 404
        
        # Format chart data
        chart_data = []
        for row in chart_result:
            if date_format == 'Day':
                name = row['date'].strftime('%a') if row['date'] else 'Unknown'
            else:
                name = row['date'].strftime('%b') if row['date'] else 'Unknown'
            
            chart_data.append({
                'name': name,
                'value': float(row['value'])
            })
        
        return jsonify({
            'success': True,
            'message': 'Revenue chart data retrieved successfully',
            'data': {
                'chart_data': chart_data,
                'period': period,
                'start_date': start_date.isoformat(),
                'end_date': now.isoformat()
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Get revenue chart error: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to retrieve revenue chart data',
            'error': str(e)
        }), 500

@admin_payments_bp.route('/add', methods=['POST'])
@add_security_headers
@require_admin_auth
@validate_json('user_id', 'amount', 'payment_method')
def add_payment():
    """
    Add a new payment record
    POST /api/admin/payments/add
    """
    try:
        data = request.get_json()
        admin_email = request.admin_user['email']
        
        # Generate payment ID and transaction ID
        payment_id = str(uuid.uuid4())
        transaction_id = data.get('transaction_id', f"TXN-{uuid.uuid4().hex[:8].upper()}")
        
        # Create payment
        create_query = """
        INSERT INTO admin_payments (
            id, user_id, amount, currency, status, payment_method, 
            transaction_id, description, metadata, created_at, updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        rds_db.execute_query(create_query, (
            payment_id,
            data['user_id'],
            data['amount'],
            data.get('currency', 'USD'),
            data.get('status', 'completed'),
            data['payment_method'],
            transaction_id,
            data.get('description', ''),
            data.get('metadata'),
            datetime.utcnow(),
            datetime.utcnow()
        ))
        
        # Log admin action
        from routes.admin_auth import log_admin_action
        log_admin_action(
            admin_email, 'CREATE_PAYMENT', 'payment', payment_id,
            f"Added payment: {transaction_id} - ${data['amount']}",
            request.remote_addr, request.headers.get('User-Agent')
        )
        
        return jsonify({
            'success': True,
            'message': 'Payment added successfully',
            'payment_id': payment_id,
            'transaction_id': transaction_id
        }), 201
        
    except Exception as e:
        logger.error(f"Add payment error: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to add payment',
            'error': str(e)
        }), 500

@admin_payments_bp.route('/<payment_id>', methods=['PATCH'])
@add_security_headers
@require_admin_auth
def update_payment(payment_id):
    """
    Update payment details
    PATCH /api/admin/payments/{payment_id}
    """
    try:
        data = request.get_json()
        admin_email = request.admin_user['email']
        
        # Check if payment exists
        payment_query = "SELECT * FROM admin_payments WHERE id = %s"
        payments = rds_db.execute_query(payment_query, (payment_id,), fetch_one=True)
        if not payments:
            return jsonify({"error": "Resource not found"}), 404
        
        if not payments:
            return jsonify({
                'success': False,
                'message': 'Payment not found'
            }), 404
        
        # Build update query
        update_fields = []
        params = []
        
        allowed_fields = ['status', 'payment_method', 'description', 'metadata']
        for field in allowed_fields:
            if field in data:
                update_fields.append(f"{field} = %s")
                params.append(data[field])
        
        if not update_fields:
            return jsonify({
                'success': False,
                'message': 'No valid fields to update'
            }), 400
        
        update_fields.append("updated_at = %s")
        params.append(datetime.utcnow())
        params.append(payment_id)
        
        update_query = f"UPDATE admin_payments SET {', '.join(update_fields)} WHERE id = %s"
        rds_db.execute_query(update_query, params)
        
        # Log admin action
        from routes.admin_auth import log_admin_action
        log_admin_action(
            admin_email, 'UPDATE_PAYMENT', 'payment', payment_id,
            f"Updated payment: {payments[0]['transaction_id']}",
            request.remote_addr, request.headers.get('User-Agent')
        )
        
        return jsonify({
            'success': True,
            'message': 'Payment updated successfully'
        }), 200
        
    except Exception as e:
        logger.error(f"Update payment error: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to update payment',
            'error': str(e)
        }), 500

@admin_payments_bp.route('/refund/<payment_id>', methods=['POST'])
@add_security_headers
@require_admin_auth
@validate_json('reason')
def process_refund(payment_id):
    """
    Process a refund for a payment
    POST /api/admin/payments/refund/{payment_id}
    """
    try:
        data = request.get_json()
        admin_email = request.admin_user['email']
        
        # Check if payment exists and is eligible for refund
        payment_query = "SELECT * FROM admin_payments WHERE id = %s"
        payments = rds_db.execute_query(payment_query, (payment_id,), fetch_one=True)
        if not payments:
            return jsonify({"error": "Resource not found"}), 404
        
        if not payments:
            return jsonify({
                'success': False,
                'message': 'Payment not found'
            }), 404
        
        payment = payments[0]
        
        if payment['status'] != 'completed':
            return jsonify({
                'success': False,
                'message': 'Only completed payments can be refunded'
            }), 400
        
        # Update payment status to refunded
        update_query = """
        UPDATE admin_payments 
        SET status = 'refunded', updated_at = %s 
        WHERE id = %s
        """
        
        rds_db.execute_query(update_query, (datetime.utcnow(), payment_id))
        
        # Log admin action
        from routes.admin_auth import log_admin_action
        log_admin_action(
            admin_email, 'PROCESS_REFUND', 'payment', payment_id,
            f"Processed refund for {payment['transaction_id']}: {data['reason']}",
            request.remote_addr, request.headers.get('User-Agent')
        )
        
        return jsonify({
            'success': True,
            'message': 'Refund processed successfully',
            'refund_amount': float(payment['amount']),
            'reason': data['reason']
        }), 200
        
    except Exception as e:
        logger.error(f"Process refund error: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to process refund',
            'error': str(e)
        }), 500
