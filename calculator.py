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
        # Pre-load US holidays for current and next few years
        current_year = datetime.now().year
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
        
        # Winter risks
        if month in [12, 1, 2, 3] and (from_prefix in [0,1,2,5,6,7] or to_prefix in [0,1,2,5,6,7]):
            weather_delay += 0.5 + (zone * 0.1)
            risk_factors.append("❄️ Winter Season Routing Risk")
            
        # Summer Storm risks
        if month in [8, 9, 10] and (from_prefix in [3,4] or to_prefix in [3,4]):
            weather_delay += 0.4 + (zone * 0.05)
            risk_factors.append("🌪️ Late Summer Storm Risk")
            
        # Distance Detour Risk
        detour_delay = (zone * 0.15)
        if zone >= 5:
            risk_factors.append("🛣️ Long-Distance Hub Transfer Risk")
            
        if not risk_factors:
            risk_factors.append("✅ Clear Seasonal Routing expected")
            
        return round(weather_delay, 2), round(detour_delay, 2), risk_factors

    def calculate_confidence(self, target_days, mu, sigma):
        if sigma <= 0:
            return 100.0 if mu <= target_days else 0.0
        probability = 0.5 * (1 + math.erf((target_days - mu) / (sigma * math.sqrt(2))))
        return max(min(probability * 100, 100.0), 0.0)

    def get_delivery_estimate(self, zip_from, zip_to, service_name, ship_date, late_dropoff=False):
        # Shift start date if dropped off after 5 PM
        active_date = ship_date
        if late_dropoff:
            active_date += timedelta(days=1)
            while active_date.weekday() == 6 or active_date in self.us_holidays:
                active_date += timedelta(days=1)

        service = self.services[service_name]
        zone = self.estimate_zone(zip_from, zip_to)
        
        zone_multiplier = 0.4 if service_name == "Media Mail" else 0.25
        target_days = math.ceil(service["base_days"] + (zone * zone_multiplier))
        
        weather_delay, detour_delay, risk_factors = self.assess_route_risks(zip_from, zip_to, active_date, zone)
        
        mu = target_days + weather_delay + detour_delay
        sigma = service["base_sigma"] + (zone * 0.15) + (weather_delay * 0.5) + (detour_delay * 0.4)

        confidence = self.calculate_confidence(target_days, mu, sigma)
        
        # Calculate final delivery date skipping Sundays AND Holidays
        delivery_date = active_date
        days_to_add = math.ceil(mu)
        
        while days_to_add > 0:
            delivery_date += timedelta(days=1)
            if delivery_date.weekday() != 6 and delivery_date not in self.us_holidays: 
                days_to_add -= 1

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
            "Risk Factors": risk_factors
        }

# ==========================================
# STREAMLIT WEB INTERFACE
# ==========================================
st.set_page_config(page_title="USPS Calculator", page_icon="📦", layout="wide")

st.title("📦 USPS Statistical Delivery Calculator")
st.write("Calculate realistic delivery probabilities factoring in zones, seasonality, holidays, and route behaviors.")

tab1, tab2 = st.tabs(["📌 Single Package", "📁 Bulk E-commerce Upload"])

calc = USPSCalculator()

# --- TAB 1: SINGLE PACKAGE ---
with tab1:
    col1, col2 = st.columns(2)
    
    with col1:
        zip_from = st.text_input("Origin Zip Code", value="10001", max_chars=5)
        service_name = st.selectbox("Service Type", list(calc.services.keys()))
        late_dropoff = st.checkbox("🕒 Dropping off after 5 PM? (Shifts to next business day)")
    
    with col2:
        zip_to = st.text_input("Destination Zip Code", value="90210", max_chars=5)
        ship_date = st.date_input("Shipment Date")
    
    if st.button("Calculate Delivery Expectation", type="primary"):
        if len(zip_from) >= 5 and len(zip_to) >= 5 and zip_from.isdigit() and zip_to.isdigit():
            result = calc.get_delivery_estimate(zip_from, zip_to, service_name, ship_date, late_dropoff)
            
            st.divider()
            
            # Display large metrics
            metric_col1, metric_col2, metric_col3 = st.columns(3)
            metric_col1.metric("USPS Quoted Target", f"{result['Target Days']} days")
            metric_col2.metric("Adjusted Expected", f"{result['Expected Days (μ)']} days")
            metric_col3.metric("Confidence Level", f"{result['Confidence']}%")
            
            st.success(f"**Estimated Delivery Date:** {result['Delivery Date']}")
            st.info("**Algorithmic Risk Assessment applied:**\n" + "\n".join([f"* {risk}" for risk in result["Risk Factors"]]))
            
            # Generate Probability Curve Chart
            st.subheader("📈 Probability Distribution Curve")
            st.write("This chart visualizes the likelihood of your package arriving on specific days based on standard deviation.")
            
            mu = result['Expected Days (μ)']
            sigma = result['Variance (σ)']
            x = np.linspace(max(0, mu - 3*sigma), mu + 4*sigma, 100)
            y = stats.norm.pdf(x, mu, sigma)
            
            chart_data = pd.DataFrame({'Days in Transit': x, 'Probability Density': y}).set_index('Days in Transit')
            st.area_chart(chart_data)
            
        else:
            st.error("Please enter valid 5-digit Zip Codes.")

# --- TAB 2: BULK UPLOAD ---
with tab2:
    st.subheader("Process Multiple Orders (CSV)")
    st.write("Upload a CSV file containing your orders. The CSV must have columns named exacty: **Origin**, **Destination**, and **Service**.")
    
    # Download template button
    template_df = pd.DataFrame({"Origin": ["10001", "33101"], "Destination": ["90210", "60601"], "Service": ["Priority", "Ground Advantage"]})
    st.download_button("📥 Download CSV Template", data=template_df.to_csv(index=False), file_name="usps_template.csv", mime="text/csv")
    
    uploaded_file = st.file_uploader("Upload filled CSV", type=["csv"])
    bulk_date = st.date_input("Shipment Date for all orders")
    bulk_late = st.checkbox("🕒 All orders dropping off after 5 PM?")
    
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            
            if st.button("Process Bulk Orders"):
                with st.spinner("Calculating logistics..."):
                    results_list = []
                    for index, row in df.iterrows():
                        res = calc.get_delivery_estimate(str(row["Origin"]), str(row["Destination"]), row["Service"], bulk_date, bulk_late)
                        # Clean up for tabular output
                        res.pop("Risk Factors") 
                        results_list.append(res)
                        
                    results_df = pd.DataFrame(results_list)
                    st.dataframe(results_df, use_container_width=True)
                    
                    csv = results_df.to_csv(index=False)
                    st.download_button(label="💾 Download Processed Results", data=csv, file_name="usps_estimates_processed.csv", mime="text/csv")
        except Exception as e:
            st.error(f"Error processing file. Ensure columns match the template. Error: {e}")
