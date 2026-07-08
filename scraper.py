import requests
import json

SYMBOL = "ARCC"
BASE_URL = "https://egxpilot.com/api"
STOCKS_API = f"{BASE_URL}/stocks/{SYMBOL}"
ANALYSIS_API = f"{BASE_URL}/stockanalysis/{SYMBOL}"

def pull_egxpilot_data():
    print(f"📡 بدء الاتصال المباشر بـ EGXpilot لسهم: {SYMBOL}...")
    
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json"
    }
    
    try:
        response = requests.get(STOCKS_API, headers=headers, timeout=10)
        print(f"📊 كود استجابة السيرفر للأسعار: {response.status_code}")
        
        if response.status_code == 200:
            stock_data = response.json()
            
            # جلب تحليل
