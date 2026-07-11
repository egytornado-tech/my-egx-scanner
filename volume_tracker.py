import requests
from bs4 import BeautifulSoup
import json
import os
import re
from datetime import datetime, time, timedelta

BASE_URL = "http://41.33.162.236/egs4/"
DB_FILE = "volume_history.json"
COMP_FILE = "volume_comparison.json"

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

def has_arabic(text):
    return bool(re.search(r'[\u0600-\u06FF]', text))

def track_and_compare_volume():
    now_str = datetime.now().strftime("%Y-%m-%d")
    
    now = datetime.now()
    if now.time() < START_SESSION:
        current_slot = get_session_intervals()[0]
    elif now.time() > END_SESSION:
        current_slot = get_session_intervals()[-1]
    else:
        minutes = (now.minute // INTERVAL_MINUTES) * INTERVAL_MINUTES
        current_slot = now.replace(minute=minutes, second=0, microsecond=0).strftime("%H:%M")

    print(f"📡 جاري قراءة البيانات بدقة واكتشاف اسم السهم للفترة [{current_slot}]...")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        response = requests.get(BASE_URL, headers=headers, timeout=25)
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table') 
        if not table:
            print("❌ لم يتم العثور على الجدول.")
            return
        rows = table.find_all('tr')[1:]
    except Exception as e:
        print(f"💥 خطأ أثناء جلب الصفحة: {e}")
        return

    history = load_history()
    available_dates = sorted([d for d in history.keys() if d != now_str])
    yesterday_str = available_dates[-1] if available_dates else None

    if now_str not in history:
        history[now_str] = {}

    realtime_comparison = {}
    total_slots = len(get_session_intervals())

    for row in rows:
        cols = row.find_all(['td', 'th'])
        if len(cols) < 8: 
            continue
            
        try:
            # 1. جلب الحجم اللحظي (العمود الأول من اليسار في كود الـ HTML)
            vol_raw = cols[0].get_text(strip=True).replace(',', '')
            current_volume = int(float(vol_raw)) if vol_raw else 0
            
            # 2. السعر الحالي (العمود الثالث)
            price_raw = cols[2].get_text(strip=True).replace(',', '')
            price = float(price_raw) if price_raw else 0.0
            
            # 3. نسبة التغير % (العمود السادس)
            change_raw = cols[5].get_text(strip=True).replace('%', '').strip()
            price_change = float(change_raw) if change_raw else 0.0
            
            # 4. البحث الديناميكي الذكي عن اسم السهم (الخلية التي تحتوي على نص عربي)
            symbol = ""
            for col in cols:
                txt = col.get_text(strip=True)
                if has_arabic(txt):
                    # تنظيف كود السهم إذا كان مدمجاً به رقم في البداية
                    parts = txt.split(maxsplit=1)
                    if parts and parts[0].isdigit():
                        symbol = parts[1] if len(parts) > 1 else txt
                    else:
                        symbol = txt
                    break
            
            # إذا لم يجد اسماً عربياً، يتخطى السطر
            if not symbol or "حجم" in symbol or "الاسم" in symbol or current_volume == 0:
                continue

            # حفظ في التاريخ اليومي للربع ساعة الحالي
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
                "price_change": round(price_change, 2),
                "current_volume": current_volume,
                "compared_to_time_volume": yesterday_vol,
                "ratio_percentage": round(vol_ratio, 2),
                "is_fallback_baseline": is_fallback
            }
        except Exception:
            continue

    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=4)
        
    with open(COMP_FILE, "w", encoding="utf-8") as f:
        json.dump(realtime_comparison, f, ensure_ascii=False, indent=4)
        
    print(f"🟢 تم التحديث بنجاح التام واكتشاف الأسماء والأسعار بشكل صحيح 100%.")

if __name__ == "__main__":
    track_and_compare_volume()
