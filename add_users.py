from recombee_api_client.api_client import RecombeeClient
from recombee_api_client.api_requests import *
import pandas as pd

# Conectare la Recombee
client = RecombeeClient(
    'sisteme-de-recomandare-upb-dev',
    'TYn7x2wy7S9bzzMDUXkxbw22QrBTvzXAiCvtKKl0dG9xfaXDpemDpPavgFLaVpyp'
)

# Citire fisier CSV cu utilizatori
df = pd.read_csv('users.csv')
print(f"{df.shape[0]} utilizatori incarcati din fisierul CSV.")

# Proprietati pentru utilizatori
user_properties = [
    ('first_name', 'string'),
    ('last_name', 'string'),
    ('age', 'int'),
    ('city', 'string'),
    ('budget', 'double'),
    ('fuel_preference', 'string'),
    ('transmission_preference', 'string'),
    ('preferred_seller', 'string')
]

# Adaugare proprietati in Recombee
for name, typ in user_properties:
    try:
        client.send(AddUserProperty(name, typ))
        print(f"Proprietate adaugata: {name} ({typ})")
    except Exception as e:
        if "already exists" in str(e):
            print(f"Proprietatea '{name}' exista deja, o ignoram.")
        else:
            print(f"Eroare la adaugarea proprietatii '{name}':", e)

# Adaugare sau actualizare utilizatori
for idx, row in df.iterrows():
    user_id = f"{int(row['id']):05d}"  # Format id 00001

    # Incearca sa adauge utilizatorul, ignora daca exista deja
    try:
        client.send(AddUser(user_id))
    except Exception as e:
        if "already exists" in str(e):
            print(f"Userul {user_id} exista deja, il actualizam.")
        else:
            print(f"Eroare la AddUser pentru {user_id}: {e}")
            continue

    # Setare valori pentru utilizator (creeaza sau actualizeaza)
    try:
        client.send(SetUserValues(
            user_id,
            {
                "first_name": row['first_name'],
                "last_name": row['last_name'],
                "age": int(row['age']),
                "city": row['city'],
                "budget": float(row['budget']),
                "fuel_preference": row['fuel_preference'],
                "transmission_preference": row['transmission_preference'],
                "preferred_seller": row['preferred_seller']

            },
            cascade_create=True
        ))
    except Exception as e:
        print(f"Eroare la SetUserValues pentru {user_id}: {e}")

print("\nToti utilizatorii au fost adaugati sau actualizati cu succes in Recombee.")
