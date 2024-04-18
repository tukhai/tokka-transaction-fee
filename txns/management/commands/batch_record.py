from django.core.management.base import BaseCommand
import os
import requests
import aiohttp
import asyncio
import asyncpg
from datetime import datetime


class Command(BaseCommand):
    help = 'Batch record transactions from Etherscan API for the previous hour'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.conn_params = {
            'host': 'localhost',
            'port': 5432,
            'user': os.environ.get('DATABASE_USER', None),
            'password': os.environ.get('DATABASE_PASSWORD', None),
            'database': os.environ.get('DATABASE_NAME', None)
        }
        self.etherscane_api_url = os.environ.get('ETHERSCAN_API_URL', None)
        self.api_key = os.environ.get('API_KEY_BATCH', None)
        self.address = os.environ.get('ADDRESS', None)

        self.step = 1000  # to ensure that each api call is <10000. Cant loop the pagination because pageNo * offset must be <10000
        self.semaphore = asyncio.Semaphore(4)  # Limit to 4 API calls per seconds, max is 5 so leaving some buffer

    def get_block_number_by_timestamp(self, timestamp, closest):
        response = requests.get(f'{self.etherscane_api_url}?module=block&action=getblocknobytime&timestamp={timestamp}&closest={closest}&apikey={self.api_key}')
        if response.status_code == 200:
            data = response.json()
            if data['status'] == '1' and data['result']:
                return int(data['result'])

    async def fetch_transactions(self, start, end):
        print(datetime.now().strftime("%d-%m-%Y %H:%M:%S"))

        start_block = self.get_block_number_by_timestamp(start, 'before')
        end_block = self.get_block_number_by_timestamp(end, 'after')

        async with asyncpg.create_pool(**self.conn_params) as conn_pool:
            await self.fetch_all_urls(conn_pool, start_block, end_block)

        print(datetime.now().strftime("%d-%m-%Y %H:%M:%S"))

    async def fetch_url(self, conn_pool, session, url):
        completed = False
        while not completed:
            async with self.semaphore:
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
                            async with conn_pool.acquire() as connection:
                                async with connection.transaction():
                                    await connection.executemany('''
                                        INSERT INTO transaction_batch_record (hash, block_number, timestamp, fee)
                                        VALUES ($1, $2, $3, $4)
                                        ON CONFLICT (hash, timestamp) DO NOTHING
                                    ''', transactions)
                            completed = True
                        else:
                            print('data ::', data)
            #         else:
            #             print('response ::', response)

    async def fetch_all_urls(self, conn_pool, start_block, end_block):
        async with aiohttp.ClientSession() as session:
            tasks = []
            for b in range(start_block, end_block, self.step):
                url = f'{self.etherscane_api_url}?module=account&action=tokentx&address={self.address}&startblock={b}&endblock={min(b + self.step - 1, end_block)}&sort=asc&apikey={self.api_key}'
                tasks.append(asyncio.create_task(self.fetch_url(conn_pool, session, url)))
            return await asyncio.gather(*tasks)

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
