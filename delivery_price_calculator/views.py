from django.http import JsonResponse
from django.views import View
import math
import requests

# Utility Functions
def calculate_distance(user_lat, user_lon, venue_lat, venue_lon):
    """
    Calculate the distance in meters between two geographic coordinates
    using the Haversine formula.
    """
    R = 6371  # Earth's radius in kilometers
    phi1 = math.radians(user_lat)
    phi2 = math.radians(venue_lat)
    delta_phi = math.radians(venue_lat - user_lat)
    delta_lambda = math.radians(venue_lon - user_lon)

    a = (math.sin(delta_phi / 2) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    distance_km = R * c
    return round(distance_km * 1000)  # Convert to meters


def calculate_small_order_surcharge(cart_value, minimum_for_free_delivery):
    """
    Calculate the surcharge for small orders if the cart value
    is below the minimum threshold for free delivery.
    """
    return max(0, minimum_for_free_delivery - cart_value)


def calculate_delivery_fee(distance, base_price, distance_tiers):
    """
    Calculate the delivery fee based on distance and predefined pricing tiers.
    """
    for tier in distance_tiers:
        if tier['max'] == 0 or tier['min'] <= distance < tier['max']:
            return base_price + tier['a'] + round(tier['b'] * distance / 10)
    return None  # Delivery not available for the distance


# Main View
class DeliveryOrderPriceView(View):
    """
    API endpoint to calculate the total order price, including delivery fee and surcharges.
    """
    def get(self, request, *args, **kwargs):
        try:
            # Input Validation and Parsing
            venue_slug = request.GET.get('venue_slug')
            cart_value = request.GET.get('cart_value')
            user_lat = request.GET.get('user_lat')
            user_lon = request.GET.get('user_lon')

            if not venue_slug or cart_value is None or user_lat is None or user_lon is None:
                return JsonResponse({'error': 'Missing required parameters'}, status=400)

            cart_value = int(cart_value)
            user_lat = float(user_lat)
            user_lon = float(user_lon)

            # Fetch Venue Data
            static_data = self.get_venue_static_data(venue_slug)
            dynamic_data = self.get_venue_dynamic_data(venue_slug)

            venue_lat, venue_lon = static_data['venue_raw']['location']['coordinates']

            # Calculate Delivery Distance
            distance = calculate_distance(user_lat, user_lon, venue_lat, venue_lon)

            # Validate Delivery Distance
            distance_ranges = dynamic_data['venue_raw']['delivery_specs']['delivery_pricing']['distance_ranges']
            max_distance_allowed = distance_ranges[-1]['min']  # Use 'min' of the last tier as the maximum distance
            if distance >= max_distance_allowed:
                return JsonResponse({
                    'error': 'Delivery is not possible due to distance.',
                    'distance': distance
                }, status=400)

            # Calculate Charges
            min_cart_for_no_surcharge = dynamic_data['venue_raw']['delivery_specs']['order_minimum_no_surcharge']
            small_order_surcharge = calculate_small_order_surcharge(cart_value, min_cart_for_no_surcharge)

            base_price = dynamic_data['venue_raw']['delivery_specs']['delivery_pricing']['base_price']
            delivery_fee = calculate_delivery_fee(distance, base_price, distance_ranges)

            if delivery_fee is None:
                return JsonResponse({'error': 'Delivery is not possible due to distance.'}, status=400)

            # Calculate Total Price
            total_price = cart_value + small_order_surcharge + delivery_fee

            # Response Data
            return JsonResponse({
                "total_price": total_price,
                "small_order_surcharge": small_order_surcharge,
                "cart_value": cart_value,
                "delivery": {
                    "fee": delivery_fee,
                    "distance": distance
                }
            })

        except ValueError:
            return JsonResponse({'error': 'Invalid input values'}, status=400)
        except requests.RequestException:
            return JsonResponse({'error': 'Failed to fetch data from the API'}, status=500)
        except Exception:
            return JsonResponse({'error': 'An unexpected error occurred'}, status=500)

    def get_venue_static_data(self, venue_slug):
        """
        Fetch the static details of the venue from the API.
        """
        url = f"https://consumer-api.development.dev.woltapi.com/home-assignment-api/v1/venues/{venue_slug}/static"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()

    def get_venue_dynamic_data(self, venue_slug):
        """
        Fetch the dynamic details of the venue from the API.
        """
        url = f"https://consumer-api.development.dev.woltapi.com/home-assignment-api/v1/venues/{venue_slug}/dynamic"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
