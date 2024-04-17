from django.core.management.base import BaseCommand
import os
import requests
import aiohttp
import asyncio
import asyncpg
from datetime import datetime


class Command(BaseCommand):
    help = 'Batch record transactions from Etherscan API for the previous hour'

    def get_block_number_by_timestamp(self, timestamp, closest):
        ETHERSCAN_API_URL = 'https://api.etherscan.io/api'
        api_key = os.environ.get('API_KEY_BATCH', None)

        response = requests.get(f'{ETHERSCAN_API_URL}?module=block&action=getblocknobytime&timestamp={timestamp}&closest={closest}&apikey={api_key}')
        if response.status_code == 200:
            data = response.json()
            if data['status'] == '1' and data['result']:
                return int(data['result'])

    async def fetch_transactions(self, start, end):
        print(datetime.now().strftime("%d-%m-%Y %H:%M:%S"))
        conn = await asyncpg.connect(
            host='localhost',
            port=5432,
            user=os.environ.get('DATABASE_USER', None),
            password=os.environ.get('DATABASE_PASSWORD', None),
            database=os.environ.get('DATABASE_NAME', None)
        )

        start_block = self.get_block_number_by_timestamp(start, 'before')
        end_block = self.get_block_number_by_timestamp(end, 'after')
        step = 1000  # to ensure that each api call is <10000. Cant loop the pagination because pageNo * offset must be <10000

        api_key = os.environ.get('API_KEY_BATCH', None)
        address = os.environ.get('ADDRESS', None)

        async with aiohttp.ClientSession() as session:
            for b in range(start_block, end_block, step):
                url = f'https://api.etherscan.io/api?module=account&action=tokentx&address={address}&startblock={b}&endblock={min(b + step - 1, end_block)}&sort=asc&apikey={api_key}'
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data['status'] == '1' and data['result']:
                            transactions = [
                                (
                                    txn['hash'],
                                    int(txn['blockNumber']),
                                    datetime.fromtimestamp(float(txn['timeStamp'])),
                                    int(txn['gasPrice']) * int(txn['gasUsed']) * pow(10, -18)
                                ) for txn in data['result']
                            ]
                            await conn.executemany('''
                                INSERT INTO transaction_batch_record (hash, block_number, timestamp, fee)
                                VALUES ($1, $2, $3, $4)
                                ON CONFLICT (hash, timestamp) DO NOTHING
                            ''', transactions)
        print(datetime.now().strftime("%d-%m-%Y %H:%M:%S"))

    def add_arguments(self, parser):
        parser.add_argument('start_timestamp', type=int, help='Start timestamp')
        parser.add_argument('end_timestamp', type=int, help='End timestamp')

    def handle(self, *args, **kwargs):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(
            self.fetch_transactions(
                kwargs['start_timestamp'], kwargs['end_timestamp']
            )
        )
