from unittest.mock import patch
from django.test import TestCase
from django.urls import reverse


class DeliveryOrderPriceViewTestCase(TestCase):

    # Setup mock data for tests
    def setUp(self):
        self.url = reverse('delivery-order-price')
        self.static_data = {
            'venue_raw': {
                'location': {
                    'coordinates': [13.4100, 52.5300]  # Venue location: Berlin (offset slightly)
                }
            }
        }
        self.dynamic_data = {
            'venue_raw': {
                'delivery_specs': {
                    'order_minimum_no_surcharge': 500,
                    'delivery_pricing': {
                        'base_price': 2.50,
                        'distance_ranges': [
                            {'min': 0, 'max': 500, 'a': 1, 'b': 0.2},
                            {'min': 500, 'max': 1000, 'a': 1.5, 'b': 0.15},
                            {'min': 1000, 'max': 0, 'a': 2, 'b': 0.1}
                        ]
                    }
                }
            }
        }

    @patch('delivery_price_calculator.views.DeliveryOrderPriceView.get_venue_static_data')
    @patch('delivery_price_calculator.views.DeliveryOrderPriceView.get_venue_dynamic_data')
    def test_valid_request(self, mock_get_dynamic, mock_get_static):
        """Test valid inputs resulting in successful delivery fee calculation."""
        # Mock the responses
        mock_get_static.return_value = self.static_data
        mock_get_dynamic.return_value = self.dynamic_data

        # Request data
        response = self.client.get(self.url, {
            'venue_slug': 'home-assignment-venue-berlin',
            'cart_value': 200,  # Trigger surcharge of 300
            'user_lat': 13.4100,  # User location: Berlin
            'user_lon': 52.5300
        })

        # Assertions
        self.assertEqual(response.status_code, 200)  # Success response
        response_data = response.json()

        # Check if the response contains the expected keys
        self.assertIn('total_price', response_data)
        self.assertIn('small_order_surcharge', response_data)
        self.assertIn('delivery', response_data)

        # Check response values
        small_order_surcharge = response_data['small_order_surcharge']
        delivery_fee = response_data['delivery']['fee']
        total_price = response_data['total_price']

        # Validate small order surcharge
        self.assertEqual(small_order_surcharge, 300)  # 500 - 200

        # Validate total price
        expected_total_price = 200 + 300 + delivery_fee
        self.assertEqual(total_price, expected_total_price)

        # Debugging outputs for troubleshooting
        print(f"Static Data: {self.static_data}")
        print(f"Dynamic Data: {self.dynamic_data}")
        print(f"Response Data: {response_data}")

    @patch('delivery_price_calculator.views.DeliveryOrderPriceView.get_venue_static_data')
    @patch('delivery_price_calculator.views.DeliveryOrderPriceView.get_venue_dynamic_data')
    def test_delivery_not_possible(self, mock_get_dynamic, mock_get_static):
        """Test when delivery distance exceeds maximum allowed range."""
        mock_get_static.return_value = self.static_data
        mock_get_dynamic.return_value = self.dynamic_data

        # User far away from venue
        response = self.client.get(self.url, {
            'venue_slug': 'home-assignment-venue-berlin',
            'cart_value': 800,
            'user_lat': 8.6821,  # Frankfurt
            'user_lon': 50.0000
        })

        # Assertions
        self.assertEqual(response.status_code, 400)  # Bad request
        response_data = response.json()
        self.assertIn('error', response_data)
        self.assertEqual(response_data['error'], 'Delivery is not possible due to distance.')

        # Debugging outputs
        print(f"Static Data: {self.static_data}")
        print(f"Dynamic Data: {self.dynamic_data}")
        print(f"Response Data: {response_data}")

    @patch('delivery_price_calculator.views.DeliveryOrderPriceView.get_venue_static_data')
    @patch('delivery_price_calculator.views.DeliveryOrderPriceView.get_venue_dynamic_data')
    def test_small_order_surcharge(self, mock_get_dynamic, mock_get_static):
        """Test when cart value is below the minimum order value."""
        mock_get_static.return_value = self.static_data
        mock_get_dynamic.return_value = self.dynamic_data

        # Request data
        response = self.client.get(self.url, {
            'venue_slug': 'home-assignment-venue-berlin',
            'cart_value': 100,  # Below minimum surcharge threshold
            'user_lat': 13.4100,
            'user_lon': 52.5300
        })

        # Assertions
        self.assertEqual(response.status_code, 200)  # Success response
        response_data = response.json()

        # Check small order surcharge
        small_order_surcharge = response_data['small_order_surcharge']
        self.assertEqual(small_order_surcharge, 400)  # 500 - 100

        # Debugging outputs
        print(f"Static Data: {self.static_data}")
        print(f"Dynamic Data: {self.dynamic_data}")
        print(f"Response Data: {response_data}")
