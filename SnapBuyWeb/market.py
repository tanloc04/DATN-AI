import threading
import webbrowser

from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

products = [
    {"id": 1, "name": "Táo", "price": "10000", "description": "Hàng mới tươi tốt"},
    {"id": 2, "name": "Bột giặt", "price": "150000", "description": "Sản phẩm chất lượng"},
    {"id": 3, "name": "Sữa chua", "price": "50000", "description": "Sản phẩm uy tín"}
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

def open_browser():
    webbrowser.open_new('http://127.0.0.1:5000/')

if __name__ == '__main__':
    threading.Timer(1.25, open_browser).start()
    app.run(debug=True, use_reloader=False)

