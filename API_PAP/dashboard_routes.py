from flask import Blueprint, render_template, redirect, url_for, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from functools import wraps

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

def check_token_client_side(f):
    """
    Decorator to render template - JWT check happens client-side via JavaScript
    Server-side JWT validation happens when API routes are called
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated_function

# ===============================
# DASHBOARD ROUTES
# ===============================

@dashboard_bp.route('/')
@check_token_client_side
def index():
    """Main dashboard page"""
    return render_template('dashboard/index.html')

@dashboard_bp.route('/gps')
@check_token_client_side
def gps():
    """GPS monitoring page"""
    return render_template('dashboard/gps.html')

@dashboard_bp.route('/clima')
@check_token_client_side
def clima():
    """Climate data page (BME280)"""
    return render_template('dashboard/clima.html')

@dashboard_bp.route('/solo')
@check_token_client_side
def solo():
    """Soil moisture page"""
    return render_template('dashboard/solo.html')

@dashboard_bp.route('/visao')
@check_token_client_side
def visao():
    """Computer vision / pest detection page"""
    return render_template('dashboard/visao.html')

@dashboard_bp.route('/culturas')
@check_token_client_side
def culturas():
    """Crop management page"""
    return render_template('dashboard/culturas.html')

@dashboard_bp.route('/sensores')
@check_token_client_side
def sensores():
    """Sensors overview page"""
    return render_template('dashboard/sensores.html')

@dashboard_bp.route('/alertas')
@check_token_client_side
def alertas():
    """Alerts page"""
    return render_template('dashboard/alertas.html')

@dashboard_bp.route('/config')
@check_token_client_side
def config():
    """Configuration page"""
    return render_template('dashboard/config.html')

@dashboard_bp.route('/relatorios')
@check_token_client_side
def relatorios():
    """Farmer reports page"""
    return render_template('dashboard/relatorios.html')

@dashboard_bp.route('/apoio')
@check_token_client_side
def apoio():
    """Support and complaints page"""
    return render_template('dashboard/apoio.html')

@dashboard_bp.route('/agronomia')
@check_token_client_side
def agronomia():
    """Agronomic knowledge and recommendations page"""
    return render_template('dashboard/agronomia.html')


# ===============================
# AUTH ROUTES (Template Rendering)
# ===============================

auth_pages_bp = Blueprint('auth_pages', __name__)

@auth_pages_bp.route('/login')
def login():
    """Login page"""
    return render_template('auth/login.html')

@auth_pages_bp.route('/register')
def register():
    """Registration page"""
    return render_template('auth/register.html')

@auth_pages_bp.route('/')
def home():
    """Landing page"""
    return render_template('landing.html')

@auth_pages_bp.route('/admin/login')
def admin_login():
    """Super Admin login page"""
    return render_template('auth/superadmin_login.html')

@auth_pages_bp.route('/admin')
def admin():
    """Super Admin panel"""
    return render_template('admin/index.html')

@auth_pages_bp.route('/admin/fazenda/<int:fid>')
def admin_fazenda_detalhes(fid):
    """Farm details full page"""
    return render_template('admin/fazenda_detalhes.html', fazenda_id=fid)

@auth_pages_bp.route('/admin/farm')
def farm_admin():
    """Farm Admin panel"""
    return render_template('admin/farm_admin.html')

@auth_pages_bp.route('/admin/normal')
def admin_normal():
    """Admin Normal panel"""
    return render_template('admin/admin_normal.html')
