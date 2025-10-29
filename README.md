# Sistem de recomandare pentru vehicule – Recombee + Kaggle Dataset

Acest proiect implementează un sistem de recomandare bazat pe conținut pentru mașini, utilizând API-ul Recombee și un dataset real de vehicule preluat de pe Kaggle

# Descriere

Proiectul demonstrează cum pot fi importate date reale despre mașini într-o bază de date Recombee pentru a genera recomandări personalizate

## Codul:
- Citește datele dintr-un fișier CSV (car_data.csv).
- Creează schema de proprietăți în Recombee.
- Încarcă fiecare mașină ca un item unic (0001, 0002, ...).
- Atribuie fiecărui item proprietăți descriptive (year, price, fuel, seller_type, etc.).
- Atribuie fiecarui utilizator proprietati precum nume, oras, buget si preferinte.
- Fișierul `tesco_sample.json` conține datele (produsele) folosite pentru calculul similarității.


## Fisierele proiectului:

- car_data.csv – Datasetul original de pe Kaggle, au fost selectate primele 200 masini.

- users.csv – Fisier care contine 30 de utilizatori cu informatii generale si preferinte.

- database.py – Scriptul care incarca datele + proprietatile despre masini in Recombee.

- add_users.py – Scriptul care incarca utilizatorii + proprietatile in Recombee.

- Scriptul `CosineSimilarity.py` realizează recomandări content-based prin calculul similarității cosine dintre descrierile produselor.
