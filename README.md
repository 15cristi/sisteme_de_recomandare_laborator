# Sistem de recomandare pentru vehicule – Recombee + Kaggle Dataset

Acest proiect implementează un sistem de recomandare bazat pe conținut pentru mașini, utilizând API-ul Recombee și un dataset real de vehicule preluat de pe Kaggle

# Descriere

Proiectul demonstrează cum pot fi importate date reale despre mașini într-o bază de date Recombee pentru a genera recomandări personalizate

Codul:
- Citește datele dintr-un fișier CSV (car_data.csv).
- Creează schema de proprietăți în Recombee.
- Încarcă fiecare mașină ca un item unic (0001, 0002, ...).
- Atribuie fiecărui item proprietăți descriptive (year, price, fuel, seller_type, etc.).

- Car_data_csv - Datasetul original de pe Kaggle, am luat primele 200 itemi
- Database.py - Scriptul care încarcă datele în Recombee
