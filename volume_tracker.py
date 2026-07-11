import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime, time, timedelta

# الرابط والـ IP الأصلي الصحيح 100%
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
            return json.load(f)
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

def track_and_compare_volume():
    now_str = datetime.now().strftime("%Y-%m-%d")
    current_slot = get_current_interval_slot()
    
    if not current_slot:
        print("⏰ خارج أوقات الجلسة. يتم السحب لآخر إغلاق معروض.")
        current_slot = get_session_intervals()[-1]

    print(f"🕵️‍♂️ جاري عمل سكرابينج بناءً على الانديكس المعتمد من الصورة للرابط: {BASE_URL}...")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "text/html,application/xhtml+xml,application/xml"
    }
    
    try:
        response = requests.get(BASE_URL, headers=headers, timeout=20)
        if response.status_code != 200:
            print("❌ فشل تحميل الصفحة من السيرفر.")
            return
            
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table') 
        if not table:
            print("❌ لم يتم العثور على جدول البيانات.")
            return
            
        rows = table.find_all('tr')[1:] # تخطي صف العناوين
        
    except Exception as e:
        print(f"💥 فشل السكرابينج: {e}")
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
            
        # 🎯 الاعتماد الصارم للانديكس بناءً على الصورة المرسلة:
        try:
            # الانديكس 1: الاسم المختصر
            symbol = cols[1].text.strip()
            
            # الانديكس 0: حجم التداول
            vol_text = cols[0].text.strip().replace(',', '')
            current_volume = int(float(vol_text)) if vol_text else 0
            
            # الانديكس 2: آخر سعر
            price_text = cols[2].text.strip().replace(',', '')
            price = float(price_text) if price_text else 0.0
            
        except (ValueError, IndexError):
            continue 

        if not symbol:
            continue
            
        if symbol not in history[now_str]:
            history[now_str][symbol] = {}
        history[now_str][symbol][current_slot] = current_volume

        yesterday_vol = 0
        is_fallback = False

        if yesterday_str and symbol in history[yesterday_str]:
            yesterday_vol = history[yesterday_str][symbol].get(current_slot, 0)
        
        # قاعدة اليوم الأول (الحجم الحالي / 18 فترة بالتساوي)
        if yesterday_vol == 0:
            is_fallback = True
            yesterday_vol = int(current_volume / total_slots)

        if yesterday_vol > 0:
            vol_ratio = (current_volume / yesterday_vol) * 100
        else:
            vol_ratio = 100.0

        realtime_comparison[symbol] = {
            "name": symbol,
            "price": price,
            "current_volume": current_volume,
            "compared_to_time_volume": yesterday_vol,
            "ratio_percentage": round(vol_ratio, 2),
            "is_fallback_baseline": is_fallback
        }

    save_history(history)
    
    # حفظ حزمة المقارنة لواجهة المستخدم
    with open("volume_comparison.json", "w", encoding="utf-8") as f:
        json.dump(realtime_comparison, f, ensure_ascii=False, indent=4)
        
    print(f"🟢 تم السحب وحفظ المطابقة ربع السنوية بنجاح.")

if __name__ == "__main__":
    track_and_compare_volume()
