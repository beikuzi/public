'use strict';
// Optional sandbox-required browser QA helper.
// Syntax-checked only for this source release. Do not weaken sandboxing.
const {chromium}=require('playwright');
(async()=>{
  if(process.env.ALLOW_SANDBOXED_SITE_QA!=='1')throw Error('Browser QA disabled. Use only in an environment where sandboxed browser access to this preview is permitted.');
  const base=process.env.SITE_QA_BASE_URL;
  if(!base)throw Error('Provide the authorized preview URL explicitly.');
  const browser=await chromium.launch({headless:true,chromiumSandbox:true});
  try{
    const page=await browser.newPage({viewport:{width:1440,height:1000}});
    const errors=[];page.on('pageerror',err=>errors.push(err.message));
    for(const style of ['editorial','transit','console','atlas'])for(const platform of ['summary','bilibili','xiaohongshu','weibo','douyin','x','wechat']){
      const url=new URL(`/${style}/${platform}/`,base).href;
      const response=await page.goto(url);
      if(!response?.ok())throw Error(`Route unavailable: ${url}`);
      await page.waitForSelector('#result-count');
      if(await page.locator('.platform-nav a').count()!==7)throw Error('Navigation count mismatch.');
    }
    if(errors.length)throw Error(errors.join('\n'));
    console.log('Sandboxed browser route checks passed.');
  }finally{await browser.close();}
})().catch(error=>{console.error(error.message);process.exitCode=1;});
