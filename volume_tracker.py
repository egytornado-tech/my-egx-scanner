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

def get_last_working_day(history, now_str):
    available_dates = sorted([d for d in history.keys() if d != now_str])
    if not available_dates:
        return None
    for date_str in reversed(available_dates):
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            if dt.weekday() not in [4, 5]: 
                return date_str
        except ValueError:
            continue
    return available_dates[-1] if available_dates else None

def track_and_compare_volume():
    try:
        utc_now = datetime.utcnow()
        egypt_now = utc_now + timedelta(hours=3) 
        
        now_str = egypt_now.strftime("%Y-%m-%d")
        all_slots = get_session_intervals()
        total_slots_count = len(all_slots) 
        
        if egypt_now.time() < START_SESSION:
            current_slot = all_slots[0]
            current_slot_index = 1
        elif egypt_now.time() > END_SESSION:
            current_slot = all_slots[-1]
            current_slot_index = total_slots_count
        else:
            minutes = (egypt_now.minute // INTERVAL_MINUTES) * INTERVAL_MINUTES
            current_slot = egypt_now.replace(minute=minutes, second=0, microsecond=0).strftime("%H:%M")
            current_slot_index = all_slots.index(current_slot) + 1

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
            print(f"💥 خطأ في جلب الصفحة: {e}")
            return

        history = load_history()
        yesterday_str = get_last_working_day(history, now_str)

        if now_str not in history:
            history[now_str] = {}

        output_data = {
            "scrape_time": egypt_now.strftime("%H:%M:%S"),
            "stocks": {}
        }

        for row in rows:
            cols = [c.get_text(strip=True) for c in row.find_all(['td', 'th'])]
            if len(cols) < 7: 
                continue
                
            try:
                # 1. جلب اسم السهم بالتأكيد من أول خانة عربية
                symbol = ""
                for txt in cols:
                    if has_arabic(txt) and "حجم" not in txt and "الاسم" not in txt:
                        parts = txt.split(maxsplit=1)
                        if parts and parts[0].isdigit():
                            symbol = parts[1] if len(parts) > 1 else txt
                        else:
                            symbol = txt
                        break
                
                if not symbol:
                    continue

                # 2. جلب الحجم الحالي (العمود الأخير دائماً)
                vol_raw = cols[-1].replace(',', '')
                current_cumulative_volume = int(float(vol_raw)) if vol_raw.replace('.','',1).isdigit() else 0
                
                # 3. إرجاع جلب السعر بناءً على موقعه الصحيح (العمود الثالث - إندكس 2) وننظفه من أي رغوة نصية
                price_raw = cols[2].replace(',', '').strip()
                if not price_raw or not price_raw.replace('.','',1).isdigit():
                    price_raw = "0.0"
                
                # 4. جلب نسبة التغير السعري بدقة (العمود السادس - إندكس 5) وحذف الـ % لو جيت هاب قراها
                change_raw = cols[5].replace('%', '').replace('+', '').strip()
                try:
                    price_change = float(change_raw)
                except:
                    price_change = 0.0

                if symbol not in history[now_str]:
                    history[now_str][symbol] = {}
                
                if current_slot not in history[now_str][symbol]:
                    history[now_str][symbol][current_slot] = current_cumulative_volume

                yesterday_target_volume = 0

                # جلب حجم نفس السلوت من داتا أمس
                if yesterday_str and symbol in history[yesterday_str]:
                    yesterday_target_volume = history[yesterday_str][symbol].get(current_slot, 0)
                
                # حساب الوزن النسبي لو مفيش سلوت حقيقي مسجل لأمس
                if yesterday_target_volume == 0 and yesterday_str and symbol in history[yesterday_str]:
                    yesterday_slots = history[yesterday_str][symbol]
                    if yesterday_slots:
                        yesterday_total_volume = max(yesterday_slots.values())
                        if current_slot_index >= total_slots_count:
                            yesterday_target_volume = yesterday_total_volume
                        else:
                            yesterday_target_volume = int(yesterday_total_volume * (current_slot_index / total_slots_count))

                if yesterday_target_volume == 0:
                    yesterday_target_volume = int(current_cumulative_volume * (current_slot_index / total_slots_count)) if current_slot_index < total_slots_count else current_cumulative_volume
                
                if yesterday_target_volume == 0: yesterday_target_volume = 1
                vol_ratio = (current_cumulative_volume / yesterday_target_volume) * 100

                output_data["stocks"][symbol] = {
                    "name": symbol,
                    "price": price_raw, 
                    "price_change": round(price_change, 2),
                    "current_volume": current_cumulative_volume,
                    "compared_to_time_volume": yesterday_target_volume,
                    "ratio_percentage": round(vol_ratio, 2)
                }
            except Exception:
                continue

        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=4)
            
        with open(COMP_FILE, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=4)
            
        print(f"🟢 تم ضبط نسبة التغير والسعر بنجاح تام.")
        
    except Exception as main_err:
        print(f"❌ خطأ حرج: {main_err}")

if __name__ == "__main__":
    track_and_compare_volume()
