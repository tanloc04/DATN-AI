from market import app

products = [
    {"id": 1, "name": "Táo", "price": "10000", "description": "Hàng mới tươi tốt"},
    {"id": 2, "name": "Bột giặt", "price": "150000", "description": "Sản phẩm chất lượng"},
    {"id": 3, "name": "Sữa chua", "price": "50000", "description": "Sản phẩm uy tín"}
]

orders = [
    {
        'id': 1,
        'customer_name': 'Nguyễn Văn A',
        'product_name': 'Dầu ăn',
        'status': 'Processing'
    },
    {
        'id': 2,
        'customer_name': 'Trần Thị B',
        'product_name': 'Mỳ gói',
        'status': 'Delivering'
    },
    {
        'id': 3,
        'customer_name': 'Lê Tuấn C',
        'product_name': 'Dầu gội',
        'status': 'Completed'
    }
]

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