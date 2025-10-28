import json
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd
from bs4 import BeautifulSoup


# citim fisierul tesco_sample.json
with open("tesco_sample.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# extragem numele si descrierea + stergem html-ul
products = []
descriptions = []

for item in data:
    name = item.get("name", "Unknown")
    desc_html = item.get("description", "")
    
    # stergem html
    text = BeautifulSoup(desc_html, "html.parser").get_text(separator=" ")
    # stergem caracterele speciale "spatiu , . : "
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^a-zA-Z0-9 ]', '', text)
    text = text.lower().strip()

    if text:
        products.append(name)
        descriptions.append(text)

# vectorizare text in TF-IDF
vectorizer = TfidfVectorizer(stop_words='english')
tfidf_matrix = vectorizer.fit_transform(descriptions)

# calculul matricei de similaritate cosine
cosine_sim = cosine_similarity(tfidf_matrix, tfidf_matrix)

# identificarea perechilor de produse similare (inclusiv cele identice)
pairs = []

for i in range(len(products)):
    for j in range(i + 1, len(products)):
        sim = cosine_sim[i, j]
        pairs.append((products[i], products[j], sim))

# sortam descrescator similitatea
pairs_sorted = sorted(pairs, key=lambda x: x[2], reverse=True)

# afisam/salvam primele N perechi de produse
top_n = 200

print(f"\nTop {top_n} perechi de produse similare:\n")
for p1, p2, sim in pairs_sorted[:top_n]:
    print(f"- {p1}  ↔  {p2}  ({sim:.4f})")

# salvam in README.txt
with open("README.txt", "w", encoding="utf-8") as f:
    f.write(f"Top {top_n} perechi de produse similare:\n\n")
    for i, (p1, p2, sim) in enumerate(pairs_sorted[:top_n], start=1):
        f.write(f"{i}. {p1}  ↔  {p2}  (similaritate: {sim:.4f})\n")

# salvam matricea de similaritate
df_sim = pd.DataFrame(cosine_sim, index=products, columns=products)
df_sim.to_csv("similarity_matrix.csv")

# top perechi intr-un CSV separat
df_pairs = pd.DataFrame(pairs_sorted, columns=["Produs 1", "Produs 2", "Similaritate"])
df_pairs.to_csv("top_similar_pairs.csv", index=False)

print("\nRezultatele au fost salvate in README.txt si top_similar_pairs.csv")
print("\nMatricea de similaritate (primele 5x5 valori):")
print(df_sim.iloc[:5, :5])
