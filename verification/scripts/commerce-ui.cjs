const {chromium}=require('./playwright-runtime.cjs');
const {spawn}=require('node:child_process');const fs=require('node:fs');const path=require('node:path');
const root=path.resolve(__dirname,'..','..'),out=path.join(root,'output/playwright/commerce-20261012');fs.mkdirSync(out,{recursive:true});
process.env.TEMP=path.join(root,'.cache/tmp');process.env.TMP=process.env.TEMP;
const env={...process.env,MORPH_REVIEW:'1',NEXT_TELEMETRY_DISABLED:'1',BACKEND_URL:'http://127.0.0.1:8007',MPLCONFIGDIR:path.join(root,'.cache/matplotlib'),PYTHONUNBUFFERED:'1'};
const children=[];function start(exe,args,cwd,name){const log=fs.openSync(path.join(out,name+'.log'),'w');const p=spawn(exe,args,{cwd,env,windowsHide:true,stdio:['ignore',log,log]});children.push(p);p.on('error',e=>console.error(name,e));}
async function ready(url){for(let i=0;i<90;i++){try{if((await fetch(url,{signal:AbortSignal.timeout(1500)})).ok)return;}catch{}await new Promise(r=>setTimeout(r,700));}throw Error('Not ready '+url);}
(async()=>{let browser;const errors=[],consoleErrors=[];try{
start(path.join(root,'backend/.venv/Scripts/python.exe'),['-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8007'],path.join(root,'backend'),'backend');
start(process.execPath,[path.join(root,'frontend/node_modules/next/dist/bin/next'),'start','--hostname','127.0.0.1','--port','3107'],path.join(root,'frontend'),'frontend');
await Promise.all([ready('http://127.0.0.1:8007/api/health'),ready('http://127.0.0.1:3107')]);console.log('SERVERS READY');
browser=await chromium.launchPersistentContext(path.join(root,'.cache/commerce-browser'),{executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,env,viewport:{width:1440,height:1024}});
const fixtures=Object.fromEntries(['front','side'].map(key=>[key,'data:image/png;base64,'+fs.readFileSync(path.join(__dirname,'qa/rendered-'+key+'.png')).toString('base64')]));
await browser.addInitScript(({fixtures})=>{
  window.__cameraFixture='blank';window.__testTracks=[];window.__cameraRequests=[];
  Object.defineProperty(navigator.mediaDevices,'enumerateDevices',{value:async()=>[
    {kind:'videoinput',deviceId:'qa-wide',label:'QA camera wide'},
    {kind:'videoinput',deviceId:'qa-second',label:'QA camera second'}]});
  Object.defineProperty(navigator.mediaDevices,'getUserMedia',{value:async(request)=>{
    window.__cameraRequests.push(request);
    if(window.__cameraDenied)throw new DOMException('Test denied','NotAllowedError');
    const canvas=document.createElement('canvas'),ctx=canvas.getContext('2d'),img=new Image();
    const fixture=window.__cameraFixture;
    if(fixture!=='blank'){img.src=fixtures[fixture];await img.decode();canvas.width=img.width;canvas.height=img.height;}else{canvas.width=1920;canvas.height=1080;}
    const draw=()=>{ctx.fillStyle='#aaaaaa';ctx.fillRect(0,0,canvas.width,canvas.height);if(fixture!=='blank')ctx.drawImage(img,0,0);};draw();
    const timer=setInterval(draw,100),stream=canvas.captureStream(10);window.__testTracks.push(...stream.getTracks());
    stream.getTracks().forEach(track=>{const stop=track.stop.bind(track);track.stop=()=>{clearInterval(timer);stop();};let zoom=2;track.getCapabilities=()=>window.__noZoom?{}:{zoom:{min:1,max:3,step:.1}};track.getSettings=()=>({zoom});track.applyConstraints=async c=>{zoom=c.advanced[0].zoom;};});return stream;
  }});
},{fixtures});
const page=await browser.newPage();page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')consoleErrors.push(m.text());});
await page.goto('http://127.0.0.1:3107',{waitUntil:'networkidle',timeout:90000});

await page.evaluate(()=>localStorage.removeItem('morph-demo-cart-v1'));
await page.reload({waitUntil:'networkidle'});
await page.locator('.product-photo img').waitFor();
await page.screenshot({path:path.join(out,'shop-desktop.png'),fullPage:true});
await page.getByRole('button',{name:'Thêm vào giỏ',exact:true}).click();
await page.getByText('Chọn một size trước khi thêm vào giỏ.',{exact:true}).waitFor();
await page.getByRole('button',{name:'Bảng size',exact:true}).click();
await page.getByRole('dialog',{name:'Bảng size Essential',exact:true}).waitFor();
await page.getByRole('button',{name:'Đóng Bảng size Essential',exact:true}).click();
await page.getByRole('group',{name:'Chọn kích thước'}).getByRole('button',{name:'M',exact:true}).click();
await page.getByRole('button',{name:'Thêm vào giỏ',exact:true}).click();
await page.getByRole('button',{name:'Tăng số lượng size M'}).click();
await page.getByRole('button',{name:'Đóng Giỏ hàng demo'}).click();
await page.reload({waitUntil:'networkidle'});
await page.getByRole('button',{name:'Mở giỏ hàng, 2 sản phẩm'}).click();
await page.getByRole('button',{name:'Xóa size M khỏi giỏ'}).click();
await page.getByText('Giỏ hàng đang trống.',{exact:true}).waitFor();
await page.getByRole('button',{name:'Đóng Giỏ hàng demo'}).click();
await page.getByRole('button',{name:/Bạn chưa chắc về size/}).click();
await page.getByRole('dialog',{name:'Tìm size của tôi',exact:true}).waitFor();
await page.locator('.fit-stage canvas').waitFor();await page.waitForTimeout(1500);
await page.screenshot({path:path.join(out,'fit-desktop.png'),fullPage:false});
await page.setViewportSize({width:390,height:844});
await page.screenshot({path:path.join(out,'fit-mobile.png'),fullPage:false});
await page.locator('.fit-visual').scrollIntoViewIfNeeded();await page.screenshot({path:path.join(out,'fit-model-mobile.png'),fullPage:false});
await page.locator('.fit-modal').evaluate(el=>el.scrollTop=0);
if(await page.evaluate(()=>document.querySelector('.fit-modal').scrollWidth>document.querySelector('.fit-modal').clientWidth))throw Error('Fit overflow mobile');
await page.getByRole('button',{name:'Đóng Tìm size của tôi',exact:true}).click();
await page.screenshot({path:path.join(out,'shop-mobile.png'),fullPage:true});
await page.setViewportSize({width:1440,height:1024});
await page.getByRole('button',{name:/Bạn chưa chắc về size/}).click();
await page.getByRole('button',{name:'Chụp ảnh',exact:true}).first().click();
await page.getByRole('checkbox',{name:'Bật AI hướng dẫn và tự chụp'}).check();await page.waitForTimeout(5000);
if(!await page.locator('.camera-dialog').isVisible())throw Error('Blank auto captured');
await page.getByRole('button',{name:'Đóng camera',exact:true}).click();
for(const [index,view] of ['front','side'].entries()){
 await page.evaluate(v=>window.__cameraFixture=v,view);
 await page.getByRole('button',{name:'Chụp ảnh',exact:true}).nth(index).click();
 await page.getByRole('checkbox',{name:'Bật AI hướng dẫn và tự chụp'}).check();
 await page.locator('.camera-dialog').waitFor({state:'detached',timeout:50000});
}
await page.getByRole('checkbox',{name:/Tôi đồng ý xử lý ảnh/}).check();
await page.getByRole('button',{name:'Tìm size phù hợp',exact:true}).click();
await page.getByText('Đã phân tích hai góc chụp',{exact:true}).waitFor({timeout:60000});
await page.getByRole('button',{name:'Chọn size XS',exact:true}).waitFor({timeout:10000});
await page.waitForTimeout(1500);
await page.screenshot({path:path.join(out,'fit-result-desktop.png'),fullPage:false});
await page.getByRole('button',{name:'Tùy chọn xem 3D'}).click();
await page.getByRole('checkbox',{name:'Tự xoay mô hình',exact:true}).check();
await page.getByRole('button',{name:'Xem nghiêng',exact:true}).click();
if(await page.getByRole('checkbox',{name:'Tự xoay mô hình',exact:true}).isChecked())throw Error('Rotation state mismatch');
await page.getByRole('button',{name:'Tùy chọn xem 3D'}).click();
await page.locator('.fit-visual').screenshot({path:path.join(out,'mannequin-side.png')});
await page.getByRole('button',{name:'Xem trước',exact:true}).click();
await page.setViewportSize({width:390,height:844});
await page.screenshot({path:path.join(out,'fit-result-mobile.png'),fullPage:false});
await page.getByRole('button',{name:'Chọn size XS',exact:true}).click();
await page.getByRole('group',{name:'Chọn kích thước'}).getByRole('button',{name:'XS',exact:true}).waitFor();
if(await page.getByRole('group',{name:'Chọn kích thước'}).getByRole('button',{name:'XS',exact:true}).getAttribute('aria-pressed')!=='true')throw Error('Size callback did not update product');
await page.getByRole('button',{name:'Thêm vào giỏ',exact:true}).click();
await page.getByRole('dialog',{name:'Giỏ hàng demo',exact:true}).evaluate(async el=>{await Promise.all(el.getAnimations({subtree:true}).map(a=>a.finished));});
await page.screenshot({path:path.join(out,'cart-mobile.png'),fullPage:false});
await page.getByRole('button',{name:'Đóng Giỏ hàng demo'}).click();
await page.getByRole('button',{name:/Gợi ý của bạn: XS/}).click();
await page.getByRole('button',{name:'Xóa phiên & chụp lại',exact:true}).click();
await page.getByRole('heading',{name:'Bắt đầu với hai góc chụp.',exact:true}).waitFor();
await page.getByRole('button',{name:'Đóng Tìm size của tôi',exact:true}).click();
if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('Shop horizontal overflow');
if(!await page.evaluate(()=>window.__testTracks.every(t=>t.readyState==='ended')))throw Error('Track leak');
await page.goto('http://127.0.0.1:3107/scan',{waitUntil:'networkidle'});
await page.getByText('Backend sẵn sàng',{exact:true}).waitFor();
fs.writeFileSync(path.join(out,'results.json'),JSON.stringify({errors,consoleErrors,production:true,fixture:'synthetic mannequin camera; actual MediaPipe backend, not accuracy validation',cartPersistence:true,cartQuantity:true,sizeChart:true,emptyCameraRejected:true,autoCaptureTwoViews:true,realScan:true,productSizeCallback:true,rotationSync:true,delete:true,legacyScanRoute:true,mobileOverflow:false},null,2));
if(errors.length||consoleErrors.length)throw Error([...errors,...consoleErrors].join('\n'));
console.log('COMMERCE FLOW PASSED');
}finally{if(browser)await browser.close();for(const p of children)p.kill();}})().catch(e=>{console.error(e);process.exitCode=1;});
