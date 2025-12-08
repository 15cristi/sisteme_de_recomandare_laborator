from recombee_api_client.api_client import RecombeeClient
from recombee_api_client.api_requests import *
import pandas as pd

client = RecombeeClient(
    'sisteme-de-recomandare-upb-dev',
    'TYn7x2wy7S9bzzMDUXkxbw22QrBTvzXAiCvtKKl0dG9xfaXDpemDpPavgFLaVpyp'
)

try:
    df = pd.read_csv('car_data.csv')
    print(f"Dataset încărcat cu succes: {df.shape[0]} rânduri, {df.shape[1]} coloane.")
except Exception as e:
    print("Eroare la citirea fișierului CSV:", e)
    exit()

properties = [
    ('year', 'int'),
    ('selling_price', 'double'),
    ('km_driven', 'double'),
    ('fuel', 'string'),
    ('seller_type', 'string'),
    ('transmission', 'string'),
    ('name', 'string'),
    ('owner', 'string')
]

for name, typ in properties:
    try:
        client.send(AddItemProperty(name, typ))
        print(f"Proprietate adăugată: {name} ({typ})")
    except Exception as e:
        if "already exists" in str(e):
            print(f"Proprietatea '{name}' există deja, ignor.")
        else:
            print(f"Eroare la AddItemProperty '{name}':", e)

for idx, row in df.iterrows():
    
    # AICI se schimbă item_id-ul
    item_id = f"{idx+1:05d}"

    try:
        client.send(AddItem(item_id))
    except Exception as e:
        if "already exists" not in str(e):
            print(f"Eroare la AddItem pentru {item_id}:", e)
            continue

    try:
        client.send(SetItemValues(
            item_id,
            {
                "year": int(row['year']),
                "selling_price": float(row['selling_price']),
                "km_driven": float(row['km_driven']),
                "fuel": str(row['fuel']),
                "seller_type": str(row['seller_type']),
                "transmission": str(row['transmission']),
                "name": str(row['name']),
                "owner": str(row['owner'])
            },
            cascade_create=True
        ))

        if idx % 100 == 0:
            print(f"{idx} mașini adăugate până acum...")

    except Exception as e:
        print(f"Eroare la SetItemValues pentru {item_id}:", e)
