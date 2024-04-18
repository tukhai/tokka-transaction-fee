import requests
import os
import random
from rest_framework.views import APIView

from django.db.models import Q
from django.http import JsonResponse
from django.core.management import call_command

from ..models import TransactionRecord, TransactionBatchRecord
from ..management.commands.batch_record import Command as BatchCommand


class CompareRealtimeData(APIView):
    def get(self, request, *args, **kwargs):
        api_key = os.environ.get('API_KEY', None)
        address = os.environ.get('ADDRESS', None)
        etherscan_api_url = os.environ.get('ETHERSCAN_API_URL', None)
        offset = 100   # compare first 100 tnxs
        url = f'{etherscan_api_url}?module=account&action=tokentx&address={address}&page=1&offset={offset}&startblock=0&endblock=999999999&sort=desc&apikey={api_key}'
        return JsonResponse(compare(url, TransactionRecord))


class CompareBatchData(APIView):
    def get(self, request, *args, **kwargs):
        start_timestamp = request.GET.get('start_timestamp')
        end_timestamp = request.GET.get('end_timestamp')

        batch_command_obj = BatchCommand()

        api_key = os.environ.get('API_KEY_BATCH', None)
        address = os.environ.get('ADDRESS', None)
        etherscan_api_url = os.environ.get('ETHERSCAN_API_URL', None)

        test_blocks_count = 100
        start_block = batch_command_obj.get_block_number_by_timestamp(start_timestamp, 'before')
        end_block = batch_command_obj.get_block_number_by_timestamp(end_timestamp, 'after')
        random_block = random.randint(start_block, end_block - test_blocks_count)

        url = f'{etherscan_api_url}?module=account&action=tokentx&address={address}&page=1&offset={test_blocks_count * 10}&startblock={random_block}&endblock={random_block + test_blocks_count}&sort=desc&apikey={api_key}'
        return JsonResponse(compare(url, TransactionBatchRecord))


def compare(url, txn_model):
    response = requests.get(url)
    keys_to_check = []
    if response.status_code == 200:
        data = response.json()
        if data['status'] == '1' and data['result']:
            keys_to_check = set([(r['hash'], r['blockNumber']) for r in data['result']])

    query = Q()
    for hash_val, block_num in keys_to_check:
        query |= Q(hash=hash_val, block_number=block_num)

    existing_records = txn_model.objects.filter(query)
    existing_count = existing_records.count()

    total_keys = len(keys_to_check)
    percentage_existing = (existing_count / total_keys) * 100 if total_keys > 0 else 0

    return {
        'existing_count': existing_count,
        'total_count': total_keys,
        'percentage_existing': percentage_existing
    }
