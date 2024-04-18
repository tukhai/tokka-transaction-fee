import requests
from rest_framework.views import APIView

from django.http import JsonResponse

from ..models import TransactionRecord, TransactionBatchRecord


class Transaction(APIView):
    def get(self, request, *args, **kwargs):
        txn_hash = request.GET.get('hash')

        transaction = get_transaction(txn_hash)
        if transaction is None:
            return JsonResponse({'message': 'transaction hash does not exist!'})

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
