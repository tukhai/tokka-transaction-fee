import requests
import os
from rest_framework.views import APIView

from django.http import JsonResponse

from web3 import Web3


class SwapPrice(APIView):
    def get(self, request, *args, **kwargs):
        txn_hash = request.GET.get('hash')

        infura_project_id = os.environ.get('INFURA_PROJECT_ID', None)
        w3 = Web3(Web3.HTTPProvider(f'https://mainnet.infura.io/v3/{infura_project_id}'))
        uniswap_contract_address = os.environ.get('UNISWAP_CONTRACT_ADDRESS', None)

        checksum_address = Web3.to_checksum_address(uniswap_contract_address)
        uniswap_abi = get_contract_abi(checksum_address)
        contract = w3.eth.contract(address=checksum_address, abi=uniswap_abi)

        receipt = w3.eth.get_transaction_receipt(txn_hash)

        swap_prices = []
        for log in receipt.logs:
            try:
                event_data = contract.events.Swap().process_log(log)
                swap_prices.append(calc_executed_price(event_data['args']['sqrtPriceX96']))
            except Exception as e:
                print(e)
                continue

        return JsonResponse({'swap_prices': swap_prices})


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


def calc_executed_price(sqrt_price_x96):
    return (sqrt_price_x96 / (2 ** 96)) ** 2