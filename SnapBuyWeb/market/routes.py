from flask_login import login_user, logout_user, current_user, login_required
from market import app, db
from flask import request, render_template, redirect, url_for, flash, session
from market.models import Admin, Item, User
from market.forms import AdminRegisterForm, AdminLoginForm, ItemForm, UserRegisterForm, UserLoginForm

@app.route('/')
@app.route('/admin/dashboard')
def dashboard_page():
    return render_template('admin/dashboard.html')

@app.route('/market')
def market_page():
    items = Item.query.all()
    return render_template('user/market.html', items=items)


@app.route('/items')
#@login_required
def item_list():
    items = Item.query.all()
    return render_template('item/list.html', items=items)


@app.route('/items/add', methods=['GET', 'POST'])
def add_item():
    form = ItemForm()
    if form.validate_on_submit():
        item = Item(
            name=form.name.data,
            price=form.price.data,
            description=form.description.data,
            image_url=form.image_url.data
        )
        try:
            db.session.add(item)
            db.session.commit()
            flash(f'Item "{item.name}" has been added successfully!', 'success')
            return redirect(url_for('item_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding item: {str(e)}', 'danger')
    return render_template('item/add.html', form=form)


@app.route('/items/edit/<int:id>', methods=['GET', 'POST'])
def edit_item(id):
    item = Item.query.get_or_404(id)
    form = ItemForm(obj=item)

    if form.validate_on_submit():
        item.name = form.name.data
        item.price = form.price.data
        item.description = form.description.data
        item.image_url = form.image_url.data
        try:
            db.session.commit()
            flash(f'Item "{item.name}" has been updated successfully!', 'success')
            return redirect(url_for('item_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating item: {str(e)}', 'danger')

    return render_template('item/edit.html', form=form, item=item)


@app.route('/items/delete/<int:id>')
def delete_item(id):
    item = Item.query.get_or_404(id)
    item_name = item.name
    try:
        db.session.delete(item)
        db.session.commit()
        flash(f'Item "{item_name}" has been deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting item: {str(e)}', 'danger')
    return redirect(url_for('item_list'))

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
        return redirect(url_for('login_admin'))
    return render_template('admin/register.html', form=form)

@app.route('/admin/login', methods=['GET', 'POST'])
def login_admin():
    form = AdminLoginForm()
    if form.validate_on_submit():
        attempted_admin = Admin.query.filter_by(username=form.username.data).first()
        if attempted_admin and attempted_admin.check_password_correction(attempted_password=form.password.data):
            login_user(attempted_admin)
            session['role'] = 'admin'
            flash(f'Success! You are logged in as: {attempted_admin.username}', category='success')
            return redirect(url_for('dashboard_page'))
        else:
            flash('Username or password not match! Please try again.', category='danger')
    return render_template('admin/login.html', form=form)


@app.route('/user/register', methods=['GET', 'POST'])
def register_user():
    form = UserRegisterForm()
    if form.validate_on_submit():
        user_to_create = User(username=form.username.data,
                                email=form.email.data,
                                password=form.password.data)
        db.session.add(user_to_create)
        db.session.commit()
        flash('User registered successfully!', category='success')
        return redirect(url_for('login_by_user'))
    return render_template('user/register.html', form=form)

@app.route('/user/login', methods=['GET', 'POST'])
def login_by_user():
    form = UserLoginForm()
    if form.validate_on_submit():
        attempted_user = User.query.filter_by(username=form.username.data).first()
        if attempted_user and attempted_user.check_password_correction(attempted_password=form.password.data):
            login_user(attempted_user)
            session['role'] = 'user'
            flash(f'Success! You are logged in as: {attempted_user.username}', category='success')
            return redirect(url_for('market_page'))
        else:
            flash('Username or password not match! Please try again.', category='danger')
    return render_template('user/login.html', form=form)

@app.route('/logout')
def logout():
    role = session.get('role')
    logout_user()
    session.pop('role', None)

    flash('You have been logged out!', category='info')
    if role == 'admin':
        return redirect(url_for('login_admin'))
    else:
        return redirect(url_for('login_by_user'))

@app.route('/item/<int:item_id>')
def product_detail(item_id):
    item = Item.query.get_or_404(item_id)
    return render_template('item/detail.html', item=item)

@app.route('/add_to_cart/<int:item_id>', methods=['POST'])
@login_required
def add_to_cart(item_id):
    if session.get('role') != 'user':
        flash('Chỉ người dùng mới có thể thêm sản phẩm vào giỏ hàng.', 'warning')
        return redirect(url_for('login_by_user'))

    item = Item.query.get_or_404(item_id)
    quantity = int(request.form.get('quantity', 1))

    if 'cart' not in session:
        session['cart'] = {}

    cart = session['cart']

    if str(item_id) in cart:
        cart[str(item_id)] += quantity
    else:
        cart[str(item_id)] = quantity

    session['cart'] = cart
    flash(f'Đã thêm {quantity} x "{item.name}" vào giỏ hàng.', 'success')
    return redirect(url_for('product_detail', item_id=item.id))

@app.context_processor
def inject_cart_quantity():
    cart = session.get('cart', {})
    total_items = sum(cart.values())
    return dict(cart_quantity=total_items)


from flask import session


@app.route('/cart')
@login_required
def view_cart():
    if session.get('role') != 'user':
        flash('Chỉ người dùng mới có thể xem giỏ hàng.', 'warning')
        return redirect(url_for('login_by_user'))

    cart = session.get('cart', {})
    items = Item.query.filter(Item.id.in_(cart.keys())).all()

    cart_details = []
    total_price = 0

    for item in items:
        quantity = cart[str(item.id)]
        item_total = float(item.price) * quantity
        total_price += item_total
        cart_details.append({
            'item': item,
            'quantity': quantity,
            'total': item_total
        })

    return render_template('user/cart.html', cart_items=cart_details, total_price=total_price)


