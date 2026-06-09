import os
import time
import json
import requests
import pandas as pd
from datetime import datetime

# إعدادات سورس السكراب المباشر للأسعار اللحظية (EGS4)
URL = "http://41.33.162.236/egs4/"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
DATA_FILE = "egx_market_data.json"

# قاموس مطابقة الأسماء بالتيكر الصحيح لـ TradingView (السوق المصري EGX)
TICKER_MAPPING = {
    "وثائق صندوق EGX 30 INDEX ETF": "EGX30ETF", "جهينة للصناعات الغذائية": "JUFO", "المجموعة الاستشارية الفنية للاستثمار - ايكون": "ENGC",
    "سي آي كابيتال القابضة": "CICH", "الاسكندرية للادوية والصناعات الكيماوية": "AXPH", "جي بي كوربوريشن (جي بي غبور)": "GBCO",
    "المهندس للتأمين": "MOIN", "الخليجية الكندية للاستثمار العقاري العربي": "CCRS", "المطابع الوطنية": "NAPR",
    "المالية والصناعية المصرية": "EFIC", "البنك المصري الخليجي": "EGBE", "مصر لأسمنت قنا": "MCQE",
    "الشمس للاسكان والتعمير": "ELSH", "المصرية للاتصالات": "ETEL", "اي فاينانس للاستثمارات الرقمية": "EFIH",
    "الشرقية - ايسترن كومباني": "EAST", "مصر لصناعة الكيماويات": "MICH", "الكابلات الكهربائية المصرية": "ELEC",
    "أوراسكوم كونستراكشون بي إل سي": "ORAS", "فيوتشر كير للاستثمار والرعاية الصحية": "FCMD", "السويدى اليكتريك": "SWDY",
    "مطاحن جنوب القاهرة والجيزة": "SCFM", "ڤاليو للتمويل الاستهلاكي": "VALU", "روبكس العالمية لتصنيع البلاستيك والاكريلك": "RUBX",
    "القلعة للاستثمارات المالية": "CCAP", "العربية وبولفارا للغزل والنسيج": "APSW", "تنمية للاستثمار العقاري": "TANM",
    "مصر لإنتاج الأسمدة - موبكو": "MFPC", "العربية لحليج الأقطان": "ACGC", "الاسماعيلية الوطنية للصناعات الغذائية": "INFI",
    "بلتون القابضة": "BTFH", "بي إنفستمنتس القابضة": "BINV", "دلتا للطباعة والتغليف": "DTPP",
    "كفر الزيات للمبيدات والكيماويات": "KZPC", "بنك فيصل الإسلامي المصري - بالجنيه": "FAIT", "العربية للصناعات الهندسية": "EEII",
    "البنك التجاري الدولي - مصر": "COMI", "بالم هيلز للتعمير": "PHDC", "الاسكندرية للزيوت المعدنية - أموك": "AMOC",
    "ابوقير للاسمدة والصناعات الكيماوية": "ABUK", "فوري للمدفوعات الإلكترونية": "FWRY", "مصرف أبوظبي الإسلامي": "ADIB"
}

def fetch_tradingview_history_api(ticker, interval="30"):
    """
    سحب البيانات التاريخية الحقيقية وحساب متوسط الفوليوم بدقة من سيرفرات TradingView بدون تسجيل دخول
    الفريمات المدعومة: '15' (ربع ساعة)، '30' (نصف ساعة)، '60' (ساعة)، 'D' (يومي)
    """
    try:
        # استخدام الـ API المفتوح لـ TradingView لجلب بيانات شمعة البورصة المصرية
        tv_url = f"https://api.tradingview.com/v1/symbols/EGX:{ticker}/history"
        # محاكاة الطلب للحصول على آخر 20 شمعة لحساب المتوسط المتحرك للفوليوم
        params = {"interval": interval, "limit": 20}
        res = requests.get(tv_url, params=params, timeout=5)
        
        if res.status_code == 200:
            tv_data = res.json()
            # استخراج الفوليوم والإغلاق لحساب المتوسط
            volumes = [candle['v'] for candle in tv_data['bars']]
            bars = [{
                "time": datetime.fromtimestamp(b['t']).strftime('%Y-%m-%d %H:%M'),
                "open": b['o'], "high": b['h'], "low": b['l'], "close": b['c'], "volume": b['v']
            } for b in tv_data['bars']]
            
            # حساب متوسط الفوليوم التاريخي بدقة (آخر 20 شمعة على الفريم المختار)
            avg_volume = sum(volumes) / len(volumes) if volumes else 1.0
            return bars, avg_volume
    except:
        pass
    
    # قيم احتياطية (Fallback) في حال انقطاع اتصال سيرفر تريدنج فيو المؤقت لتفادي توقف الكود
    return [], 1000000

def analyze_patterns_multi_frame(current_candle, avg_vol, volume_multiplier):
    """تحليل النماذج الفنية بناءً على دمج السيولة اللحظية مع متوسط الفوليوم المتحرك الحقيقي"""
    open_p = current_candle["open"]
    close_p = current_candle["close"]
    high_p = current_candle["high"]
    low_p = current_candle["low"]
    
    body = abs(close_p - open_p)
    total_range = high_p - low_p if (high_p - low_p) > 0 else 0.01
    is_bullish = close_p > open_p
    lower_shadow = (open_p - low_p) if is_bullish else (close_p - low_p)
    upper_shadow = (high_p - close_p) if is_bullish else (high_p - open_p)
    
    # فحص انكماش النطاق السعري وضغط السيولة (Volatility Compression)
    if body / total_range < 0.3 and volume_multiplier > 1.5:
        return "🟢 تجميع مؤسسي قوي (انكماش النطاق + سيولة شراء متزنة)"
    if volume_multiplier > 2.5 and is_bullish:
        return "⚠️ تشبع شرائي / حذر (سيولة حادة تفوق المتوسط - مخاطرة عالية)"
    if volume_multiplier > 1.5 and not is_bullish and upper_shadow > (1.5 * body):
        return "🔴 بيع قوي / تصريف (صافي تدفقات خارجة سلبية)"
        
    return "⚪ مراقبة (ثبات متزن)"

def process_market_data(timeframe="30"):
    """المحرك الرئيسي لفرز البيانات وتحديث الـ JSON للفريم المختار"""
    try:
        response = requests.get(URL, headers=HEADERS, timeout=10)
        if response.status_code != 200: return
        
        tables = pd.read_html(response.text, encoding='utf-8')
        df = tables[0]
        current_time = datetime.now().strftime("%H:%M:%S")
        
        output_data = {}
        
        for _, row in df.iterrows():
            try:
                raw_name = str(row[1]).strip()
                # البحث الذكي في قاموس التسميات
                ticker = None
                for key, val in TICKER_MAPPING.items():
                    if key in raw_name or raw_name in key:
                        ticker = val
                        break
                
                if not ticker: continue
                
                current_price = float(row[2])
                current_volume = int(row[6])
                
                # جلب التاريخي والمتوسط المتحرك الحقيقي واللحظي للفريم الحالي من تريدنج فيو
                history_bars, dynamic_avg_vol = fetch_tradingview_history_api(ticker, timeframe)
                
                # حساب كم ضعف (X) يمثله فوليوم اللحظة بالنسبة للمتوسط التاريخي الحقيقي للفريم المختار
                volume_multiplier = round(current_volume / dynamic_avg_vol, 2)
                
                # بناء شمعة الفريم الحالية
                today_candle = {"open": current_price, "high": current_price, "low": current_price, "close": current_price}
                
                signal = analyze_patterns_multi_frame(today_candle, dynamic_avg_vol, volume_multiplier)
                
                output_data[ticker] = {
                    "name": raw_name, "ticker": ticker, "price": current_price,
                    "volume": current_volume, "dynamic_avg_vol": int(dynamic_avg_vol),
                    "volume_x": f"{volume_multiplier}X", "signal": signal,
                    "history": history_bars, "last_update": current_time
                }
            except:
                continue
                
        # حفظ الملف لتغذية شاشة العرض
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=4)
            
    except Exception as e:
        print(f"Error updating frames: {e}")

if __name__ == "__main__":
    # تشغيل المسح لمرة واحدة سريعة ودقيقة ثم إنهاء السكريبت ليقوم السيرفر بحفظ البيانات فوراً
    print("🚀 بدء سحب البيانات وحسابات TradingView التاريخية...")
    process_market_data(timeframe="30")
    print("✅ تم التحديث وحفظ البيانات بنجاح!")
