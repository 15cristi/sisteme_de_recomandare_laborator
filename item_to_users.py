from recombee_api_client.api_client import RecombeeClient
from recombee_api_client.api_requests import *

client = RecombeeClient(
    'sisteme-de-recomandare-upb-dev',
    'TYn7x2wy7S9bzzMDUXkxbw22QrBTvzXAiCvtKKl0dG9xfaXDpemDpPavgFLaVpyp'
)

user_id = "00056"  # exemplu

response = client.send(RecommendItemsToUser(
    user_id=user_id,
    count=10,
    scenario="recommend_items_to_user"
))

print("Recomandări pentru user:")
for r in response['recomms']:
    print(r['id'])
