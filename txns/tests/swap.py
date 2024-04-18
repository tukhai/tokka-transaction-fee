from django.test import TestCase
from unittest.mock import patch
from django.urls import reverse
from rest_framework.test import APIRequestFactory
import json

from ..views import SwapPrice, get_contract_abi, calc_executed_price

import os
from dotenv import load_dotenv
load_dotenv()


class TestSwapPrice(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    def test_swap_price_api(self):
        print('Method: test_swap_price_api - Test if get_swap_price API return correct Uniswap V3 swap price.')
        with patch.dict('os.environ', {
            'INFURA_PROJECT_ID': os.environ.get('INFURA_PROJECT_ID'),
            'UNISWAP_CONTRACT_ADDRESS': os.environ.get('UNISWAP_CONTRACT_ADDRESS')
        }):
            url = reverse('get_swap_price')
            request = self.factory.get(url, {'hash': os.environ.get('TEST_TRANSACTION_HASH')})

            response = SwapPrice.as_view()(request)

            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)
            self.assertIn('swap_prices', data)
            self.assertEqual(data['swap_prices'], [822849076.5350317])

    @patch('requests.get')
    def test_get_contract_abi(self, mock_requests_get):
        print('Method: test_get_contract_abi - Check if the contract ABI obtained is correct.')
        mock_requests_get.return_value.status_code = 200
        mock_requests_get.return_value.json.return_value = {
            'status': '1',
            'result': 'ABI JSON'
        }

        abi = get_contract_abi('contract_address')
        self.assertEqual(abi, 'ABI JSON')

    def test_calc_executed_price(self):
        print('Method: test_calc_executed_price - Check if sqrt price x96 is converted correctly into executed price.')
        sqrt_price_x96 = 123
        result = calc_executed_price(sqrt_price_x96)
        self.assertAlmostEqual(result, 2.044055672905246 * (10 ** -38))
