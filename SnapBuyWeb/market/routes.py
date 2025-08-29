import numpy as np
from flask_login import login_user, logout_user, current_user, login_required
from market import app, db
from flask import request, render_template, redirect, url_for, flash, session, Blueprint, jsonify
from market.models import Item, User, Order, Category, Rating, Tag, Brand, UserHistory
from market.forms import AdminRegisterForm, AdminLoginForm, ItemForm, UserRegisterForm, UserLoginForm, OrderForm, CategoryForm, RatingForm, TagForm, BrandForm
from market.decorators import admin_required
from sqlalchemy.orm import joinedload
from sklearn.metrics.pairwise import linear_kernel
import pickle
import os
from datetime import datetime, timedelta
from functools import wraps
from werkzeug.security import generate_password_hash
from sqlalchemy import or_, func

tag_bp = Blueprint('tag', __name__, url_prefix='/tags')
brand_bp = Blueprint('brand', __name__, url_prefix='/brands')

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login_admin'))
        elif session.get('role') != 'admin':
            return redirect(url_for('market_page'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin/dashboard')
@admin_required
def dashboard_page():
    total_items = Item.query.count()
    total_users = User.query.count()
    total_orders = Order.query.count()
    total_ratings = Rating.query.count()
    total_categories = Category.query.count()
    total_brands = Brand.query.count()
    total_tags = Tag.query.count()
    return render_template('admin/dashboard.html',
                           total_items=total_items,
                           total_users=total_users,
                           total_orders=total_orders,
                           total_ratings=total_ratings,
                           total_categories=total_categories,
                           total_brands=total_brands,
                           total_tags=total_tags)

@app.route('/admin/revenue_data')
@admin_required
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
@admin_required
def analyze_page():
    return render_template('admin/analyze.html')


@app.route('/')
@app.route('/market')
def market_page():
    from model_ml.content_recommender import get_content_recommendations
    from model_ml.mind_recommender import get_mind_recommendations
    from model_ml.ratings_recommender import get_ratings_recommendations

    if current_user.is_authenticated:
        recommended_items = get_content_recommendations(current_user, top_n=5)
        mind_items = get_mind_recommendations(current_user, top_n=5)
        ratings_items = get_ratings_recommendations(current_user, top_n=5)
    else:
        recommended_items = []
        mind_items = []
        ratings_items = []

    latest_items = Item.query.order_by(Item.created_at.desc()).limit(10).all()

    categories = Category.query.all()
    featured_categories = categories[:10]

    price_filter = request.args.get('price_filter')
    query = Item.query
    if price_filter == 'asc':
        query = query.order_by(Item.price.asc())
    elif price_filter == 'desc':
        query = query.order_by(Item.price.desc())
    items = query.limit(16).all()

    suggested_items = Item.query.order_by(Item.id.desc()).limit(8).all()

    recently_viewed_ids = session.get('viewed_items', [])
    recently_viewed_items = Item.query.filter(Item.id.in_(recently_viewed_ids)).all()
    id_order = {id_: i for i, id_ in enumerate(recently_viewed_ids)}
    recently_viewed_items.sort(key=lambda x: id_order.get(x.id, 0))

    return render_template(
        'user/market.html',
        items=items,
        categories=categories,
        featured_categories=featured_categories,
        suggested_items=suggested_items,
        recently_viewed=recently_viewed_items,
        selected_category=None,
        price_filter=price_filter,
        latest_items=latest_items,
        recommended_items=recommended_items,
        mind_items=mind_items,
        ratings_items=ratings_items
    )

@app.route('/items')
@admin_required
def item_list():
    page = request.args.get('page', 1, type=int)
    q = request.args.get('q', '', type=str)
    per_page = 12
    query = Item.query
    if q:
        query = query.filter(Item.name.ilike(f"%{q}%"))
    pagination = query.order_by(Item.created_at.desc()).paginate(page=page, per_page=per_page)
    items = pagination.items
    return render_template('item/list.html', items=items, pagination=pagination)

@app.route('/items/add', methods=['GET', 'POST'])
@admin_required
def add_item():
    form = ItemForm()
    form.category_id.choices = [(c.id, c.name) for c in Category.query.all()]
    form.brand_id.choices = [(b.id, b.name) for b in Brand.query.all()]
    form.tag_ids.choices = [(t.id, t.name) for t in Tag.query.all()]

    if form.validate_on_submit():
        try:
            item = Item(
                name=form.name.data,
                price=form.price.data,
                description=form.description.data,
                image_url=form.image_url.data,
                category_id=form.category_id.data,
                brand_id=form.brand_id.data
            )

            if form.tag_ids.data:
                item.tags = Tag.query.filter(Tag.id.in_(form.tag_ids.data)).all()

            db.session.add(item)
            db.session.commit()

            flash(f'Item "{item.name}" đã được thêm thành công!', 'success')
            return redirect(url_for('item_list'))

        except Exception as e:
            db.session.rollback()
            flash(f'Lỗi khi thêm sản phẩm: {str(e)}', 'danger')

    return render_template('item/add.html', form=form)

@app.route('/items/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_item(id):
    item = Item.query.get_or_404(id)
    form = ItemForm(obj=item)

    form.category_id.choices = [(c.id, c.name) for c in Category.query.all()]
    form.brand_id.choices = [(b.id, b.name) for b in Brand.query.all()]
    form.tag_ids.choices = [(t.id, t.name) for t in Tag.query.all()]

    if request.method == 'GET':
        form.category_id.data = item.category_id
        form.brand_id.data = item.brand_id
        form.tag_ids.data = [tag.id for tag in item.tags]

    if form.validate_on_submit():
        try:
            item.name = form.name.data
            item.price = form.price.data
            item.description = form.description.data
            item.image_url = form.image_url.data
            item.category_id = form.category_id.data
            item.brand_id = form.brand_id.data
            item.tags = Tag.query.filter(Tag.id.in_(form.tag_ids.data)).all()

            db.session.commit()
            flash(f'Sản phẩm "{item.name}" đã được cập nhật thành công!', 'success')
            return redirect(url_for('item_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'Đã xảy ra lỗi khi cập nhật: {str(e)}', 'danger')

    return render_template('item/edit.html', form=form, item=item)

@app.route('/items/delete/<int:id>')
@admin_required
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

@app.route('/admin/brands')
@admin_required
def list_brands():
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('search', '', type=str)
    per_page = 12

    query = Brand.query
    if search_query:
        query = query.filter(Brand.name.ilike(f"%{search_query}%"))

    pagination = query.order_by(Brand.name.asc()).paginate(page=page, per_page=per_page, error_out=False)
    brands = pagination.items

    return render_template(
        'brand/list.html',
        brands=brands,
        pagination=pagination,
        search_query=search_query
    )

@app.route('/admin/brands/add', methods=['GET', 'POST'])
@admin_required
def add_brand():
    form = BrandForm()
    if form.validate_on_submit():
        brand = Brand(name=form.name.data)
        db.session.add(brand)
        db.session.commit()
        flash('Brand added!', 'success')
        return redirect(url_for('list_brands'))
    return render_template('brand/add.html', form=form)

@app.route('/admin/brands/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_brand(id):
    brand = Brand.query.get_or_404(id)
    form = BrandForm(obj=brand)
    if form.validate_on_submit():
        brand.name = form.name.data
        db.session.commit()
        flash('Brand updated!', 'success')
        return redirect(url_for('list_brands'))
    return render_template('brand/edit.html', form=form, brand=brand)

@app.route('/admin/brands/delete/<int:id>')
@admin_required
def delete_brand(id):
    brand = Brand.query.get_or_404(id)
    db.session.delete(brand)
    db.session.commit()
    flash('Brand deleted!', 'success')
    return redirect(url_for('list_brands'))

@app.route('/admin/tags')
@admin_required
def list_tags():
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('search', '', type=str)
    per_page = 12

    query = Tag.query
    if search_query:
        query = query.filter(Tag.name.ilike(f"%{search_query}%"))

    pagination = query.order_by(Tag.name.asc()).paginate(page=page, per_page=per_page, error_out=False)
    tags = pagination.items

    return render_template(
        'tag/list.html',
        tags=tags,
        pagination=pagination,
        search_query=search_query
    )

@app.route('/admin/tags/add', methods=['GET', 'POST'])
@admin_required
def add_tag():
    form = TagForm()
    if form.validate_on_submit():
        tag = Tag(name=form.name.data)
        db.session.add(tag)
        db.session.commit()
        flash('Tag added successfully!', 'success')
        return redirect(url_for('list_tags'))
    return render_template('tag/add.html', form=form)

@app.route('/admin/tags/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_tag(id):
    tag = Tag.query.get_or_404(id)
    form = TagForm(obj=tag)
    if form.validate_on_submit():
        tag.name = form.name.data
        db.session.commit()
        flash('Tag updated!', 'success')
        return redirect(url_for('list_tags'))
    return render_template('tag/edit.html', form=form, tag=tag)

@app.route('/admin/tags/delete/<int:id>')
@admin_required
def delete_tag(id):
    tag = Tag.query.get_or_404(id)
    db.session.delete(tag)
    db.session.commit()
    flash('Tag deleted!', 'success')
    return redirect(url_for('list_tags'))

@app.route('/admin/register', methods=['GET', 'POST'])
def register_admin():
    form = AdminRegisterForm()
    if form.validate_on_submit():
        new_admin = User(
            username=form.username.data,
            email=form.email.data,
            role='admin'
        )
        new_admin.password = form.password.data
        db.session.add(new_admin)
        db.session.commit()
        flash('Admin account created successfully!', category='success')
        return redirect(url_for('login_admin'))
    return render_template('admin/register.html', form=form)

@app.route('/admin/login', methods=['GET', 'POST'])
def login_admin():
    if current_user.is_authenticated:
        if getattr(current_user, 'role', None) == 'user':
            flash('You must logout from user account before accessing admin.', 'warning')
            return redirect(url_for('logout'))
        else:
            return redirect(url_for('dashboard_page'))

    form = AdminLoginForm()
    if form.validate_on_submit():
        attempted_admin = User.query.filter_by(username=form.username.data, role='admin').first()
        if attempted_admin and attempted_admin.check_password_correction(form.password.data):
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
    if current_user.is_authenticated and session.get('role') == 'user':
        flash('Bạn đã đăng nhập rồi.', 'info')
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

    recent_view = UserHistory.query.filter_by(
        user_id=current_user.id,
        item_id=item.id,
        interaction_type='view'
    ).order_by(UserHistory.timestamp.desc()).first()

    now = datetime.utcnow()
    if not recent_view or (now - recent_view.timestamp > timedelta(minutes=10)):
        new_history = UserHistory(
            user_id=current_user.id,
            item_id=item.id,
            interaction_type='view',
            timestamp=now
        )
        db.session.add(new_history)
        db.session.commit()

    viewed = session.get('viewed_items', [])
    if item_id in viewed:
        viewed.remove(item_id)
    viewed.insert(0, item_id)
    session['viewed_items'] = viewed[:4]

    star_filter = request.args.get('stars', type=int)
    query = Rating.query.filter_by(item_id=item_id)
    if star_filter and 1 <= star_filter <= 5:
        query = query.filter(Rating.rating == star_filter)

    total_reviews = query.count()
    page = request.args.get('page', 1, type=int)
    per_page = 5
    pagination = query.order_by(Rating.created_at.desc()).paginate(page=page, per_page=per_page)
    reviews = pagination.items

    avg_rating = db.session.query(func.avg(Rating.rating)).filter_by(item_id=item_id).scalar()
    avg_rating = round(avg_rating, 1) if avg_rating else None

    has_rated = False
    if current_user.is_authenticated:
        has_rated = Rating.query.filter_by(user_id=current_user.id, item_id=item_id).first() is not None

    return render_template('item/detail.html',
                           item=item,
                           reviews=reviews,
                           avg_rating=avg_rating,
                           has_rated=has_rated,
                           total_reviews=total_reviews,
                           pagination=pagination,
                           star_filter=star_filter)

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

@app.route('/admin/categories')
@login_required

def category_list():
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('search', '', type=str)
    query = Category.query
    if search_query:
        query = query.filter(Category.name.ilike(f'%{search_query}%'))
    per_page = 10
    pagination = query.order_by(Category.name).paginate(page=page, per_page=per_page)
    categories = pagination.items
    return render_template('category/list.html', categories=categories,
                           pagination=pagination, search_query=search_query)

@app.route('/admin/categories/add', methods=['GET', 'POST'])
@login_required
def add_category():
    errors = {}

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()

        if not name:
            errors['name'] = ['Tên danh mục không được để trống.']
        elif Category.query.filter_by(name=name).first():
            errors['name'] = ['Tên danh mục đã tồn tại.']

        if not errors:
            new_category = Category(name=name, description=description)
            try:
                db.session.add(new_category)
                db.session.commit()
                flash('✅ Danh mục mới đã được thêm thành công!', 'success')
                return redirect(url_for('category_list'))
            except Exception as e:
                db.session.rollback()
                flash(f'❌ Lỗi khi thêm danh mục: {str(e)}', 'danger')

    return render_template('category/add.html', errors=errors)

@app.route('/admin/categories/edit/<int:id>', methods=['GET', 'POST'])
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

@app.route('/admin/orders')
@login_required
def view_orders():
    if current_user.is_authenticated and hasattr(current_user, 'orders'):
        orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
        return render_template('user/order.html', orders=orders)
    flash('Hãy đăng nhập!', 'warning')
    return redirect(url_for('login_by_user'))

@app.route('/admin/orders/confirm/<int:order_id>', methods=['POST'])
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

    existing_rating = Rating.query.filter_by(order_id=order.id, user_id=current_user.id).first()
    if existing_rating:
        flash('Bạn đã đánh giá đơn hàng này rồi.', 'info')
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

# @app.route('/recommendations/content')
# @login_required
# def recommend_content():
#     import pandas as pd
#     from sklearn.feature_extraction.text import TfidfVectorizer
#     from sklearn.metrics.pairwise import cosine_similarity
#     import os
#
#     BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
#     DATA_PATH = os.path.join(BASE_DIR, 'model_ml', 'data', 'items_content.csv')
#
#     try:
#         df = pd.read_csv(DATA_PATH)
#         df['combined'] = df['name'].fillna('') + ' ' + df['description'].fillna('') + ' ' + df['category'].fillna('')
#
#         tfidf = TfidfVectorizer(stop_words='english')
#         tfidf_matrix = tfidf.fit_transform(df['combined'])
#
#         cosine_sim = cosine_similarity(tfidf_matrix, tfidf_matrix)
#         indices = pd.Series(df.index, index=df['id'])
#
#         purchased_item_ids = {order.item_id for order in current_user.orders}
#
#         if not purchased_item_ids:
#             return "Bạn chưa mua sản phẩm nào để hệ thống gợi ý tương tự."
#
#         all_scores = {}
#         for item_id in purchased_item_ids:
#             if item_id not in indices:
#                 continue
#             idx = indices[item_id]
#             sim_scores = list(enumerate(cosine_sim[idx]))
#             sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
#
#             for sim_idx, score in sim_scores[1:]:
#                 sim_item_id = int(df.iloc[sim_idx]['id'])
#                 if sim_item_id not in purchased_item_ids:
#                     all_scores[sim_item_id] = max(all_scores.get(sim_item_id, 0), score)
#
#         if not all_scores:
#             return "Không tìm thấy sản phẩm tương tự phù hợp."
#
#         top_items = sorted(all_scores.items(), key=lambda x: x[1], reverse=True)[:5]
#         recommended_items = [Item.query.get(item_id) for item_id, _ in top_items]
#
#         return render_template('user/recommendations.html', items=recommended_items)
#
#     except Exception as e:
#         return f"Lỗi gợi ý content-based: {str(e)}"


# @app.route('/recommendations/ratings')
# @login_required
# def recommend():
#     BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
#     MODEL_PATH = os.path.join(BASE_DIR, 'model_ml', 'model_surprise.pkl')
#
#     try:
#         with open(MODEL_PATH, 'rb') as f:
#             model = pickle.load(f)
#
#
#         items = Item.query.options(joinedload(Item.orders)).all()
#
#
#         purchased_item_ids = {order.item_id for order in current_user.orders}
#
#
#         item_ids = [item.id for item in items if item.id not in purchased_item_ids]
#
#
#         predictions = []
#         for item_id in item_ids:
#             pred = model.predict(str(current_user.id), str(item_id))
#             print(f"[CF] Item {item_id} → predicted rating: {pred.est:.2f}")
#             predictions.append((item_id, pred.est))
#
#
#         top_items = sorted(predictions, key=lambda x: x[1], reverse=True)[:5]
#         recommended_items = [Item.query.get(item_id) for item_id, _ in top_items]
#
#         return render_template('user/recommendations.html', items=recommended_items)
#
#     except Exception as e:
#         return f"Lỗi gợi ý: {str(e)}"

# @app.route('/recommendations/content-mind')
# @login_required
# def recommend_mind_content():
#     model_path = os.path.join('model_ml', 'model_content_mind.pkl')
#
#     if not os.path.exists(model_path):
#         return "Mô hình MIND chưa được tìm thấy.", 500
#
#     with open(model_path, 'rb') as f:
#         mind_model = pickle.load(f)
#
#     user_id = current_user.id
#
#     tfidf_matrix = mind_model['tfidf_matrix']
#     user_profiles = mind_model['user_profiles']
#     item_ids = mind_model['item_ids']
#     items_df = mind_model['items_df']
#
#     if user_id not in user_profiles:
#         return "Người dùng chưa có lịch sử tương tác.", 400
#
#     user_vector = mind_model['user_profiles'][user_id]
#     user_vector = np.asarray(user_vector)
#     cosine_sim = linear_kernel(user_vector, tfidf_matrix).flatten()
#     top_indices = cosine_sim.argsort()[-10:][::-1]
#     recommended_item_ids = [item_ids[idx] for idx in top_indices]
#
#     recommended_items = items_df[items_df['id'].isin(recommended_item_ids)].to_dict(orient='records')
#
#     return render_template('user/recommendations.html', items=recommended_items)


@app.route('/categories/<int:category_id>')
def category_detail(category_id):
    category = Category.query.get_or_404(category_id)
    items = Item.query.filter_by(category_id=category.id).all()
    categories = Category.query.all()

    return render_template('user/market.html', items=items, categories=categories, selected_category=category)
@app.route('/category/<string:category_name>')
def products_by_category(category_name):
    price_filter = request.args.get('price_filter')
    page = request.args.get('page', 1, type=int)
    per_page = 10
    category = Category.query.filter_by(name=category_name).first_or_404()
    query = Item.query.filter_by(category_id=category.id)
    if price_filter == 'asc':
        query = query.order_by(Item.price.asc())
    elif price_filter == 'desc':
        query = query.order_by(Item.price.desc())
    pagination = query.paginate(page=page, per_page=per_page)
    items = pagination.items
    return render_template('user/category_products.html', items=items, category_name=category.name,
                           pagination=pagination, price_filter=price_filter)

@app.route('/admin/users')
@login_required
def manage_users():
    page = request.args.get('page', 1, type=int)
    keyword = request.args.get('q', '', type=str).strip()
    query = User.query
    if keyword:
        query = query.filter(
            (User.username.ilike(f'%{keyword}%')) |
            (User.email.ilike(f'%{keyword}%'))
        )
    users = query.order_by(User.username).paginate(page=page, per_page=10)
    return render_template('admin/user_management.html', users=users, keyword=keyword)

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
@login_required
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

@app.route('/user/search')
def search_product():
    keyword = request.args.get("q", "").strip()
    sort = request.args.get('sort', '')
    category_id = request.args.get('category', type=int)
    page = request.args.get('page', 1, type=int)
    per_page = 8
    query = Item.query
    if keyword:
        query = query.filter(or_(
            Item.name.ilike(f"%{keyword}%"),
            Item.description.ilike(f"%{keyword}%")
        ))
    if category_id:
        query = query.filter_by(category_id=category_id)

    if sort == 'price_asc':
        query = query.order_by(Item.price.asc())
    elif sort == 'price_desc':
        query = query.order_by(Item.price.desc())
    pagination = query.paginate(page=page, per_page=12)
    items = pagination.items
    categories = Category.query.all()
    return render_template('user/search.html', keyword=keyword, items=items, sort=sort,
                           selected_category=category_id, categories=categories, pagination=pagination)

@app.route('/user/profile', methods=['GET', 'POST'])
@login_required
def user_profile():
    if session.get('role') != 'user':
        flash("Bạn phải đăng nhập mới có quyền truy cập trang này", "danger")
        return redirect(url_for('market_page'))

    if request.method == 'POST':
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if not new_password or not confirm_password:
            flash("Vui lòng nhập đầy đủ thông tin mật khẩu.", "warning")
        elif new_password != confirm_password:
            flash("Mật khẩu không khớp.", "danger")
        else:
            current_user.password = generate_password_hash(new_password)
            db.session.commit()
            flash("Cập nhật mật khẩu thành công!", "success")
            return redirect(url_for('user_profile'))

    return render_template('/user/user_profile.html', user=current_user)

@app.route("/about_us")
def about_us():
    return render_template("user/about_us.html")

@app.route('/news')
def news_page():
    return render_template('/user/news.html')