from datetime import datetime
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIRequestFactory
from unittest.mock import patch

from ..views import Transaction, get_transaction, get_historical_price_by_timestamp
from ..models import TransactionRecord, TransactionBatchRecord

import json
from dotenv import load_dotenv
load_dotenv()


class TestTransaction(TestCase):
    def setUp(self):
        self.transaction_record = TransactionRecord(
            hash='test_hash_123',
            block_number=19681102,
            timestamp=datetime.fromtimestamp(1672670267),
            fee=0.001
        )
        self.factory = APIRequestFactory()

    def test_transaction_api(self):
        print('Method: test_transaction_api - Test if get_transaction_by_hash API return correct transaction fee in USDT.')
        with patch('txns.models.TransactionRecord.objects.get') as mock_get:
            mock_get.return_value = self.transaction_record

            url = reverse('get_transaction_by_hash')
            request = self.factory.get(url, {'hash': 'test_hash_123'})

            response = Transaction.as_view()(request)

            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)
            self.assertIn('txn_fee_in_usdt', data)
            self.assertEqual(data['txn_fee_in_usdt'], 1.2155799999999999)

    def test_get_transaction_existing_record(self):
        print('Method: test_get_transaction_existing_record - Test in case transaction record exists in DB.')
        with patch('txns.models.TransactionRecord.objects.get') as mock_get:
            mock_get.return_value = self.transaction_record
            result = get_transaction('test_hash_123')
            self.assertEqual(result, self.transaction_record)

    def test_get_transaction_nonexistent_record(self):
        print('Method: test_get_transaction_nonexistent_record - Test in case transaction record does not exists in DB.')
        with patch('txns.models.TransactionRecord.objects.get') as mock_get_record:
            with patch('txns.models.TransactionBatchRecord.objects.get') as mock_get_batch:
                mock_get_record.side_effect = TransactionRecord.DoesNotExist()
                mock_get_batch.side_effect = TransactionBatchRecord.DoesNotExist()
                result = get_transaction('nonexistent_hash')
                self.assertIsNone(result)

    def test_get_historical_price_by_timestamp(self):
        print('Method: test_get_historical_price_by_timestamp - Check if Binance ETH/USDT return correct historical price.')
        price = get_historical_price_by_timestamp('ETHUSDT', 1672666667)
        self.assertEqual(price, 1215.37)
