import requests
import os
from rest_framework.views import APIView

from django.db.models import Q
from django.http import JsonResponse

from ..models import TransactionRecord


class CompareRealtimeData(APIView):
    def get(self, request, *args, **kwargs):
        api_key = os.environ.get('API_KEY', None)
        address = os.environ.get('ADDRESS', None)
        etherscan_api_url = os.environ.get('ETHERSCAN_API_URL', None)
        offset = 100   # compare first 100 tnxs
        url = f'{etherscan_api_url}?module=account&action=tokentx&address={address}&page=1&offset={offset}&startblock=0&endblock=999999999&sort=desc&apikey={api_key}'
        response = requests.get(url)
        keys_to_check = []
        if response.status_code == 200:
            data = response.json()
            if data['status'] == '1' and data['result']:
                keys_to_check = set([(r['hash'], r['blockNumber']) for r in data['result']])

        query = Q()
        for hash_val, block_num in keys_to_check:
            query |= Q(hash=hash_val, block_number=block_num)

        # Query the database for existing keys
        existing_records = TransactionRecord.objects.filter(query)
        existing_count = existing_records.count()

        # Calculate the percentage of existing records
        total_keys = len(keys_to_check)
        print(existing_count, '___', total_keys)
        percentage_existing = (existing_count / total_keys) * 100 if total_keys > 0 else 0

        return JsonResponse({'percentage_existing': percentage_existing})
