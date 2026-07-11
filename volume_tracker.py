import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime, time, timedelta

# الرابط الأصلي المباشر لصفحة الويب الحية
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
        print("⏰ خارج أوقات الجلسة. يتم عمل سكرابينج لآخر إغلاق معروض بالصفحة.")
        current_slot = get_session_intervals()[-1]

    print(f"🕵️‍♂️ بدء عمل سكرابينج لصفحة EGX4 المباشرة: {BASE_URL}...")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml"
    }
    
    try:
        response = requests.get(BASE_URL, headers=headers, timeout=20)
        print(f"📊 كود استجابة السيرفر: {response.status_code}")
        
        if response.status_code != 200:
            print("❌ فشل تحميل الصفحة الحية من السيرفر.")
            return
            
        # فك تشفير الصفحة وقراءتها عبر BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # البحث عن جدول الأسهم (تعديل الـ selector بناءً على بنية الجدول في egs4)
        # الكود يبحث عن أول جدول أو جدول يحمل كلاس الأسهم
        table = soup.find('table') 
        if not table:
            print("❌ لم يتم العثور على أي جدول بيانات داخل الصفحة الحية.")
            return
            
        rows = table.find_all('tr')[1:] # تخطي سطر العناوين (Header)
        print(f"📈 تم العثور على {len(rows)} سطر داخل جدول الأسهم.")
        
    except Exception as e:
        print(f"💥 فشل السكرابينج والاتصال بالسيرفر: {e}")
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
        if len(cols) < 3: # التأكد من وجود خلايا كافية (اسم، سعر، حجم)
            continue
            
        # استخراج اسم السهم، السعر، والحجم من الخلايا بناءً على ترتيب الأعمدة
        # افتراضياً: الاسم العمود 0، السعر 1، الحجم 2 (تعديل الاندكس لو الترتيب مختلف عندك)
        symbol = cols[0].text.strip()
        
        try:
            price_text = cols[1].text.strip().replace(',', '')
            price = float(price_text) if price_text else 0.0
            
            vol_text = cols[2].text.strip().replace(',', '')
            current_volume = int(float(vol_text)) if vol_text else 0
        except ValueError:
            continue # تخطي السطور التي لا تحتوي على أرقام صافية

        if not symbol:
            continue
            
        if symbol not in history[now_str]:
            history[now_str][symbol] = {}
        history[now_str][symbol][current_slot] = current_volume

        yesterday_vol = 0
        is_fallback = False

        if yesterday_str and symbol in history[yesterday_str]:
            yesterday_vol = history[yesterday_str][symbol].get(current_slot, 0)
        
        # قاعدة اليوم الأول: التقسيم بالتساوي على 18 فترة لجلسة التداول
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
    
    # تصدير ملف المقارنة الصافي لتقرأه واجهة المستخدم الخاصة بك
    with open("volume_comparison.json", "w", encoding="utf-8") as f:
        json.dump(realtime_comparison, f, ensure_ascii=False, indent=4)
        
    print(f"🟢 تم السكرابينج بنجاح ومطابقة أحجام تداول الأسهم مع توقيت ربع الساعة.")

if __name__ == "__main__":
    track_and_compare_volume()
