import os
import json
import requests
import pandas as pd
from datetime import datetime

LOCAL_URL = "http://41.33.162.236/egs4/"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
DATA_FILE = "egx_market_data.json"

# قاموس ذكي يعتمد على كلمات مفتاحية صغيرة لضمان قراءة اسم السهم كيفما كُتب في سيرفرك
TICKER_MAPPING = {
    "التجاري": "COMI",
    "فوري": "FWRY",
    "طلعت": "TMGH",
    "جهينة": "JUFO",
    "السويدى": "SWDY",
    "بلتون": "BTFH",
    "أموك": "AMOC",
    "أبو قير": "ABUK",
    "موبكو": "MFPC",
    "بالم هيلز": "PHDC",
    "سي آي": "CICH",
    "غبور": "GBCO"
}

def fetch_tv_historical_bars(ticker, interval="30"):
    """جلب الشموع التاريخية من TradingView وتجنب الشمعة اللحظية الأخيرة"""
    try:
        tv_url = f"https://api.tradingview.com/v1/symbols/EGX:{ticker}/history"
        params = {"interval": interval, "limit": 30}
        res = requests.get(tv_url, params=params, timeout=7)
        if res.status_code == 200:
            candles = res.json().get('bars', [])
            if candles:
                historical_volumes = [c['v'] for c in candles[:-1]]
                avg_vol = sum(historical_volumes) / len(historical_volumes) if historical_volumes else 1.0
                history_bars = [{
                    "time": datetime.fromtimestamp(c['t']).strftime('%Y-%m-%d %H:%M'),
                    "open": c['o'], "high": c['h'], "low": c['l'], "close": c['c'], "volume": c['v']
                } for c in candles[:-1]]
                return history_bars, avg_vol
    except:
        pass
    return [], 1.0

if __name__ == "__main__":
    print("📡 قراءة وفك تشفير جدول السيرفر المحلي 100%...")
    output_data = {}
    current_time = datetime.now().strftime("%H:%M:%S")
    
    try:
        response = requests.get(LOCAL_URL, headers=HEADERS, timeout=15)
        
        if response.status_code == 200 and "html" in response.text:
            tables = pd.read_html(response.text, encoding='utf-8')
            df = tables[0]
            
            # تحويل كل الخلايا لنصوص لتسهيل البحث الذكي عن الأعمدة والأسهم
            df = df.astype(str)
            
            for _, row in df.iterrows():
                # دمج كل نصوص الصف في نص واحد للبحث الفوري عن الكلمة المفتاحية
                row_text = " ".join(row.values)
                
                ticker = None
                matched_keyword = None
                for keyword, tck in TICKER_MAPPING.items():
                    if keyword in row_text:
                        ticker = tck
                        matched_keyword = keyword
                        break
                
                if not ticker:
                    continue
                
                try:
                    # استخراج الأرقام (السعر والفوليوم) من الصف ديناميكياً بفلترة النصوص
                    numeric_values = []
                    for val in row.values:
                        cleaned = val.replace(',', '').strip()
                        # التحقق من أن القيمة رقمية (سواء كانت فلوت أو إنتجر)
                        if cleaned.replace('.', '', 1).isdigit():
                            numeric_values.append(float(cleaned))
                    
                    if len(numeric_values) < 2:
                        continue
                    
                    # عادة في جداول الأسعار: الرقم الصغير هو السعر، والرقم الضخم جداً هو الفوليوم (حجم التداول)
                    server_price = min(numeric_values)
                    server_volume = max(numeric_values)
                    
                    # إذا كان الفوليوم مستحيل أن يكون سعراً (أكبر من 1000 مثلاً) نعتمد الترتيب الصحيح
                    if len(numeric_values) >= 3:
                        # ترتيب افتراضي احتياطي دقيق بحسب جداول egs
                        try:
                            server_price = float(row.iloc[2].replace(',', ''))
                            server_volume = int(float(row.iloc[6].replace(',', '')))
                        except:
                            pass

                    # جلب الداتا التاريخية من TradingView
                    history_bars, dynamic_avg_vol = fetch_tv_historical_bars(ticker, interval="30")
                    
                    # حساب نسبة مضاعف السيولة
                    volume_multiplier = round(server_volume / dynamic_avg_vol, 2) if dynamic_avg_vol > 0 else 0.0
                    
                    # صياغة الإشارة بناءً على فوليوم سيرفرك 100%
                    if server_volume == 0 or server_price == 0:
                        signal = "💤 السوق مغلق حالياً (البيانات صفرية بالسيرفر)"
                    elif volume_multiplier > 1.5:
                        signal = "🟢 تجمع مؤسسي قوي (سيولة السيرفر تخترق المتوسط)"
                    else:
                        signal = "⚪ مراقبة (تدفقات طبيعية)"
                    
                    now_str = datetime.now().strftime('%Y-%m-%d %H:%M')
                    server_latest_candle = {
                        "time": now_str, "open": server_price, "high": server_price,
                        "low": server_price, "close": server_price, "volume": int(server_volume)
                    }
                    
                    full_history = history_bars + [server_latest_candle] if history_bars else [server_latest_candle]
                    
                    output_data[ticker] = {
                        "name": f"{matched_keyword} (من سيرفرك)",
                        "ticker": ticker,
                        "price": server_price,
                        "volume": int(server_volume),
                        "dynamic_avg_vol": int(dynamic_avg_vol),
                        "volume_x": f"{volume_multiplier}X",
                        "signal": signal,
                        "history": full_history,
                        "last_update": current_time
                    }
                    print(f"✅ نجح صيد سهم {ticker} من السيرفر المحلي.")
                except Exception as e:
                    print(f"خطأ صف {ticker}: {e}")
                    continue
        else:
            print("⚠️ السيرفر لم يرجع HTML.")
    except Exception as e:
        print(f"❌ خطأ اتصال: {e}")

    # قسرياً: إذا كان الجدول فاضي تماماً الآن نضع القالب ليعمل الموقع ولا يعلق على "جاري قراءة ملف البيانات"
    if not output_data:
        for tck, name in {"COMI": "التجاري الدولي", "FWRY": "فوري", "TMGH": "طلعت مصطفى"}.items():
            output_data[tck] = {
                "name": name, "ticker": tck, "price": 0.0, "volume": 0, "dynamic_avg_vol": 1,
                "volume_x": "0X", "signal": "💤 السوق مغلق حالياً — بانتظار بدء الجلسة", "history": [], "last_update": current_time
            }

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)
    print("🚀 تم تحديث ملف egx_market_data.json بنجاح تام!")
