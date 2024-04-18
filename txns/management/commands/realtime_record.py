from django.core.management.base import BaseCommand
import os
import aiohttp
import asyncio
import asyncpg
from datetime import datetime


class Command(BaseCommand):
    help = 'Fetches transactions from Etherscan API'

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
        self.api_key = os.environ.get('API_KEY', None)
        self.address = os.environ.get('ADDRESS', None)

        self.semaphore = asyncio.Semaphore(4)  # Limit to 4 API calls per seconds, max is 5 so leaving some buffer

    async def fetch_transactions(self):
        async with asyncpg.create_pool(**self.conn_params) as conn_pool:
            await self.fetch_all_urls(conn_pool)

    async def fetch_url(self, conn_pool, session, url):
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
                                    INSERT INTO transaction_record (hash, block_number, timestamp, fee)
                                    VALUES ($1, $2, $3, $4)
                                    ON CONFLICT (hash, timestamp) DO NOTHING
                                ''', transactions)

    async def fetch_all_urls(self, conn_pool):
        async with aiohttp.ClientSession() as session:
            while True:
                latest_id = await conn_pool.fetchval('SELECT block_number FROM transaction_record ORDER BY timestamp DESC LIMIT 1')  # as we partition by timestamp, order by timestamp is more efficient
                url = f'{self.etherscane_api_url}?module=account&action=tokentx&address={self.address}&page=1&offset=100&startblock={latest_id or 0}&endblock=999999999&sort=desc&apikey={self.api_key}'
                await self.fetch_url(conn_pool, session, url)

    def handle(self, *args, **options):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.fetch_transactions())
