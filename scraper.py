# إذا فشل السكريبت في جلب داتا حقيقية من السيرفر، سنقوم بطباعة السبب في الـ Logs لتراه بعينك
    if not output_data:
        print("❌ تذكير فني: السكريبت لم يجد بيانات حقيقية داخل جدول السيرفر المحلي.")
        try:
            test_res = requests.get(LOCAL_URL, headers=HEADERS, timeout=5)
            print(f"📡 حالة استجابة سيرفرك الآن هي: {test_res.status_code}")
            if test_res.status_code != 200:
                print("💡 السبب: سيرفرك المحلي مغلق حالياً أو يرفض اتصال جيت هاب خارج أوقات الجلسة.")
        except Exception as conn_error:
            print(f"🚨 فشل الاتصال تماماً بسيرفرك (Timeout/Connection Refused): {conn_error}")

        # بناء الجدول الاحتياطي مؤقتاً لمنع انهيار الموقع
        for tck, name in {"COMI": "التجاري الدولي", "FWRY": "فوري", "TMGH": "طلعت مصطفى"}.items():
            output_data[tck] = {
                "name": name, "ticker": tck, "price": 0.0, "volume": 0, "dynamic_avg_vol": 1,
                "volume_x": "0X", "signal": "💤 السوق مغلق حالياً — بانتظار بدء الجلسة", "history": [], "last_update": current_time
            }

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)
    print("🚀 تم تحديث ملف egx_market_data.json بنجاح تام!")
