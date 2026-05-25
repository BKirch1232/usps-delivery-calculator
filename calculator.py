import math
from datetime import datetime, timedelta

class USPSCalculator:
    def __init__(self):
        # Base expected days and standard deviations (uncertainty) for USPS services
        self.services = {
            "Express": {"base_days": 1, "base_sigma": 0.2, "guaranteed": True},
            "Priority": {"base_days": 2, "base_sigma": 0.7, "guaranteed": False},
            "Ground": {"base_days": 4, "base_sigma": 1.2, "guaranteed": False},
            
            # First-Class Letter: High variance due to bulk bin sorting and lack of prioritization
            "First-Class Letter": {"base_days": 3, "base_sigma": 1.8, "guaranteed": False},
            
            # eBay Standard Envelope: Physically the same as First-Class, just with IMb tracking
            "eBay Standard": {"base_days": 3, "base_sigma": 1.8, "guaranteed": False},
            
            # Media Mail: Lowest priority, space-available routing, subject to inspection
            "Media Mail": {"base_days": 4, "base_sigma": 2.5, "guaranteed": False}
        }

    def estimate_zone(self, zip_from, zip_to):
        """Estimate USPS Zone (1-8) based on the first digit of the zip codes."""
        diff = abs(int(str(zip_from)[0]) - int(str(zip_to)[0]))
        return min(max(diff, 1), 8) # Keeps zone between 1 and 8

    def calculate_confidence(self, target_days, mu, sigma):
        """Calculates probability using the Normal Distribution CDF."""
        if sigma <= 0:
            return 100.0 if mu <= target_days else 0.0
        
        # Calculates area under the curve to the left of the target days
        probability = 0.5 * (1 + math.erf((target_days - mu) / (sigma * math.sqrt(2))))
        return max(min(probability * 100, 100.0), 0.0)

    def get_delivery_estimate(self, zip_from, zip_to, service_name, ship_date, weather_delay_days=0, detour_delay_days=0):
        if service_name not in self.services:
            raise ValueError(f"Invalid service. Choose from: {', '.join(self.services.keys())}")

        service = self.services[service_name]
        zone = self.estimate_zone(zip_from, zip_to)
        
        # 1. Calculate Target (Quoted) Days 
        # Media Mail scales poorly with distance; other services scale normally
        zone_multiplier = 0.4 if service_name == "Media Mail" else 0.25
        target_days = service["base_days"] + (zone * zone_multiplier)
        target_days = math.ceil(target_days)
        
        # 2. Calculate the Actual Mean (mu) and Variance (sigma)
        mu = target_days + weather_delay_days + detour_delay_days
        
        # Letter-class and Media Mail have higher inherent variance; distance makes it worse
        sigma = service["base_sigma"] + (zone * 0.15) + (weather_delay_days * 0.5) + (detour_delay_days * 0.4)

        # 3. Calculate Confidence Percentage
        confidence = self.calculate_confidence(target_days, mu, sigma)
        
        # 4. Calculate Expected Delivery Date (Skipping Sundays)
        delivery_date = ship_date
        days_to_add = math.ceil(mu)
        
        while days_to_add > 0:
            delivery_date += timedelta(days=1)
            if delivery_date.weekday() != 6: # Skip Sundays
                days_to_add -= 1

        return {
            "Service": service_name,
            "Origin -> Dest Zip": f"{zip_from} -> {zip_to}",
            "Est. Zone": zone,
            "Quoted Target Days": target_days,
            "Adjusted Expected Days": round(mu, 2),
            "Estimated Delivery Date": delivery_date.strftime("%Y-%m-%d (%A)"),
            "Confidence Level": f"{confidence:.2f}%"
        }

# ==========================================
# Run the Calculator
# ==========================================
if __name__ == "__main__":
    calc = USPSCalculator()
    ship_date = datetime(2026, 6, 1) # Monday, June 1, 2026
    
    # Test across the country (Zone 8)
    print("--- CROSS COUNTRY COMPARISON (Zone 8, Clear Weather) ---")
    
    services_to_test = ["Priority", "First-Class Letter", "eBay Standard", "Media Mail"]
    
    for s in services_to_test:
        result = calc.get_delivery_estimate(10001, 90210, s, ship_date)
        print(f"\n{result['Service'].upper()}")
        print(f"Target: {result['Quoted Target Days']} days | Expected: {result['Adjusted Expected Days']} days")
        print(f"Delivery: {result['Estimated Delivery Date']}")
        print(f"Confidence of hitting Target: {result['Confidence Level']}")
