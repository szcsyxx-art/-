from flask import Blueprint, request, render_template

ab = Blueprint('about', __name__)

@ab.route('/about')
def about():
    if request.method == 'GET':
        return render_template('about.html')
