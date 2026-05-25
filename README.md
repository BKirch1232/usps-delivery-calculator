# 📦 USPS Statistical Delivery Calculator

> A Python-based logistics tool that calculates realistic USPS delivery dates by treating transit times as probability distributions rather than static guarantees. 

Instead of simply adding days to a calendar, this calculator factors in shipping zones, specific service types, weather delays, and routing detours to generate a statistical **Confidence Percentage** for your expected delivery date.

---

### 🧮 The Math Behind the Model
This tool uses Normal Distribution and Cumulative Distribution Functions (CDF) to calculate delivery probabilities. It establishes a baseline mean delivery time (**μ**) and standard deviation/variance (**σ**) for each service class, which are then modified by distance (Zones 1-8) and external delays.

---

### 🚚 Supported Services & Network Behaviors

* **Priority Mail Express:** Low variance, strict routing.
* **Priority Mail:** Standard variance, reliable network flow.
* **Ground Advantage:** Moderate variance, truck-based routing.
* **First-Class Letter (Stamped):** High variance. Models standard letter mail processed through high-speed sorting bins. Subject to machine misrouting with no tracking visibility.
* **eBay Standard Envelope (ESE):** High variance. Uses the exact same physical network and mathematical model as First-Class Letters, but includes eBay's proprietary Intelligent Mail barcode (IMb) tracking.
* **Media Mail:** Highest variance. Models the "space-available" routing behavior of USPS freight, scaling the penalty for cross-country (Zone 8) transit.

---

### ✨ Key Features

* **Dynamic Zone Estimation:** Approximates USPS shipping zones based on origin and destination zip code prefixes.
* **External Delay Modifiers:** Adjusts the probability curve for severe weather or rerouted trucks.
* **Smart Calendar Routing:** Automatically skips Sundays when projecting the final estimated delivery date.

---

### 🚀 How to Run

To run this calculator locally, open your terminal and execute the following command:

```bash
python calculator.py
