import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sqlalchemy import create_engine, inspect
import pickle

# Đường dẫn lưu model
MODEL_PATH = 'model_ml/model_content_mind.pkl'

print("[INFO] Đang kết nối database...")
engine = create_engine('sqlite:///instance/snapbuy.db')
inspector = inspect(engine)
print(inspector.get_table_names())

print("[INFO] Đang đọc dữ liệu từ bảng user_history, item, category, brand...")
history_df = pd.read_sql("SELECT * FROM user_history", engine)
item_df = pd.read_sql("SELECT * FROM item", engine)
category_df = pd.read_sql("SELECT id, name FROM category", engine)
brand_df = pd.read_sql("SELECT id, name FROM brand", engine)

print("[INFO] Đang merge để lấy tên category và brand cho items...")
# Merge bảng category và brand vào item
item_df = item_df.merge(category_df, left_on='category_id', right_on='id', how='left', suffixes=('', '_cat'))
item_df = item_df.merge(brand_df, left_on='brand_id', right_on='id', how='left', suffixes=('', '_brand'))

print("[INFO] Tạo cột description từ tên category và brand...")
item_df['description'] = item_df[['name_cat', 'name_brand']] \
    .fillna('') \
    .agg(' '.join, axis=1)

print("[INFO] Mẫu dữ liệu description:")
print(item_df[['name_cat', 'name_brand', 'description']].head())

print("[INFO] Tạo chỉ số ánh xạ giữa item_id và vị trí index...")
item_id_to_index = {item_id: idx for idx, item_id in enumerate(item_df['id'])}
index_to_item_id = {idx: item_id for item_id, idx in item_id_to_index.items()}

print("[INFO] Đang huấn luyện TF-IDF vectorizer...")
vectorizer = TfidfVectorizer(stop_words='english')
tfidf_matrix = vectorizer.fit_transform(item_df['description'])

print("[INFO] Xây dựng hồ sơ người dùng (user profiles)...")
user_profiles = {}
for user_id, group in history_df.groupby('user_id'):
    viewed_indices = group['item_id'].map(item_id_to_index).dropna().astype(int).tolist()
    if viewed_indices:
        user_profiles[user_id] = tfidf_matrix[viewed_indices].mean(axis=0)

print(f"[INFO] Đang lưu mô hình tại {MODEL_PATH}...")
with open(MODEL_PATH, 'wb') as f:
    pickle.dump({
        'tfidf_matrix': tfidf_matrix,
        'vectorizer': vectorizer,
        'item_ids': list(item_df['id']),
        'user_profiles': user_profiles,
        'items_df': item_df
    }, f)

print("[SUCCESS] Mô hình đã được huấn luyện và lưu thành công!")
