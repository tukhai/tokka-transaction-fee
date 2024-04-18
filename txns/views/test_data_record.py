import requests
import os
import random
from rest_framework.views import APIView

from django.db.models import Q
from django.http import JsonResponse
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from ..models import TransactionRecord, TransactionBatchRecord
from ..management.commands.batch_record import Command as BatchCommand


class CompareRealtimeData(APIView):
    @swagger_auto_schema(
        responses={
            200: openapi.Response("Realtime Testing Response.", schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'existing_count': openapi.Schema(type=openapi.TYPE_INTEGER, description='No.of txns found in realtime record.', example=49),
                    'total_count': openapi.Schema(type=openapi.TYPE_INTEGER, description='No.of most recent txns we take as sample (hardcoded as 100), using Etherscan API.', example=49),
                    'percentage_existing': openapi.Schema(type=openapi.TYPE_NUMBER, description='Percentage of txns found / sample.', example=100),
                }
            )),
            404: "Not found.",
        }
    )
    def get(self, request, *args, **kwargs):
        """
        Run this API to Test how well realtime record can sync with Txns data on Etherscan.
        This API will query the most recent 100 records (equivalent to around 50 txns) from Etherscan, and check if our Realtime TimescaleDB has these records.

        As tested, most of the time the percentage is 100%, meaning there's almost no delay between Etherscan & our DB.
        (the latency is less than the programmatical testing speed)
        """
        api_key = os.environ.get('API_KEY', None)
        address = os.environ.get('ADDRESS', None)
        etherscan_api_url = os.environ.get('ETHERSCAN_API_URL', None)
        offset = 100   # compare first 100 tnxs
        url = f'{etherscan_api_url}?module=account&action=tokentx&address={address}&page=1&offset={offset}&startblock=0&endblock=999999999&sort=desc&apikey={api_key}'
        return JsonResponse({
            'status': 'success',
            'message': 'Realtime Record Data Test completed!',
            'data': compare(url, TransactionRecord)
        })


class CompareBatchData(APIView):
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('start_timestamp', openapi.IN_QUERY, description='Start timestamp of the batched time range.', type=openapi.TYPE_INTEGER, example=1704105600),
            openapi.Parameter('end_timestamp', openapi.IN_QUERY, description='Start timestamp of the batched time range.', type=openapi.TYPE_INTEGER, example=1706784000),
        ],
        responses={
            200: openapi.Response("Batch Testing Response.", schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'existing_count': openapi.Schema(type=openapi.TYPE_INTEGER, description='No.of txns found in batch record.', example=44),
                    'total_count': openapi.Schema(type=openapi.TYPE_INTEGER, description='No.of txns in sample.', example=44),
                    'percentage_existing': openapi.Schema(type=openapi.TYPE_NUMBER, description='Percentage of txns found / sample.', example=100),
                }
            )),
            404: "Not found.",
        }
    )
    def get(self, request, *args, **kwargs):
        """
        Input a time range (start_timestamp and end_timestamp) that you have run batch record.
        This API will select random samples of transactions within the time range, to see if they're available in batch record.
        """
        start_timestamp = request.query_params.get('start_timestamp', '')
        end_timestamp = request.query_params.get('end_timestamp', '')

        batch_command_obj = BatchCommand()

        api_key = os.environ.get('API_KEY_BATCH', None)
        address = os.environ.get('ADDRESS', None)
        etherscan_api_url = os.environ.get('ETHERSCAN_API_URL', None)

        test_blocks_count = 100
        start_block = batch_command_obj.get_block_number_by_timestamp(start_timestamp, 'before')
        end_block = batch_command_obj.get_block_number_by_timestamp(end_timestamp, 'after')
        random_block = random.randint(start_block, end_block - test_blocks_count)

        url = f'{etherscan_api_url}?module=account&action=tokentx&address={address}&page=1&offset={test_blocks_count * 10}&startblock={random_block}&endblock={random_block + test_blocks_count}&sort=desc&apikey={api_key}'
        return JsonResponse({
            'status': 'success',
            'message': 'Batch Record Data Test completed!',
            'data': compare(url, TransactionBatchRecord)
        })


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
