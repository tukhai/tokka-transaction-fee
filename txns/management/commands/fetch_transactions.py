from django.core.management.base import BaseCommand
import os
import aiohttp
import asyncio
import asyncpg
from datetime import datetime


class Command(BaseCommand):
    help = 'Fetches transactions from Etherscan API'

    async def fetch_transactions(self):
        conn = await asyncpg.connect(
            host='localhost',
            port=5432,
            user=os.environ.get('DATABASE_USER', None),
            password=os.environ.get('DATABASE_PASSWORD', None),
            database=os.environ.get('DATABASE_NAME', None)
        )

        api_key = os.environ.get('API_KEY', None)
        address = os.environ.get('ADDRESS', None)

        latest_id = await conn.fetchval('SELECT block_number FROM transaction_record ORDER BY block_number DESC LIMIT 1')
        url = f'https://api.etherscan.io/api?module=account&action=tokentx&address={address}&page=1&offset=100&startblock={latest_id or 0}&endblock=999999999&sort=desc&apikey={api_key}'

        # offset = 10 # redundant to ensure no data loss
        # url = f'https://api.etherscan.io/api?module=account&action=tokentx&address={address}&page=1&offset={offset}&startblock=0&endblock=999999999&sort=desc&apikey={api_key}'

        async with aiohttp.ClientSession() as session:
            while True:
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
                                INSERT INTO transaction_record (hash, block_number, timestamp, fee)
                                VALUES ($1, $2, $3, $4)
                                ON CONFLICT (hash, timestamp) DO NOTHING
                            ''', transactions)

    def handle(self, *args, **options):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.fetch_transactions())
