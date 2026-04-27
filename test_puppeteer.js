const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  await page.goto('http://localhost:8080/ui/index.html');
  await page.waitForTimeout(2000);
  
  // click chart analysis
  await page.evaluate(() => {
    navigate('chart');
  });
  await page.waitForTimeout(2000);
  
  const metrics = await page.evaluate(() => {
    const aiSection = document.querySelector('.ai-analysis-content');
    const panelCard = aiSection ? aiSection.closest('.panel-card') : null;
    return {
      aiSectionExists: !!aiSection,
      panelCardExists: !!panelCard,
      aiSectionRect: aiSection ? aiSection.getBoundingClientRect() : null,
      panelCardRect: panelCard ? panelCard.getBoundingClientRect() : null,
      documentHeight: document.body.scrollHeight,
      windowHeight: window.innerHeight
    };
  });
  console.log(JSON.stringify(metrics, null, 2));
  await browser.close();
})();
