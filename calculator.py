import streamlit as st
import math
from datetime import datetime, timedelta

class USPSCalculator:
    def __init__(self):
        # Base expected days and standard deviations (uncertainty) for USPS services
        self.services = {
            "Express": {"base_days": 1, "base_sigma": 0.2, "guaranteed": True},
            "Priority": {"base_days": 2, "base_sigma": 0.7, "guaranteed": False},
            "Ground": {"base_days": 4, "base_sigma": 1.2, "guaranteed": False},
            "First-Class Letter": {"base_days": 3, "base_sigma": 1.8, "guaranteed": False},
            "eBay Standard": {"base_days": 3, "base_sigma": 1.8, "guaranteed": False},
            "Media Mail": {"base_days": 4, "base_sigma": 2.5, "guaranteed": False}
        }

    def estimate_zone(self, zip_from, zip_to):
        """Estimate USPS Zone (1-8) based on the first digit of the zip codes."""
        diff = abs(int(str(zip_from)[0]) - int(str(zip_to)[0]))
        return min(max(diff, 1), 8)

    def calculate_confidence(self, target_days, mu, sigma):
        """Calculates probability using the Normal Distribution CDF."""
        if sigma <= 0:
            return 100.0 if mu <= target_days else 0.0
        probability = 0.5 * (1 + math.erf((target_days - mu) / (sigma * math.sqrt(2))))
        return max(min(probability * 100, 100.0), 0.0)

    def get_delivery_estimate(self, zip_from, zip_to, service_name, ship_date, weather_delay_days=0.0, detour_delay_days=0.0):
        service = self.services[service_name]
        zone = self.estimate_zone(zip_from, zip_to)
        
        zone_multiplier = 0.4 if service_name == "Media Mail" else 0.25
        target_days = math.ceil(service["base_days"] + (zone * zone_multiplier))
        
        mu = target_days + weather_delay_days + detour_delay_days
        sigma = service["base_sigma"] + (zone * 0.15) + (weather_delay_days * 0.5) + (detour_delay_days * 0.4)

        confidence = self.calculate_confidence(target_days, mu, sigma)
        
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
# STREAMLIT WEB INTERFACE
# ==========================================
st.set_page_config(page_title="USPS Calculator", page_icon="📦")

st.title("📦 USPS Statistical Delivery Calculator")
st.write("Calculate realistic delivery probabilities based on standard variances and routing.")

# Create two columns for a clean layout
col1, col2 = st.columns(2)

with col1:
    zip_from = st.text_input("Origin Zip Code", value="10001", max_chars=5)
    service_name = st.selectbox("Service Type", ["Priority", "Express", "Ground", "First-Class Letter", "eBay Standard", "Media Mail"])
    weather_delay = st.number_input("Weather Delay (Days)", min_value=0.0, value=0.0, step=0.5)

with col2:
    zip_to = st.text_input("Destination Zip Code", value="90210", max_chars=5)
    ship_date = st.date_input("Shipment Date")
    detour_delay = st.number_input("Detour/Routing Delay (Days)", min_value=0.0, value=0.0, step=0.5)

# Calculate Button
if st.button("Calculate Delivery Expectation", type="primary"):
    if len(zip_from) > 0 and len(zip_to) > 0 and zip_from[0].isdigit() and zip_to[0].isdigit():
        calc = USPSCalculator()
        result = calc.get_delivery_estimate(
            zip_from, zip_to, service_name, ship_date, weather_delay, detour_delay
        )
        
        st.divider()
        st.subheader("📊 Delivery Projection")
        
        # Display large metrics
        metric_col1, metric_col2, metric_col3 = st.columns(3)
        metric_col1.metric("USPS Quoted Target", f"{result['Quoted Target Days']} days")
        metric_col2.metric("Adjusted Expected", f"{result['Adjusted Expected Days']} days")
        metric_col3.metric("Confidence Level", result['Confidence Level'])
        
        st.success(f"**Estimated Delivery Date:** {result['Estimated Delivery Date']}")
        st.caption(f"Routing Data: {result['Origin -> Dest Zip']} | Estimated Shipping Zone: {result['Est. Zone']}")
    else:
        st.error("Please enter valid starting digits for your Zip Codes.")
