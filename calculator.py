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

    def assess_route_risks(self, zip_from, zip_to, ship_date, zone):
        """Automatically estimates weather and routing delays based on geography and seasonality."""
        month = ship_date.month
        from_prefix = int(str(zip_from)[0])
        to_prefix = int(str(zip_to)[0])
        
        weather_delay = 0.0
        risk_factors = []
        
        # Winter risks (Dec-Mar) for Northeast (0-2) and Midwest (5-7)
        if month in [12, 1, 2, 3] and (from_prefix in [0,1,2,5,6,7] or to_prefix in [0,1,2,5,6,7]):
            weather_delay += 0.5 + (zone * 0.1)
            risk_factors.append("❄️ Winter Season Routing Risk")
            
        # Hurricane/Summer Storm risks (Aug-Oct) for South (3-4)
        if month in [8, 9, 10] and (from_prefix in [3,4] or to_prefix in [3,4]):
            weather_delay += 0.4 + (zone * 0.05)
            risk_factors.append("🌪️ Late Summer Storm Risk")
            
        # Baseline Detour Risk (Distance based)
        # Packages crossing many zones have a naturally higher risk of misrouting
        detour_delay = (zone * 0.15)
        if zone >= 5:
            risk_factors.append("🛣️ Long-Distance Hub Transfer Risk")
            
        if not risk_factors:
            risk_factors.append("✅ Clear Seasonal Routing expected")
            
        return round(weather_delay, 2), round(detour_delay, 2), risk_factors

    def calculate_confidence(self, target_days, mu, sigma):
        """Calculates probability using the Normal Distribution CDF."""
        if sigma <= 0:
            return 100.0 if mu <= target_days else 0.0
        probability = 0.5 * (1 + math.erf((target_days - mu) / (sigma * math.sqrt(2))))
        return max(min(probability * 100, 100.0), 0.0)

    def get_delivery_estimate(self, zip_from, zip_to, service_name, ship_date):
        service = self.services[service_name]
        zone = self.estimate_zone(zip_from, zip_to)
        
        # 1. Calculate Target Quoted Days
        zone_multiplier = 0.4 if service_name == "Media Mail" else 0.25
        target_days = math.ceil(service["base_days"] + (zone * zone_multiplier))
        
        # 2. Automatically assess route risks instead of asking the user
        weather_delay, detour_delay, risk_factors = self.assess_route_risks(zip_from, zip_to, ship_date, zone)
        
        # 3. Calculate Mean (mu) and Variance (sigma)
        mu = target_days + weather_delay + detour_delay
        sigma = service["base_sigma"] + (zone * 0.15) + (weather_delay * 0.5) + (detour_delay * 0.4)

        # 4. Calculate Confidence and Final Date
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
            "Confidence Level": f"{confidence:.2f}%",
            "Risk Factors": risk_factors
        }

# ==========================================
# STREAMLIT WEB INTERFACE
# ==========================================
st.set_page_config(page_title="USPS Calculator", page_icon="📦")

st.title("📦 USPS Statistical Delivery Calculator")
st.write("Calculate realistic delivery probabilities. Weather and routing delays are now automatically estimated based on geography, distance, and seasonality.")

# Cleaned up layout (removed the manual delay inputs)
col1, col2 = st.columns(2)

with col1:
    zip_from = st.text_input("Origin Zip Code", value="10001", max_chars=5)
    service_name = st.selectbox("Service Type", ["Priority", "Express", "Ground", "First-Class Letter", "eBay Standard", "Media Mail"])

with col2:
    zip_to = st.text_input("Destination Zip Code", value="90210", max_chars=5)
    ship_date = st.date_input("Shipment Date")

# Calculate Button
if st.button("Calculate Delivery Expectation", type="primary"):
    if len(zip_from) > 0 and len(zip_to) > 0 and zip_from[0].isdigit() and zip_to[0].isdigit():
        calc = USPSCalculator()
        result = calc.get_delivery_estimate(zip_from, zip_to, service_name, ship_date)
        
        st.divider()
        st.subheader("📊 Delivery Projection")
        
        # Display large metrics
        metric_col1, metric_col2, metric_col3 = st.columns(3)
        metric_col1.metric("USPS Quoted Target", f"{result['Quoted Target Days']} days")
        metric_col2.metric("Adjusted Expected", f"{result['Adjusted Expected Days']} days")
        metric_col3.metric("Confidence Level", result['Confidence Level'])
        
        st.success(f"**Estimated Delivery Date:** {result['Estimated Delivery Date']}")
        
        # Display the algorithm's detected risk factors
        st.info("**Algorithmic Risk Assessment applied:**\n" + "\n".join([f"* {risk}" for risk in result["Risk Factors"]]))
        
        st.caption(f"Routing Data: {result['Origin -> Dest Zip']} | Estimated Shipping Zone: {result['Est. Zone']}")
    else:
        st.error("Please enter valid starting digits for your Zip Codes.")
