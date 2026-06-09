import os
import json
import requests
import pandas as pd
from datetime import datetime

# السورس اللحظي الخاص بك (تحديث كل 30 ثانية)
LOCAL_URL = "http://41.33.162.236/egs4/"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
DATA_FILE = "egx_market_data.json"

TICKER_MAPPING = {
    "وثائق صندوق EGX 30 INDEX ETF": "EGX30ETF", "جهينة للصناعات الغذائية": "JUFO",
    "سي آي كابيتال القابضة": "CICH", "جي بي كوربوريشن (جي بي غبور)": "GBCO",
    "المالية والصناعية المصرية": "EFIC", "البنك التجاري الدولي - مصر": "COMI", 
    "بالم هيلز للتعمير": "PHDC", "الاسكندرية للزيوت المعدنية - أموك": "AMOC",
    "ابوقير للاسمدة والصناعات الكيماوية": "ABUK", "فوري للمدفوعات الإلكترونية": "FWRY", 
    "مصرف أبوظبي الإسلامي": "ADIB", "مصر لإنتاج الأسمدة - موبكو": "MFPC",
    "مجموعة طلعت مصطفى": "TMGH", "بلتون القابضة": "BTFH", "السويدى اليكتريك": "SWDY"
}

def fetch_tradingview_history(ticker, interval="30"):
    """جلب المتوسطات التاريخية بدقة من تريدنج فيو للفريم المختار"""
    try:
        tv_url = f"https://api.tradingview.com/v1/symbols/EGX:{ticker}/history"
        params = {"interval": interval, "limit": 21}
        res = requests.get(tv_url, params=params, timeout=5)
        if res.status_code == 200:
            candles = res.json().get('bars', [])
            if candles:
                # حساب المتوسط لآخر 20 شمعة مغلقة (باستثناء الشمعة الحالية)
                volumes = [c['v'] for c in candles[:-1]]
                avg_volume = sum(volumes) / len(volumes) if volumes else 1.0
                
                history_bars = [{
                    "time": datetime.fromtimestamp(c['t']).strftime('%Y-%m-%d %H:%M'),
                    "open": c['o'], "high": c['h'], "low": c['l'], "close": c['c'], "volume": c['v']
                } for c in candles]
                return history_bars, avg_volume
    except:
        pass
    return [], 1000000 # قيمة احتياطية

if __name__ == "__main__":
    print("📡 محاولة الاتصال بالسيرفر المحلي لسحب البيانات اللحظية...")
    output_data = {}
    current_time = datetime.now().strftime("%H:%M:%S")
    
    try:
        response = requests.get(LOCAL_URL, headers=HEADERS, timeout=12)
        
        if response.status_code == 200 and "html" in response.text:
            tables = pd.read_html(response.text, encoding='utf-8')
            df = tables[0]
            
            for _, row in df.iterrows():
                try:
                    raw_name = str(row[1]).strip()
                    ticker = None
                    for key, val in TICKER_MAPPING.items():
                        if key in raw_name or raw_name in key:
                            ticker = val
                            break
                    
                    if not ticker: continue
                    
                    # قراءة البيانات اللحظية الحية المحدثة كل 30 ثانية من سيرفرك
                    current_price = float(row[2])
                    current_volume = int(row[6])
                    
                    # دمجها مع متوسط الفوليوم التاريخي من تريدنج فيو
                    history_bars, dynamic_avg_vol = fetch_tradingview_history(ticker, "30")
                    volume_multiplier = round(current_volume / dynamic_avg_vol, 2)
                    
                    # فلترة التجمع بناءً على معادلتك المستقرة
                    if volume_multiplier > 1.5:
                        signal = "🟢 تجمع مؤسسي (السيولة اللحظية تفوق المتوسط التاريخي)"
                    else:
                        signal = "⚪ مراقبة (تدفقات طبيعية متزنة)"
                        
                    output_data[ticker] = {
                        "name": raw_name, "ticker": ticker, "price": current_price,
                        "volume": current_volume, "dynamic_avg_vol": int(dynamic_avg_vol),
                        "volume_x": f"{volume_multiplier}X", "signal": signal,
                        "history": history_bars, "last_update": current_time
                    }
                except:
                    continue
        else:
            print("⚠️ السيرفر المحلي لم يرجع جدول بيانات (قد يكون خارج أوقات الجلسة).")
    except Exception as e:
        print(f"❌ تعذر الاتصال بالسيرفر المحلي: {e}")

    # حماية المنظومة: إذا كان السيرفر مغلقاً ولم نجد بيانات، نضع بيانات احتياطية لكي لا يفشل الـ Git
    if not output_data:
        print("📦 إنشاء ملف البيانات الافتراضي لحماية واجهة الموقع من التوقف...")
        output_data = {
            "COMI": {
                "name": "البنك التجاري الدولي (خارج أوقات الجلسة)", "ticker": "COMI", "price": 0.0,
                "volume": 0, "dynamic_avg_vol": 1000000, "volume_x": "0X",
                "signal": "💤 السوق مغلق حالياً — بانتظار بدء الجلسة", "history": [], "last_update": current_time
            }
        }

    # كتابة وحفظ الملف دائماً
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)
    print("✅ تم حفظ ملف egx_market_data.json بنجاح وتم إنهاء المهمة!")
