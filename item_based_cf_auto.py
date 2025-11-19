import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity


# incarcare date

print("1. Se încarcă datele...")
try:
    users_df = pd.read_csv('users.csv')
    cars_df = pd.read_csv('car_data.csv')
except FileNotFoundError:
    print("Eroare: Fișierele users.csv sau car_data.csv lipsesc.")
    exit()

# curatare text
cols_to_strip_users = ['fuel_preference', 'transmission_preference', 'preferred_seller']
for col in cols_to_strip_users:
    users_df[col] = users_df[col].str.strip()

cols_to_strip_cars = ['name', 'fuel', 'transmission', 'seller_type']
for col in cols_to_strip_cars:
    cars_df[col] = cars_df[col].str.strip()

# elim duplicatelor
initial_count = len(cars_df)
cars_df.drop_duplicates(subset=['name', 'year', 'selling_price', 'km_driven', 'fuel', 'transmission', 'seller_type'], inplace=True)
print(f"   Au fost eliminate {initial_count - len(cars_df)} mașini duplicate. Ramase: {len(cars_df)}")

cars_df.reset_index(drop=True, inplace=True)

cars_subset = cars_df.head(300).copy() 
n_users = len(users_df)
n_items = len(cars_subset)


# gen matricei

user_item_matrix = np.zeros((n_users, n_items))
print("2. Se generează matricea de preferințe...")

for u_idx, user in users_df.iterrows():
    u_budget = user['budget']
    u_fuel = user['fuel_preference']
    u_trans = user['transmission_preference']
    u_seller = user['preferred_seller']
    
    for c_idx, car in cars_subset.iterrows():
        score = 0
        
        if car['selling_price'] <= u_budget:
            score = 2 
            
           
            if car['fuel'] == u_fuel:
                score += 3
            
           
            if car['transmission'] == u_trans:
                score += 4
            
            
            if car['seller_type'] == u_seller:
                score += 5
                
        user_item_matrix[u_idx, c_idx] = score


# algoritm simi

print("3. Se calculează similitudinea...")
item_similarity = cosine_similarity(user_item_matrix.T)

def recommend_items(user_id_index, matrix, similarity, top_k=5):
    user_ratings = matrix[user_id_index]
    scores = user_ratings.dot(similarity)
    
    sum_similarity = np.array([np.abs(similarity).sum(axis=1)])
    with np.errstate(divide='ignore', invalid='ignore'):
        scores = scores / sum_similarity.flatten()
        scores = np.nan_to_num(scores)
    
    # eliminam doar ce e complet nepotrivit
    scores[user_ratings == 0] = -1
    
    top_indices = np.argsort(scores)[::-1][:top_k]
    return top_indices, scores


# rezultate users

target_user_idx = 7 
target_user = users_df.iloc[target_user_idx]

recom_indices, all_scores = recommend_items(target_user_idx, user_item_matrix, item_similarity, top_k=5)

with open("README2.txt", "w", encoding="utf-8") as f:
    header_lines = [
        "\n" + "="*50,
        f"RECOMANDĂRI PENTRU: {target_user['first_name']} {target_user['last_name']}",
        f"Profil: {target_user['budget']} RON | {target_user['fuel_preference']} | {target_user['transmission_preference']} | {target_user['preferred_seller']}",
        "="*50
    ]
    
    for line in header_lines:
        print(line)
        f.write(line + "\n")

    for i, idx in enumerate(recom_indices):
        car = cars_subset.iloc[idx]
        score = all_scores[idx]
        
        lines_to_print = [
            f"{i+1}. {car['name']} ({car['year']})",
            f"   Pret: {car['selling_price']} | {car['fuel']} | {car['transmission']} | {car['seller_type']}",
            f"   Scor Compatibilitate: {score:.4f}",
            "-" * 40
        ]
        
        for line in lines_to_print:
            print(line)
            f.write(line + "\n")

print("\n[INFO] Rezultatele au fost salvate în README2.txt")