const {chromium}=require(process.env.LIFELINETWIN_PLAYWRIGHT || 'playwright');
const fs=require('node:fs');
const path=require('node:path');
(async()=>{
 const directory=path.resolve('evidence/continuity-release');fs.mkdirSync(directory,{recursive:true});
 const browser=await chromium.launch({channel:'msedge',headless:true});
 const page=await browser.newPage({viewport:{width:1440,height:1100}});
 const errors=[];page.on('pageerror',error=>errors.push(error.message));
 const results=[];
 try {
  await page.goto('http://127.0.0.1:5173/',{waitUntil:'domcontentloaded'});
  await page.getByRole('heading',{name:'Keep care within reach.'}).waitFor();
  await page.getByLabel('Hospital record').waitFor({timeout:90000});
  const metadata=await (await page.request.get('http://127.0.0.1:5173/api/continuity/regions',{timeout:90000})).json();
  if(metadata.some(r=>!r.ready))throw Error('One or more pilot regions not ready');
  await page.screenshot({path:path.join(directory,'overview.png')});
  for(const region of ['houston','alabama']) {
   if(region==='alabama')await page.getByRole('button',{name:/West Alabama.*Tuscaloosa/}).click();
   const data=metadata.find(r=>r.id===region);
   await page.getByLabel('Hospital record').waitFor();
   await page.getByLabel('Hospital record').selectOption(data.facilities.find(f=>region==='houston'?f.name.includes('Ben Taub'):f.name.includes('DCH Regional')).id);
   await page.getByText('Compare a temporary service location or attach an alert',{exact:true}).click();
   const site=data.communities.find(c=>region==='alabama'?c.name==='Moundville':c.name==='Southgate');
   if(!site)throw Error('Expected named place missing in '+region);
   await page.getByLabel('Proposed temporary service point').selectOption(site.id);
   const responsePromise=page.waitForResponse(r=>r.url().endsWith('/continuity/cases')&&r.request().method()==='POST',{timeout:90000});
   await page.getByRole('button',{name:'Assess access & save brief'}).click();
   const response=await responsePromise;
   const record=await response.json();
   if(response.status()!==201)throw Error(JSON.stringify(record));
   await page.getByRole('link',{name:'Export brief'}).waitFor();
   await page.getByRole('button',{name:'Assess access & save brief',exact:true}).waitFor();
   await page.locator('.result-panel').evaluate(element=>element.scrollIntoView({block:'start'}));
   await page.screenshot({path:path.join(directory,`${region}-case.png`)});
   const exported=await page.request.get(`http://127.0.0.1:5173/api/continuity/cases/${record.id}/brief`);
   if(exported.status()!==200)throw Error('Brief export failed');
   fs.writeFileSync(path.join(directory,`${region}-brief.md`),await exported.text());
   fs.writeFileSync(path.join(directory,`${region}-case.json`),JSON.stringify(record,null,2));
   results.push({region,id:record.id,summary:record.result.summary,alternatives:record.result.alternatives.map(a=>({kind:a.kind,reconnected:a.reconnected_communities,saved_m:a.distance_saved_m}))});
   await page.reload();
   await page.getByRole('button').filter({hasText:record.request.title}).first().waitFor({timeout:60000});
   await page.getByRole('button').filter({hasText:record.request.title}).first().click();
   await page.getByRole('link',{name:'Export brief'}).waitFor();
   await page.getByRole('button',{name:'Assess access & save brief',exact:true}).waitFor();
  }
  await page.setViewportSize({width:390,height:844});
  await page.locator('.result-panel').evaluate(element=>element.scrollIntoView({block:'start'}));
  await page.screenshot({path:path.join(directory,'alabama-mobile.png')});
  const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth);
  if(overflow)throw Error('Mobile page has horizontal overflow');
  fs.writeFileSync(path.join(directory,'browser-results.json'),JSON.stringify({results,page_errors:errors,mobile_overflow:overflow},null,2));
  console.log(JSON.stringify({results,page_errors:errors,mobile_overflow:overflow}));
  if(errors.length)process.exitCode=1;
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1});
