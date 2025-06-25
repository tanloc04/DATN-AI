from flask_login import login_user

from market import app, db
from flask import request, render_template, redirect, url_for, flash
from market.models import Admin
from market.forms import AdminRegisterForm, AdminLoginForm

@app.route('/')
@app.route('/home')
def home_page():
    return render_template('home.html')

@app.route('/market')
def market_page():
    return render_template('market.html', products=products)

@app.route('/add', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        name = request.form['name']
        price = request.form['price']
        description = request.form['description']
        new_id = products[-1]['id'] + 1 if products else 1
        products.append({
            "id": new_id,
            "name": name,
            "price": price,
            "description": description
        })
        return redirect(url_for('market_page'))
    return render_template('add.html')

@app.route('/delete/<int:id>')
def delete_product(id):
    global products
    products = [p for p in products if p['id'] != id]
    return redirect(url_for('market_page'))

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_product(id):
    product = next((p for p in products if p['id'] == id), None)
    if not product:
        return "NOT AVAILABLE", 404

    if request.method == 'POST':
        product['name'] = request.form['name']
        product['price'] = request.form['price']
        product['description'] = request.form['description']
        return redirect(url_for('market_page'))

    return render_template('edit.html', product=product)

@app.route('/orders')
def order_list():
    return render_template('orders.html', orders=orders)

@app.route('/update_order/<int:id>', methods=['POST'])
def update_order(id):
    new_status = request.form.get('status')
    for order in orders:
        if order['id'] == id:
            order['status'] = new_status
            break
    return redirect(url_for('order_list'))

@app.route('/admin/register', methods=['GET', 'POST'])
def register_admin():
    form = AdminRegisterForm()
    if form.validate_on_submit():
        admin_to_create = Admin(username=form.username.data,
                                email=form.email.data,
                                password=form.password.data)
        db.session.add(admin_to_create)
        db.session.commit()
        flash('Admin registered successfully!', category='success')
        return redirect(url_for('admin_login'))
    return render_template('admin/register.html', form=form)

@app.route('/admin/login', methods=['GET', 'POST'])
def login_admin():
    form = AdminLoginForm()
    if form.validate_on_submit():
        attempted_admin = Admin.query.filter_by(username=form.username.data).first()
        if attempted_admin and attempted_admin.check_password_correction(attempted_password=form.password.data):
            login_user(attempted_admin)
            flash(f'Success! You are logged in as: {attempted_admin.username}', category='success')
            return redirect(url_for('home_page'))
        else:
            flash('Username or password not match! Please try again.', category='danger')
    return render_template('admin/login.html', form=form)



