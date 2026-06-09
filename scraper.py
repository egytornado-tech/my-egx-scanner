import os
import json
import requests
import pandas as pd
from datetime import datetime

# السورس اللحظي الأساسي الخاص بك
LOCAL_URL = "http://41.33.162.236/egs4/"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
DATA_FILE = "egx_market_data.json"

# قاموس الربط بين الأسماء في سيرفرك وتيكرات TradingView
TICKER_MAPPING = {
    "وثائق صندوق EGX 30 INDEX ETF": "EGX30ETF", 
    "جهينة للصناعات الغذائية": "JUFO",
    "سي آي كابيتال القابضة": "CICH", 
    "جي بي كوربوريشن (جي بي غبور)": "GBCO",
    "المالية والصناعية المصرية": "EFIC", 
    "البنك التجاري الدولي - مصر": "COMI", 
    "بالم هيلز للتعمير": "PHDC", 
    "الاسكندرية للزيوت المعدنية - أموك": "AMOC",
    "ابوقير للاسمدة والصناعات الكيماوية": "ABUK", 
    "فوري للمدفوعات الإلكترونية": "FWRY", 
    "مصرف أبوظبي الإسلامي": "ADIB", 
    "مصر لإنتاج الأسمدة - موبكو": "MFPC",
    "مجموعة طلعت مصستم": "TMGH", 
    "بلتون القابضة": "BTFH", 
    "السويدى اليكتريك": "SWDY"
}

def fetch_tv_historical_bars(ticker, interval="30"):
    """جلب الشموع التاريخية القديمة فقط من TradingView"""
    try:
        tv_url = f"https://api.tradingview.com/v1/symbols/EGX:{ticker}/history"
        params = {"interval": interval, "limit": 30}
        res = requests.get(tv_url, params=params, timeout=7)
        if res.status_code == 200:
            candles = res.json().get('bars', [])
            if candles:
                # حساب متوسط حجم التداول للشموع السابقة (باستثناء الشمعة الحالية)
                historical_volumes = [c['v'] for c in candles[:-1]]
                avg_vol = sum(historical_volumes) / len(historical_volumes) if historical_volumes else 1.0
                
                # تحويل الشموع لصيغة الواجهة مع استثناء الشمعة اللحظية الأخيرة لتأتي من سيرفرك
                history_bars = [{
                    "time": datetime.fromtimestamp(c['t']).strftime('%Y-%m-%d %H:%M'),
                    "open": c['o'], "high": c['h'], "low": c['l'], "close": c['c'], "volume": c['v']
                } for c in candles[:-1]] # أخذ الشموع القديمة فقط
                
                return history_bars, avg_vol
    except:
        pass
    return [], 1.0

if __name__ == "__main__":
    print("📡 جلب البيانات اللحظية الحالية من السيرفر المحلي 100%...")
    output_data = {}
    current_time = datetime.now().strftime("%H:%M:%S")
    
    try:
        response = requests.get(LOCAL_URL, headers=HEADERS, timeout=15)
        
        if response.status_code == 200 and "html" in response.text:
            # قراءة الجداول من السيرفر المحلي الخاص بك
            tables = pd.read_html(response.text, encoding='utf-8')
            df = tables[0]
            
            print(f"📊 تم العثور على {len(df)} صف في جدول السيرفر المحلي.")
            
            for _, row in df.iterrows():
                try:
                    # استخراج الاسم والسعر والحجم اللحظي مباشرة من سيرفرك
                    raw_name = str(row[1]).strip()
                    
                    # البحث عن التيكر المناسب
                    ticker = None
                    for key, val in TICKER_MAPPING.items():
                        if key in raw_name or raw_name in key:
                            ticker = val
                            break
                    
                    if not ticker: 
                        continue
                    
                    # قراءة البيانات الرقمية اللحظية من سيرفرك الآن
                    server_price = float(row[2])      # السعر الحالي من سيرفرك
                    server_volume = int(row[6])      # حجم التداول اللحظي من سيرفرك
                    
                    # جلب الشموع التاريخية القديمة للفريم الحالي من TradingView
                    history_bars, dynamic_avg_vol = fetch_tv_historical_bars(ticker, interval="30")
                    
                    # حساب مضاعف الفوليوم بناءً على (حجم سيرفرك الحالي ÷ متوسط حجم TV القديم)
                    volume_multiplier = round(server_volume / dynamic_avg_vol, 2)
                    
                    # تطبيق معادلة التجميع الخاصة بك (فلترة السيولة القوية تفوق 1.5X أو بناءً على نسبتك 58%)
                    if volume_multiplier > 1.5:
                        signal = "🟢 تجمع مؤسسي (سيولة السيرفر تخترق المتوسط)"
                    else:
                        signal = "⚪ مراقبة (تدفقات طبيعية)"
                    
                    # إضافة الشمعة اللحظية الحالية بناءً على أسعار سيرفرك الآن فوق الشموع القديمة
                    now_str = datetime.now().strftime('%Y-%m-%d %H:%M')
                    server_latest_candle = {
                        "time": now_str,
                        "open": server_price, # محاكاة بداية الشمعة بسعر السيرفر الحالي
                        "high": server_price,
                        "low": server_price,
                        "close": server_price,
                        "volume": server_volume
                    }
                    
                    # دمج داتا السيرفر اللحظية مع تاريخ TradingView القديم
                    full_history = history_bars + [server_latest_candle]
                    
                    output_data[ticker] = {
                        "name": raw_name,
                        "ticker": ticker,
                        "price": server_price,
                        "volume": server_volume,
                        "dynamic_avg_vol": int(dynamic_avg_vol),
                        "volume_x": f"{volume_multiplier}X",
                        "signal": signal,
                        "history": full_history,
                        "last_update": current_time
                    }
                    print(f"✅ تم دمج سهم {ticker}: سورس السيرفر المحلي ({server_price}) + تاريخ TV.")
                except Exception as e:
                    continue
        else:
            print("⚠️ السيرفر المحلي متوقف حالياً أو لم يرسل جدولاً صحسحاً.")
    except Exception as e:
        print(f"❌ خطأ في الاتصال بالسيرفر المحلي: {e}")

    # حماية الهيكل: إذا كان السيرفر مغلقاً تماماً الآن نترك آخر داتا مسجلة أو نضع قالباً لكي لا ينهار الـ Git
    if not output_data:
        print("📦 السيرفر لم يرسل بيانات جديدة حالياً، جاري الحفاظ على استقرار الهيكل...")
        output_data = {
            "COMI": {
                "name": "البنك التجاري الدولي (بانتظار السيرفر)", "ticker": "COMI", "price": 0.0,
                "volume": 0, "dynamic_avg_vol": 1, "volume_x": "0X",
                "signal": "💤 السيرفر المحلي لم يرسل داتا حية الآن", "history": [], "last_update": current_time
            }
        }

    # حفظ ملف الـ JSON النهائي
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)
    print("🚀 تم تحديث ملف egx_market_data.json بنجاح تام!")
