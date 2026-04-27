const puppeteer = require('puppeteer');
(async () => {
  try {
    const browser = await puppeteer.launch();
    const page = await browser.newPage();
    page.on('console', msg => console.log('BROWSER LOG:', msg.text()));
    await page.goto('http://localhost:8080/ui/index.html');
    await page.waitForTimeout(1000);
    await page.evaluate(() => navigate('chart'));
    await page.waitForTimeout(1000);
    const box = await page.evaluate(() => {
        const btn = document.getElementById('btn-generate-ai-analysis');
        if (btn) btn.click();
        const el = document.getElementById('ai-analysis-content');
        return el ? el.getBoundingClientRect() : null;
    });
    console.log("Box:", box);
    await page.waitForTimeout(2000);
    const text = await page.evaluate(() => {
        const el = document.getElementById('ai-analysis-content');
        return el ? el.innerText : null;
    });
    console.log("Text inside:", text);
    await browser.close();
  } catch (e) {
    console.error(e);
  }
})();
