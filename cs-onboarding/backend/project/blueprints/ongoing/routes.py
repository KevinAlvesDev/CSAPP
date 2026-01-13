from flask import render_template
from . import ongoing_bp
from ..auth import login_required

@ongoing_bp.route('/dashboard')
@login_required
def dashboard():
    return render_template('pages/ongoing/dashboard.html')
