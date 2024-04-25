from django.core.management.base import BaseCommand
import os
import requests

from web3 import Web3
from ...models import TransactionBatchRecord
from ...tasks import process_transaction


class Command(BaseCommand):
    help = 'Batch decode the actual Uniswap swap price executed for each Txn'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.conn_params = {
            'host': os.environ.get('HOST', 'localhost'),
            'port': os.environ.get('PORT', '5432'),
            'user': os.environ.get('DATABASE_USER', None),
            'password': os.environ.get('DATABASE_PASSWORD', None),
            'database': os.environ.get('DATABASE_NAME', None),
        }
        self.infura_project_id = os.environ.get('INFURA_PROJECT_ID', None)
        self.uniswap_contract_address = os.environ.get('UNISWAP_CONTRACT_ADDRESS', None)

    def decode(self):
        checksum_address = Web3.to_checksum_address(self.uniswap_contract_address)
        uniswap_abi = get_contract_abi(checksum_address)

        objs = TransactionBatchRecord.objects.values_list('hash', 'timestamp').distinct()
        for obj in objs:
            process_transaction.delay(
                obj[0],
                obj[1],
                uniswap_abi,
                self.uniswap_contract_address,
                self.infura_project_id
            )

    def handle(self, *args, **kwargs):
        self.decode()


def get_contract_abi(contract_address):
    api_key = os.environ.get('API_KEY', None)
    etherscan_api_url = os.environ.get('ETHERSCAN_API_URL', None)
    url = f"{etherscan_api_url}?module=contract&action=getabi&address={contract_address}&apikey={api_key}"

    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if data['status'] == '1':  # Check if the request was successful
            return data['result']  # This is the ABI in JSON format
        else:
            raise Exception(f"Error fetching ABI: {data['result']}")
    else:
        response.raise_for_status()
