import requests
from bs4 import BeautifulSoup
import json
import os
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

def track_and_compare_volume():
    now_str = datetime.now().strftime("%Y-%m-%d")
    
    # تحديد توقيت الربع ساعة الحالي
    now = datetime.now()
    if now.time() < START_SESSION:
        current_slot = get_session_intervals()[0]
    elif now.time() > END_SESSION:
        current_slot = get_session_intervals()[-1]
    else:
        minutes = (now.minute // INTERVAL_MINUTES) * INTERVAL_MINUTES
        current_slot = now.replace(minute=minutes, second=0, microsecond=0).strftime("%H:%M")

    print(f"📡 جاري قراءة البيانات الحية من egs4 للفترة [{current_slot}]...")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        response = requests.get(BASE_URL, headers=headers, timeout=25)
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table') 
        if not table:
            print("❌ لم يتم العثور على جدول في الصفحة.")
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
        if len(cols) < 3: 
            continue
            
        try:
            # 🎯 تنظيف اسم السهم حتى لو كان داخل وسم <a> أو يحتوي على مسافات غريبة
            symbol = cols[1].get_text(strip=True)
            
            # تنظيف وتحويل الحجم والسعر بأمان
            vol_raw = cols[0].get_text(strip=True).replace(',', '')
            current_volume = int(float(vol_raw)) if vol_raw else 0
            
            price_raw = cols[2].get_text(strip=True).replace(',', '')
            price = float(price_raw) if price_raw else 0.0
            
            # تخطي السطور غير الصالحة أو الفارغة
            if not symbol or "حجم" in symbol or "الاسم" in symbol or current_volume == 0:
                continue

            # تأمين هيكل الـ JSON للسهم
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
        except Exception as row_error:
            # تخطي أي سهم به مشكلة ومتابعة باقي الجدول لمنع توقف السكريبت
            continue

    # 💾 الإجبار على حفظ الملفات مهما كانت الظروف
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=4)
        
    with open(COMP_FILE, "w", encoding="utf-8") as f:
        json.dump(realtime_comparison, f, ensure_ascii=False, indent=4)
        
    print(f"🟢 تم إنشاء وتحديث ملف {COMP_FILE} بنجاح تام.")

if __name__ == "__main__":
    track_and_compare_volume()
