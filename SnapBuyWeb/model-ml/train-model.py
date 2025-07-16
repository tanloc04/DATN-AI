import pandas as pd
from surprise import Dataset, Reader, SVD
from surprise.model_selection import train_test_split
import pickle

file_path = "./model-ml/data/ratings.csv"
df = pd.read_csv(file_path, sep='\t', names=["user_id", "item_id", "rating", "timestamp"])

df = df.drop(columns=['timestamp'])

reader = Reader(rating_scale=(1, 5))

data = Dataset.load_from_df(df[['user_id', 'item_id', 'rating']], reader)

trainset, testset = train_test_split(data, test_size=0.2, random_state=42)

model = SVD()
model.fit(trainset)

print("Một vài dự đoán mẫu:")
for i in range(10):
    uid, iid, true_r = testset[i]
    pred = model.predict(uid, iid, r_ui=true_r)
    print(f"User {uid} - Item {iid} | Thực tế: {true_r}, Dự đoán: {pred.est:.2f}")

with open("model.pkl", "wb") as f:
    pickle.dump(model, f)

print("✅ Mô hình đã được huấn luyện và lưu vào 'model.pkl'")
