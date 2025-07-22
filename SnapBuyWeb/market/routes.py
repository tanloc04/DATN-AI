from flask_login import login_user, logout_user, current_user, login_required
from market import app, db
from flask import request, render_template, redirect, url_for, flash, session, Blueprint, jsonify
from market.models import Admin, Item, User, Order, Category, Rating
from market.forms import AdminRegisterForm, AdminLoginForm, ItemForm, UserRegisterForm, UserLoginForm, OrderForm, CategoryForm, RatingForm
from sqlalchemy.orm import joinedload
import pickle
import os
from datetime import datetime, timedelta

recommend_bp = Blueprint('recommend', __name__)

@app.route('/')
@app.route('/admin/dashboard')
@login_required
def dashboard_page():
    return render_template('admin/dashboard.html')

@app.route('/admin/revenue_data')
def revenue_data():
    delivered_orders = Order.query.filter_by(status='delivered').all()

    revenue_by_item = {}
    for order in delivered_orders:
        item = order.item
        if item.name in revenue_by_item:
            revenue_by_item[item.name] += float(order.total_price)
        else:
            revenue_by_item[item.name] = float(order.total_price)

    labels = list(revenue_by_item.keys())
    data = list(revenue_by_item.values())

    return jsonify({'labels': labels, 'data': data})

@app.route('/admin/analyze')
@login_required
def analyze_page():
    return render_template('admin/analyze.html')

@app.route('/market')
def market_page():
    items = Item.query.all()
    categories = Category.query.all()
    return render_template('user/market.html', items=items, categories=categories)

@app.route('/items')
def item_list():
    items = Item.query.all()
    return render_template('item/list.html', items=items)

@app.route('/items/add', methods=['GET', 'POST'])
def add_item():
    form = ItemForm()
    form.category_id.choices = [(c.id, c.name) for c in Category.query.all()]
    if form.validate_on_submit():
        item = Item(
            name=form.name.data,
            price=form.price.data,
            description=form.description.data,
            image_url=form.image_url.data,
            category_id=form.category_id.data
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

    # Gán category_id cho field dropdown nếu GET (không cần khi POST vì FlaskForm tự xử lý)
    if request.method == 'GET':
        form.category_id.data = item.category_id

    if form.validate_on_submit():
        item.name = form.name.data
        item.price = form.price.data
        item.description = form.description.data
        item.image_url = form.image_url.data
        item.category_id = form.category_id.data  # 🔥 Đừng quên lưu lại lựa chọn danh mục

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
        Order.query.filter_by(item_id=id).delete()
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
    if current_user.is_authenticated:
        flash('You are already logged in', 'info')
        return redirect(url_for('dashboard_page'))
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
    if current_user.is_authenticated:
        flash('You must log out of your current account if you want to register a new account', 'info')
        return redirect(url_for('market_page'))
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
    if current_user.is_authenticated:
        flash('You are already logged in', 'info')
        return redirect(url_for('market_page'))
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

@app.route('/remove_from_cart/<int:item_id>')
@login_required
def remove_from_cart(item_id):
    if session.get('role') != 'user':
        flash('Chỉ người dùng mới có thể xóa sản phẩm khỏi giỏ hàng.', 'warning')
        return redirect(url_for('login_by_user'))

    cart = session.get('cart', {})
    if str(item_id) in cart:
        del cart[str(item_id)]
        session['cart'] = cart
        flash('Sản phẩm đã được xóa khỏi giỏ hàng.', 'success')
    else:
        flash('Sản phẩm không tồn tại trong giỏ hàng.', 'warning')

    return redirect(url_for('view_cart'))

@app.route('/increase_quantity/<int:item_id>')
@login_required
def increase_quantity(item_id):
    if session.get('role') != 'user':
        flash('Chỉ người dùng mới có thể thay đổi số lượng.', 'warning')
        return redirect(url_for('login_by_user'))

    cart = session.get('cart', {})
    if str(item_id) in cart:
        cart[str(item_id)] += 1
        session['cart'] = cart
        flash('Số lượng đã được tăng.', 'success')
    else:
        flash('Sản phẩm không tồn tại trong giỏ hàng.', 'warning')

    return redirect(url_for('view_cart'))

@app.route('/decrease_quantity/<int:item_id>')
@login_required
def decrease_quantity(item_id):
    if session.get('role') != 'user':
        flash('Chỉ người dùng mới có thể thay đổi số lượng.', 'warning')
        return redirect(url_for('login_by_user'))

    cart = session.get('cart', {})
    if str(item_id) in cart and cart[str(item_id)] > 1:
        cart[str(item_id)] -= 1
        session['cart'] = cart
        flash('Số lượng đã được giảm.', 'success')
    elif str(item_id) in cart and cart[str(item_id)] == 1:
        del cart[str(item_id)]
        session['cart'] = cart
        flash('Số lượng giảm xuống 0, sản phẩm đã bị xóa.', 'success')
    else:
        flash('Sản phẩm không tồn tại trong giỏ hàng.', 'warning')

    return redirect(url_for('view_cart'))

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    if session.get('role') != 'user':
        flash('Chỉ người dùng mới có thể đặt hàng.', 'warning')
        return redirect(url_for('login_by_user'))

    cart = session.get('cart', {})
    if not cart:
        flash('Giỏ hàng của bạn đang trống.', 'warning')
        return redirect(url_for('view_cart'))

    form = OrderForm()
    items = Item.query.filter(Item.id.in_([int(k) for k in cart.keys()])).all()
    total_price = sum(float(item.price) * cart.get(str(item.id), 0) for item in items)

    if form.validate_on_submit():
        try:
            for item_id in cart.keys():
                item = Item.query.get_or_404(int(item_id))
                quantity = cart[item_id]
                order = Order(
                    user_id=current_user.id,
                    item_id=item.id,
                    quantity=quantity,
                    total_price=float(item.price) * quantity
                )
                db.session.add(order)
            db.session.commit()
            session.pop('cart', None)
            flash('Đơn hàng của bạn đã được đặt thành công!', 'success')
            return redirect(url_for('order_confirmation'))
        except Exception as e:
            db.session.rollback()
            flash(f'Có lỗi khi đặt hàng: {str(e)}', 'danger')
            return redirect(url_for('checkout'))

    return render_template('user/checkout.html', form=form, cart_items=items, cart=cart, total_price=total_price)

@app.route('/order_confirmation')
@login_required
def order_confirmation():
    if session.get('role') != 'user':
        flash('Chỉ người dùng mới có thể xem xác nhận đơn hàng.', 'warning')
        return redirect(url_for('login_by_user'))
    return render_template('user/order_confirmation.html')

@app.route('/categories')
@login_required
def category_list():
    categories = Category.query.all()
    return render_template('category/list.html', categories=categories)

@app.route('/categories/add', methods=['GET', 'POST'])
@login_required
def add_category():
    form = CategoryForm()
    if form.validate_on_submit():
        new_category = Category(
            name = form.name.data,
            description = form.description.data
        )
        db.session.add(new_category)
        db.session.commit()
        flash('Danh mục mới đã được thêm!', 'success')
        return redirect(url_for('category_list'))
    return render_template('category/add.html', form=form)

@app.route('/categories/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_category(id):
    category = Category.query.get_or_404(id)
    form = CategoryForm(obj=category)

    if form.validate_on_submit():
        category.name = form.name.data
        category.description = form.description.data
        db.session.commit()
        flash('Danh mục đã được cập nhật!', 'success')
        return redirect(url_for('category_list'))

    return render_template('category/edit.html', form=form, category=category)

@app.route('/categories/delete/<int:id>', methods=['POST'])
@login_required
def delete_category(id):
    category = Category.query.get_or_404(id)
    try:
        db.session.delete(category)
        db.session.commit()
        flash('Đã xoá danh mục thành công!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Lỗi xoá danh mục: {str(e)}', 'danger')
    return redirect(url_for('category_list'))

@app.route('/orders')
@login_required
def view_orders():
    if current_user.is_authenticated and hasattr(current_user, 'orders'):
        orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
        return render_template('user/order.html', orders=orders)
    flash('Hãy đăng nhập!', 'warning')
    return redirect(url_for('login_by_user'))

@app.route('/orders/confirm/<int:order_id>', methods=['POST'])
@login_required
def confirm_order(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('view_orders'))

    order.status = 'delivered'
    db.session.commit()
    flash('Order marked as delivered. Please leave a review.', 'success')
    return redirect(url_for('rate_order', order_id=order_id))

@app.route('/orders/rate/<int:order_id>', methods=['GET', 'POST'])
@login_required
def rate_order(order_id):
    order = Order.query.get_or_404(order_id)

    if order.user_id != current_user.id:
        flash('You are not authorized to rate this order.', 'danger')
        return redirect(url_for('view_orders'))

    form = RatingForm()
    if form.validate_on_submit():
        rating = Rating(
            order_id=order.id,
            user_id=current_user.id,
            item_id=order.item_id,
            rating=form.rating.data,
            review=form.review.data
        )
        db.session.add(rating)
        db.session.commit()
        flash('Cảm ơn bạn đã đánh giá. Chúc bạn mua sắm vui vẻ!', 'success')
        return redirect(url_for('view_orders'))

    return render_template('user/rate_order.html', form=form, order=order)

@recommend_bp.route('/recommendations')
@login_required
def recommend():
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    MODEL_PATH = os.path.join(BASE_DIR, 'model-ml', 'model.pkl')

    try:
        with open(MODEL_PATH, 'rb') as f:
            model = pickle.load(f)

        # Lấy toàn bộ sản phẩm
        items = Item.query.options(joinedload(Item.orders)).all()

        # Lấy ID sản phẩm mà user đã mua
        purchased_item_ids = {order.item_id for order in current_user.orders}

        # Lọc ra những sản phẩm mà user chưa mua
        item_ids = [item.id for item in items if item.id not in purchased_item_ids]

        # Dự đoán rating
        predictions = []
        for item_id in item_ids:
            pred = model.predict(str(current_user.id), str(item_id))
            predictions.append((item_id, pred.est))

        # Chọn top 5 sản phẩm được dự đoán rating cao nhất
        top_items = sorted(predictions, key=lambda x: x[1], reverse=True)[:5]
        recommended_items = [Item.query.get(item_id) for item_id, _ in top_items]

        return render_template('user/recommendations.html', items=recommended_items)

    except Exception as e:
        return f"Lỗi gợi ý: {str(e)}"


@app.route('/categories/<int:category_id>')
@login_required
def category_detail(category_id):
    category = Category.query.get_or_404(category_id)
    items = Item.query.filter_by(category_id=category.id).all()
    categories = Category.query.all()

    return render_template('user/market.html', items=items, categories=categories, selected_category=category)

@app.route('/admin/users')
@login_required
def manage_users():
    users = User.query.all()
    return render_template('admin/user_management.html', users=users)

@app.route('/admin/users/toggle_status/<int:user_id>', methods=['POST'])
@login_required
def toggle_user_status(user_id):
    user = User.query.get_or_404(user_id)
    action = request.form.get('action')
    if action == 'deactivate':
        user.is_active = False
        user.deactivated_at = datetime.utcnow()
        flash(f'User "{user.username}" has been deactivated.', 'success')
    elif action == 'activate':
        user.is_active = True
        user.deactivated_at = None
        flash(f'User "{user.username}" has been activated.', 'success')
    db.session.commit()
    return redirect(url_for('manage_users'))

@app.cli.command('cleanup_users')
def cleanup_inactive_users():
    threshold_date = datetime.utcnow() - timedelta(days=30)
    inactive_users = User.query.filter(User.is_active == False, User.deactivated_at <= threshold_date).all()
    for user in inactive_users:
        db.session.delete(user)
    db.session.commit()
    print(f"Cleaned up {len(inactive_users)} inactive users")

@app.route('/admin/profile', methods=['GET', 'POST'])
@login_required
def admin_profile():
    if session.get('role') != 'admin':
        flash('You are not authorized to access this page.', 'danger')
        return redirect(url_for('login_admin'))

    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if current_user.check_password_correction(current_password):
            if new_password == confirm_password and len(new_password) >= 6:
                current_user.password = new_password
                db.session.commit()
                flash('Password updated successfully!', 'success')
            else:
                flash('New passwords do not match or are too short (minimum 6 characters).', 'danger')
        else:
            flash('Current password is incorrect.', 'danger')

    return render_template('admin/profile.html')