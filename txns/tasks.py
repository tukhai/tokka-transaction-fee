from .celery import app
from web3 import Web3
from django.db import connection


# @shared_task
@app.task()
def process_transaction(hash, timestamp, uniswap_abi, uniswap_contract_address, infura_project_id):
    w3 = Web3(Web3.HTTPProvider(f'https://mainnet.infura.io/v3/{infura_project_id}'))
    checksum_address = Web3.to_checksum_address(uniswap_contract_address)
    contract = w3.eth.contract(address=checksum_address, abi=uniswap_abi)

    try:
        receipt = w3.eth.get_transaction_receipt(hash)
        swap_prices = []
        for log in receipt.logs:
            try:
                event_data = contract.events.Swap().process_log(log)
                swap_prices.append(calc_executed_price(event_data['args']['sqrtPriceX96']))
            except Exception as e:
                continue
        price_str = ', '.join(map(str, swap_prices))

        with connection.cursor() as cursor:
            cursor.execute('''
                INSERT INTO transaction_uniswap_price (hash, timestamp, price)
                VALUES (%s, %s, %s)
                ON CONFLICT (hash, timestamp) DO NOTHING
            ''', (hash, timestamp, price_str))
    except Exception as e:
        print(f"Error processing transaction {hash}: {e}")


def calc_executed_price(sqrt_price_x96):
    return (sqrt_price_x96 / (2 ** 96)) ** 2
