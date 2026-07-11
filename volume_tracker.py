import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime, time, timedelta

BASE_URL = "http://41.33.162.236/egs4/"
DB_FILE = "volume_history.json"

START_SESSION = time(10, 0)
END_SESSION = time(14, 30)
INTERVAL_MINUTES = 15

def get_session_intervals():
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
            try:
                return json.load(f)
            except Exception:
                return {}
    return {}

def save_history(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def get_current_interval_slot():
    now = datetime.now()
    if now.time() < START_SESSION:
        return None
    if now.time() > END_SESSION:
        return get_session_intervals()[-1]
    
    minutes = (now.minute // INTERVAL_MINUTES) * INTERVAL_MINUTES
    return now.replace(minute=minutes, second=0, microsecond=0).strftime("%H:%M")

def clean_int(text):
    """تنظيف النصوص وتحويلها لـ int بأمان بدون كراش"""
    try:
        t = text.strip().replace(',', '')
        if not t or any(c.isalpha() for c in t): # لو فيها حروف أو فاضية
            return 0
        return int(float(t))
    except Exception:
        return 0

def clean_float(text):
    """تنظيف النصوص وتحويلها لـ float بأمان بدون كراش"""
    try:
        t = text.strip().replace(',', '')
        if not t or any(c.isalpha() for c in t):
            return 0.0
        return float(t)
    except Exception:
        return 0.0

def track_and_compare_volume():
    now_str = datetime.now().strftime("%Y-%m-%d")
    current_slot = get_current_interval_slot()
    
    if not current_slot:
        print("⏰ خارج أوقات الجلسة. يتم السحب لآخر إغلاق معروض.")
        current_slot = get_session_intervals()[-1]

    print(f"🕵️‍♂️ بدء السكرابينج الآمن من: {BASE_URL} للفترة [{current_slot}]...")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "text/html"
    }
    
    try:
        response = requests.get(BASE_URL, headers=headers, timeout=20)
        if response.status_code != 200:
            print(f"❌ السيرفر رجع كود خطأ: {response.status_code}")
            return
            
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table') 
        if not table:
            print("❌ لم يتم العثور على أي جدول في الصفحة.")
            return
            
        rows = table.find_all('tr')[1:]
    except Exception as e:
        print(f"💥 فشل الاتصال بالسيرفر: {e}")
        return

    history = load_history()
    available_dates = sorted([d for d in history.keys() if d != now_str])
    yesterday_str = available_dates[-1] if available_dates else None

    if now_str not in history:
        history[now_str] = {}

    realtime_comparison = {}
    all_intervals = get_session_intervals()
    total_slots = len(all_intervals)

    for row in rows:
        cols = row.find_all(['td', 'th'])
        if len(cols) < 3: 
            continue
            
        symbol = cols[1].text.strip()
        
        # حماية قراءة الداتا من الكراش باستخدام دوال التنظيف الآمنة
        current_volume = clean_int(cols[0].text)
        price = clean_float(cols[2].text)

        # تخطي السطور الفاضية أو سطور العناوين المكررة داخل الجدول
        if not symbol or "حجم" in symbol or "الاسم" in symbol or current_volume == 0:
            continue
            
        if symbol not in history[now_str]:
            history[now_str][symbol] = {}
        history[now_str][symbol][current_slot] = current_volume

        yesterday_vol = 0
        is_fallback = False

        if yesterday_str and symbol in history[yesterday_str]:
            yesterday_vol = history[yesterday_str][symbol].get(current_slot, 0)
        
        if yesterday_vol == 0:
            is_fallback = True
            yesterday_vol = int(current_volume / total_slots)

        vol_ratio = (current_volume / yesterday_vol) * 100 if yesterday_vol > 0 else 100.0

        realtime_comparison[symbol] = {
            "name": symbol,
            "price": price,
            "current_volume": current_volume,
            "compared_to_time_volume": yesterday_vol,
            "ratio_percentage": round(vol_ratio, 2),
            "is_fallback_baseline": is_fallback
        }

    # حفظ السجلات الأساسية
    save_history(history)
    
    # 🎯 الخطوة الأهم: حفظ حزمة المقارنة الصافية اللي بتدور عليها الصفحة
    with open("volume_comparison.json", "w", encoding="utf-8") as f:
        json.dump(realtime_comparison, f, ensure_ascii=False, indent=4)
        
    print(f"🟢 نجاح تام: تم تكوين ملف volume_comparison.json بنجاح وبدون أي كراش.")

if __name__ == "__main__":
    track_and_compare_volume()
