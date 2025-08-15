# SnapBuyWeb/model_ml/ratings_recommender.py
import os
import pickle
from market.models import Item
from sqlalchemy.orm import joinedload

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
MODEL_PATH = os.path.join(BASE_DIR, 'model_ml', 'model_surprise.pkl')

def get_ratings_recommendations(user, top_n=5):
    if not os.path.exists(MODEL_PATH):
        return []

    with open(MODEL_PATH, 'rb') as f:
        model = pickle.load(f)

    # Lấy toàn bộ sản phẩm + đơn hàng
    items = Item.query.options(joinedload(Item.orders)).all()

    # ID sản phẩm đã mua
    purchased_item_ids = {order.item_id for order in user.orders}

    # Sản phẩm chưa mua
    item_ids = [item.id for item in items if item.id not in purchased_item_ids]

    # Dự đoán rating
    predictions = []
    for item_id in item_ids:
        pred = model.predict(str(user.id), str(item_id))
        predictions.append((item_id, pred.est))

    # Top N sản phẩm
    top_items = sorted(predictions, key=lambda x: x[1], reverse=True)[:top_n]
    return [Item.query.get(item_id) for item_id, _ in top_items]
