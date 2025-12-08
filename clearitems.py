from recombee_api_client.api_client import RecombeeClient
from recombee_api_client.api_requests import *

client = RecombeeClient(
    'sisteme-de-recomandare-upb-dev',
    'TYn7x2wy7S9bzzMDUXkxbw22QrBTvzXAiCvtKKl0dG9xfaXDpemDpPavgFLaVpyp'
)

# obține lista itemelor (doar ID-uri)
items = client.send(ListItems())

print(f"Am găsit {len(items)} iteme. Le șterg...")

for item_id in items:
    client.send(DeleteItem(item_id))

print("Toate itemele au fost șterse.")
