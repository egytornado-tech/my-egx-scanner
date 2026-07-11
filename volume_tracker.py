import requests
import json
import os
from datetime import datetime, time, timedelta

# إعدادات الرادار والـ API
API_URL = "https://egxpilot.com/api/stocks/all/"
DB_FILE = "volume_history.json"

# تحديد أوقات جلسة البورصة المصرية (10:00 ص إلى 2:30 ظهراً)
START_SESSION = time(10, 0)
END_SESSION = time(14, 30)
INTERVAL_MINUTES = 15

def get_session_intervals():
    """توليد مواقيت الربع ساعة لجلسة التداول الحالية"""
    intervals = []
    current = datetime.combine(datetime.today(), START_SESSION)
    end = datetime.combine(datetime.today(), END_SESSION)
    while current <= end:
        intervals.append(current.strftime("%H:%M"))
        current += timedelta(minutes=INTERVAL_MINUTES)
    return intervals

def load_history():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_history(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def get_current_interval_slot():
    """تحديد أقرب ربع ساعة مرت في الجلسة الحالية"""
    now = datetime.now()
    if now.time() < START_SESSION:
        return None
    if now.time() > END_SESSION:
        return get_session_intervals()[-1]
    
    # التقريب لأقرب ربع ساعة مضت
    minutes = (now.minute // INTERVAL_MINUTES) * INTERVAL_MINUTES
    return now.replace(minute=minutes, second=0, microsecond=0).strftime("%H:%M")

def track_and_compare_volume():
    now_str = datetime.now().strftime("%Y-%m-%d")
    current_slot = get_current_interval_slot()
    
    if not current_slot:
        print("⏰ خارج أوقات تتبع الجلسة اللحظية حالياً.")
        return

    print(f"📡 سحب أحجام التداول اللحظية للفترة: [{current_slot}]...")
    
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(API_URL, headers=headers, timeout=12)
        if response.status_code != 200:
            print(f"❌ فشل الاتصال بالـ API: {response.status_code}")
            return
        
        all_stocks = response.json()
        stocks_list = all_stocks if isinstance(all_stocks, list) else all_stocks.values()
    except Exception as e:
        print(f"💥 خطأ في الشبكة: {e}")
        return

    history = load_history()
    
    # استخراج تاريخ اليوم السابق المتاح في التخزين
    available_dates = sorted([d for d in history.keys() if d != now_str])
    yesterday_str = available_dates[-1] if available_dates else None

    # تجهيز هيكل اليوم الحالي في قاعدة البيانات
    if now_str not in history:
        history[now_str] = {}

    realtime_comparison = {}
    all_intervals = get_session_intervals()
    total_slots = len(all_intervals)

    for stock in stocks_list:
        symbol = stock.get("symbol") or stock.get("code")
        if not symbol:
            continue
            
        # حجم التداول التراكمي الحالي من السيرفر
        current_volume = int(stock.get("volume", 0))
        
        # حفظ الحجم الحالي للفترة الحالية لليوم
        history[now_str][symbol] = history[now_str].get(symbol, {})
        history[now_str][symbol][current_slot] = current_volume

        # حساب المقارنة مع الأمس
        yesterday_vol = 0
        is_fallback = False

        if yesterday_str and symbol in history[yesterday_str]:
            # إذا كانت بيانات الأمس مخزنة بالكامل، نجلب حجم نفس الربع ساعة
            yesterday_vol = history[yesterday_str][symbol].get(current_slot, 0)
        
        # خطة الطوارئ: أول يوم تشغيل ومفيش بيانات مخزنة للأمس
        if yesterday_vol == 0:
            is_fallback = True
            # توزيع الحجم التراكمي الحالي بالتساوي على عدد فترات الجلسة
            yesterday_vol = int(current_volume / total_slots)

        # حساب النسبة المئوية للحجم مقارنة بالأمس في نفس التوقيت
        if yesterday_vol > 0:
            vol_ratio = (current_volume / yesterday_vol) * 100
        else:
            vol_ratio = 100.0

        realtime_comparison[symbol] = {
            "current_volume": current_volume,
            "compared_to_time_volume": yesterday_vol,
            "ratio_percentage": round(vol_ratio, 2),
            "is_fallback_baseline": is_fallback
        }

    # حفظ السجلات المحدثة
    save_history(history)
    
    # طباعة تقرير الأداء اللحظي المقارن في الـ Logs
    print(f"📊 --- تقرير مقارنة الأحجام لـ {total_slots} فترات (ربع سنوية) ---")
    for sym, metrics in list(realtime_comparison.items())[:10]:  # عرض أول 10 أسهم كمثال
        status_tag = "[تقديري]" if metrics["is_fallback_baseline"] else "[حقيقي]"
        print(f"🔹 السهم: {sym:<8} | اللحظي: {metrics['current_volume']:,} | أمس: {metrics['compared_to_time_volume']:,} {status_tag} | النسبة: {metrics['ratio_percentage']}%")

if __name__ == "__main__":
    track_and_compare_volume()
