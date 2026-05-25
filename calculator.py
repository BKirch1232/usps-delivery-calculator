import streamlit as st
import math
import pandas as pd
import numpy as np
import scipy.stats as stats
import holidays
from datetime import datetime, timedelta

class USPSCalculator:
    def __init__(self):
        self.services = {
            "Express": {"base_days": 1, "base_sigma": 0.2, "guaranteed": True},
            "Priority": {"base_days": 2, "base_sigma": 0.7, "guaranteed": False},
            "Ground Advantage": {"base_days": 4, "base_sigma": 1.2, "guaranteed": False},
            "First-Class Letter": {"base_days": 3, "base_sigma": 1.8, "guaranteed": False},
            "eBay Standard": {"base_days": 3, "base_sigma": 1.8, "guaranteed": False},
            "Media Mail": {"base_days": 4, "base_sigma": 2.5, "guaranteed": False}
        }
        current_year = datetime.now().year
        # Pre-load US holidays for current and next few years
        self.us_holidays = holidays.US(years=[current_year, current_year + 1, current_year + 2])

    def estimate_zone(self, zip_from, zip_to):
        diff = abs(int(str(zip_from)[0]) - int(str(zip_to)[0]))
        return min(max(diff, 1), 8)

    def assess_route_risks(self, zip_from, zip_to, ship_date, zone):
        month = ship_date.month
        from_prefix = int(str(zip_from)[0])
        to_prefix = int(str(zip_to)[0])
        
        weather_delay = 0.0
        risk_factors = []
        
        if month in [11, 12]:
            weather_delay += 0.5 + (zone * 0.05)
            risk_factors.append("🎄 Q4 Peak Season Congestion")
        if month in [1, 2, 3] and (from_prefix in [0,1,2,5,6,7] or to_prefix in [0,1,2,5,6,7]):
            weather_delay += 0.5 + (zone * 0.1)
            risk_factors.append("❄️ Winter Weather Routing Risk")
        if month in [8, 9, 10] and (from_prefix in [3,4] or to_prefix in [3,4]):
            weather_delay += 0.4 + (zone * 0.05)
            risk_factors.append("🌪️ Late Summer Storm Risk")
            
        detour_delay = (zone * 0.15)
        if zone >= 5:
            risk_factors.append("🛣️ Long-Distance Hub Transfer Risk")
            
        return round(weather_delay, 2), round(detour_delay, 2), risk_factors

    def calculate_confidence(self, target_days, mu, sigma):
        if sigma <= 0:
            return 100.0 if mu <= target_days else 0.0
        probability = 0.5 * (1 + math.erf((target_days - mu) / (sigma * math.sqrt(2))))
        return max(min(probability * 100, 100.0), 0.0)

    def get_delivery_estimate(self, zip_from, zip_to, service_name, ship_date, late_dropoff=False):
        active_date = ship_date
        skipped_days_log = []
        
        # 1. Check Origin Date for Sundays, Holidays, or Late Dropoff
        while active_date.weekday() == 6 or active_date in self.us_holidays or late_dropoff:
            if active_date in self.us_holidays:
                holiday_name = self.us_holidays.get(active_date)
                skipped_days_log.append(f"Origin Paused: {holiday_name} ({active_date.strftime('%b %d')})")
            elif active_date.weekday() == 6:
                skipped_days_log.append(f"Origin Paused: Sunday ({active_date.strftime('%b %d')})")
            elif late_dropoff:
                skipped_days_log.append("Origin Paused: After-hours dropoff (Shifts to next day)")
            
            late_dropoff = False # Reset so we don't infinitely loop
            active_date += timedelta(days=1)

        service = self.services[service_name]
        zone = self.estimate_zone(zip_from, zip_to)
        zone_multiplier = 0.4 if service_name == "Media Mail" else 0.25
        
        base = service["base_days"]
        zone_penalty = zone * zone_multiplier
        target_days = math.ceil(base + zone_penalty)
        
        weather_delay, detour_delay, risk_factors = self.assess_route_risks(zip_from, zip_to, active_date, zone)
        
        mu = target_days + weather_delay + detour_delay
        sigma = service["base_sigma"] + (zone * 0.15) + (weather_delay * 0.5) + (detour_delay * 0.4)
        confidence = self.calculate_confidence(target_days, mu, sigma)
        
        # 2. Iterate through Transit Calendar
        delivery_date = active_date
        days_to_add = math.ceil(mu)
        
        while days_to_add > 0:
            delivery_date += timedelta(days=1)
            if delivery_date in self.us_holidays:
                holiday_name = self.us_holidays.get(delivery_date)
                skipped_days_log.append(f"Transit Paused: {holiday_name} ({delivery_date.strftime('%b %d')})")
            elif delivery_date.weekday() == 6: 
                skipped_days_log.append(f"Transit Paused: Sunday ({delivery_date.strftime('%b %d')})")
            else:
                days_to_add -= 1

        # 3. Create the Impact Breakdown
        impact_breakdown = {
            "Base Transit Time": f"{base} days",
            "Distance Penalty (Zone)": f"+{round(zone_penalty, 2)} days",
            "Weather/Seasonal Delay": f"+{weather_delay} days",
            "Logistical Detour Risk": f"+{detour_delay} days",
            "Total Working Days (μ)": f"{round(mu, 2)} days"
        }

        return {
            "Service": service_name,
            "Origin": str(zip_from).zfill(5),
            "Destination": str(zip_to).zfill(5),
            "Zone": zone,
            "Target Days": target_days,
            "Expected Days (μ)": round(mu, 2),
            "Variance (σ)": round(sigma, 2),
            "Delivery Date": delivery_date.strftime("%Y-%m-%d (%A)"),
            "Confidence": round(confidence, 2),
            "Risk Factors": risk_factors,
            "Skipped Calendar Days": skipped_days_log,
            "Impact Breakdown": impact_breakdown
        }

# ==========================================
# STREAMLIT WEB INTERFACE
# ==========================================
st.set_page_config(page_title="USPS Calculator", page_icon="📦", layout="wide")

st.title("📦 USPS Statistical Delivery Calculator")
st.write("Calculate realistic delivery probabilities factoring in zones, seasonality, holidays, and route behaviors.")

tab1, tab2 = st.tabs(["📌 Single Package", "📁 Bulk E-commerce Upload"])
calc = USPSCalculator()

# --- TAB
