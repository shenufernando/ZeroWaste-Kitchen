<div align="center">

# 🥦 ZeroWaste Kitchen — Smart Pantry & AI Impact Dashboard

<img src="https://img.shields.io/badge/Python-3.8%2B-blue?style=for-the-badge&logo=python&logoColor=white" />
<img src="https://img.shields.io/badge/Flask-Framework-black?style=for-the-badge&logo=flask&logoColor=white" />
<img src="https://img.shields.io/badge/Bootstrap-5.3-purple?style=for-the-badge&logo=bootstrap&logoColor=white" />
<img src="https://img.shields.io/badge/Chart.js-Analytics-orange?style=for-the-badge&logo=chart.js&logoColor=white" />
<img src="https://img.shields.io/badge/AI-Generative%20LLM-green?style=for-the-badge&logo=googlegemini&logoColor=white" />
<img src="https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge" />

*An intelligent, full-stack sustainable web platform engineered to optimize household inventory tracking, mitigate food wastage, quantify ecological/financial impacts, and deliver dynamic AI-driven culinary insights.*

</div>

---

## 🌟 Executive Summary

**ZeroWaste Kitchen** is a modern, data-driven web application designed to tackle household food waste at its root. By combining real-time inventory management, dynamic freshness tracking, and advanced Generative AI capabilities, the platform bridges the gap between everyday pantry surplus and sustainable cooking. It empowers users to monitor expiry thresholds, visualize category distributions, calculate real-world financial savings and carbon footprint reductions, and generate smart custom recipes on the fly.

---

## 🚀 Key Architectural Features

* **📦 Smart Inventory Lifecycle Management:** 
  * Real-time tracking of total pantry contents, categorized items, and granular expiration lifecycles.
* **🥦 Predictive Freshness Analytics & Alerts:**
  * Automated threshold categorization differentiating between *Fresh*, *Expiring Soon ($\le 3$ Days)*, and *Expired* items via live visual rings.
* **📊 Immersive Data Visualization:**
  * Custom-styled, responsive analytical dashboards utilizing **Chart.js** for real-time Doughnut breakdown metrics and Category-wise distribution bars.
* **🌱 Ecological & Financial Impact Engine:**
  * Algorithmic quantification modules calculating estimated monetary savings (in LKR) and avoided $\text{CO}_2$ emissions ($kg$) to promote zero-waste behavioral shifts.
* **🤖 AI-Powered Recipe & Insight Generation:**
  * Seamless integration with advanced Large Language Models (LLMs) to scan active inventory constraints and formulate personalized gourmet recipes alongside predictive smart insights.

---

## 🛠️ Technology Stack & Architecture

### **Presentation Tier (Frontend)**
* **Markup & Styling:** HTML5, CSS3, **Bootstrap 5** (utilizing a modern glassmorphism and clean card-based UI layout).
* **Interactivity & Scripting:** Vanilla JavaScript (ES6+), asynchronous DOM manipulation.
* **Data Visualization Engine:** Chart.js (Interactive canvas rendering).

### **Application & Logic Tier (Backend)**
* **Core Framework:** Python **Flask** (Lightweight, robust WSGI web application framework).
* **Template Engine:** Jinja2 (Dynamic server-side template rendering).
* **AI Integration:** Google GenAI / LLM API wrapper for automated prompt engineering and context-aware recipe formulation.

---

## ⚙️ Installation & Local Setup Guide

Follow these sequential steps to set up and run the application locally on your machine.

### **1. Prerequisites**
Ensure you have the following installed on your system:
* Python (v3.8 or higher)
* Git

### **2. Clone the Repository**
Open your terminal and clone the project:
```bash
git clone [https://github.com/shenufernando/ZeroWaste-Kitchen.git](https://github.com/shenufernando/ZeroWaste-Kitchen.git)
cd ZeroWaste-Kitchen
