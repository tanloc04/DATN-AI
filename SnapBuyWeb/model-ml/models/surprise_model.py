import pandas as pd
from surprise import Dataset, Reader, SVD
from surprise.model_selection import train_test_split
import pickle
import os

def train_surprise_model(input_path="model-ml/data/ratings.csv", output_path="model-ml/model_surprise.pkl"):
    if not os.path.exists(input_path):
        print(f"❌ File không tồn tại: {input_path}")
        return

    try:
        # Bản mới đã có header, dùng dấu phẩy
        df = pd.read_csv(input_path)
        df.rename(columns={"userId": "user_id", "movieId": "item_id"}, inplace=True)
        df = df[["user_id", "item_id", "rating"]]  # Bỏ timestamp
    except Exception as e:
        print(f"❌ Lỗi đọc file: {e}")
        return

    if df.empty:
        print("⚠️ File rỗng sau khi làm sạch.")
        return

    reader = Reader(rating_scale=(df["rating"].min(), df["rating"].max()))
    data = Dataset.load_from_df(df, reader)
    trainset, testset = train_test_split(data, test_size=0.2, random_state=42)

    model = SVD()
    model.fit(trainset)

    print("🔍 Một vài dự đoán mẫu:")
    for i in range(min(10, len(testset))):
        uid, iid, true_r = testset[i]
        pred = model.predict(uid, iid, r_ui=true_r)
        print(f"🧑 User {uid} - 🛍️ Item {iid} | Thực tế: {true_r}, Dự đoán: {pred.est:.2f}")

    try:
        with open(output_path, "wb") as f:
            pickle.dump(model, f)
        print(f"✅ Mô hình đã lưu tại: {output_path}")
    except Exception as e:
        print(f"❌ Không thể lưu model: {e}")
