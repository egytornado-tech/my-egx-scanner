import requests
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # تفعيل CORS للسماح لصفحة الـ HTML بالاتصال بالسيرفر المحلي

# الـ Headers والـ Token الأمني الخاص بك لتخطي جدار حماية السيرفر
SECURE_HEADERS = {
    "accept": "application/json",
    "accept-language": "en-US,en;q=0.9,ar;q=0.8,ru;q=0.7",
    "authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI5MDg5MDgxMTkiLCJuYW1lIjoiTW9zdGFmYSIsImV4cCI6MTc4NDAyNzUzNX0.OMXE07QPfiBYBAe6ODI-wn1MArWp7MyyrkLjrhcDMq4",
    "priority": "u=1, i",
    "sec-ch-ua": '"Google Chrome";v="149", "Chromium";v="149", "Not)A;Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin"
}

@app.route('/api/radar', methods=['GET'])
def get_hybrid_radar():
    symbol = "ARCC"
    borsa_url = f"https://egxbot.com/api/Market/getOrderBook?symbol={symbol}"
    
    # 1. جلب عمق السوق من السيرفر مباشرة لتخطي حظر المتصفح (CORS)
    depth_data = {}
    try:
        response = requests.get(borsa_url, headers=SECURE_HEADERS, timeout=5)
        if response.status_code == 200:
            depth_data = response.json()
    except Exception as e:
        print(f"Error fetching depth: {e}")

    # 2. جلب صفقات الماركت والأسعار اللحظية من قاعدة بيانات V12 المحلية الخاصة بك
    # (قم باستبدال هذه البيانات الوهمية بآلية السحب الفعلية من الكور الخاص بك)
    local_trades = [
        {"time": "14:28:10", "price": 18.37, "volume": 212565, "side": "buy"},
        {"time": "14:25:15", "price": 18.35, "volume": 5000, "side": "sell"}
    ]
    
    # دمج كتل البيانات في استجابة واحدة موحدة للواجهة
    return jsonify({
        "status": "connected",
        "symbol": symbol,
        "depth": depth_data,  # يحتوي على مصفوفات buy و sell الحقيقية لبورصجي
        "lastPrice": 18.37,
        "changePercent": 0.88,
        "trades": local_trades
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
