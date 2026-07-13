const axios = require('axios');
const cheerio = require('cheerio');
const fs = require('fs');

// دالة لجلب بيانات البورصة وكشطها (Scraping)
async function runScanner() {
    console.log('جاري بدء السكّانر وجلب البيانات اللحظية من البورصة المصرية...');
    
    try {
        // الرابط اللحظي الذي تعتمد عليه لجلب البيانات
        const url = 'https://www.egx.com.eg/ar/MarketSummary.aspx'; // كمثال للمصدر، يمكنك استبداله برابط مصدر بياناتك المباشر
        const response = await axios.get(url, {
            headers: {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        });

        const $ = cheerio.load(response.data);
        const stockData = [];

        // هنا يتم كشط البيانات (اسم السهم، السعر، الحجم المنفذ) بناءً علىโครงสร้าง الجدول الخاص بك
        // تأكد من ضبط الـ selectors (الأكواد الجانبية) لتطابق جدول بياناتك تماماً
        $('table tr').each((index, element) => {
            if (index === 0) return; // تخطي السطر الأول (العناوين)

            const row = $(element);
            const name = row.find('td').eq(0).text().trim();  // اسم السهم
            const price = row.find('td').eq(1).text().trim(); // السعر الحالي
            const volume = row.find('td').eq(2).text().trim(); // الحجم المنفذ

            if (name && price) {
                stockData.push({
                    name: name,
                    price: price,
                    volume: volume,
                    updatedAt: new Date().toLocaleTimeString('ar-EG', { timeZone: 'Africa/Cairo' })
                });
            }
        });

        if (stockData.length === 0) {
            console.log('⚠️ تحذير: لم يتم العثور على بيانات أسهم، تأكد من الـ selectors أو رابط المصدر.');
            return;
        }

        // حفظ البيانات المستخرجة في ملف JSON لتحديث الاندكس أو لوحة التحكم الخاصة بك
        fs.writeFileSync('data.json', JSON.stringify(stockData, null, 2), 'utf-8');
        console.log(`✅ تم جلب وتحديث بيانات (${stockData.length}) سهم بنجاح وحفظها في data.json`);

    } catch (error) {
        console.error('❌ خطأ أثناء تشغيل السكّانر وجلب البيانات:', error.message);
        process.exit(1); // إنهاء التشغيل بكود خطأ ليظهر في GitHub Actions
    }
}

// تشغيل السكّانر مباشرة عند استدعاء الملف بواسطة Node.js
runScanner();
