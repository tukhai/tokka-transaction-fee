import requests
import os
from rest_framework.views import APIView

from django.db.models import Q
from django.http import JsonResponse

from .models import TransactionRecord, TransactionBatchRecord


class CompareRealtimeData(APIView):
    def get(self, request, *args, **kwargs):
        api_key = os.environ.get('API_KEY', None)
        address = os.environ.get('ADDRESS', None)
        offset = 100   # compare first 100 tnxs
        url = f'https://api.etherscan.io/api?module=account&action=tokentx&address={address}&page=1&offset={offset}&startblock=0&endblock=999999999&sort=desc&apikey={api_key}'
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


class Transaction(APIView):
    def get(self, request, *args, **kwargs):
        txn_hash = request.GET.get('hash')

        transaction = get_transaction(txn_hash)
        timestamp = int(transaction.timestamp.timestamp())
        factor = get_historical_price_by_timestamp('ETHUSDT', timestamp)
        return JsonResponse({'txn_fee_in_usdt': transaction.fee * factor})


def get_transaction(txn_hash):
    try:
        transaction = TransactionRecord.objects.get(hash=txn_hash)
    except TransactionRecord.DoesNotExist:
        transaction = None

    if not transaction:
        try:
            transaction = TransactionBatchRecord.objects.get(hash=txn_hash)
        except TransactionBatchRecord.DoesNotExist:
            transaction = None

    return transaction


def get_historical_price_by_timestamp(symbol, target_timestamp):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1s&startTime={target_timestamp * 1000}&endTime={target_timestamp * 1000}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if data and data[0] and len(data[0]) == 12:
            return float(data[0][4])  # Choose Closing price is at index 4, most suitable for historical analysis
        return None
    return None
