const {chromium}=require('./playwright-runtime.cjs');
const {spawn}=require('node:child_process');const fs=require('node:fs');const path=require('node:path');
const root=path.resolve(__dirname,'..','..'),out=path.join(root,'output/playwright/upper-20261012');fs.mkdirSync(out,{recursive:true});
process.env.TEMP=path.join(root,'.cache/tmp');process.env.TMP=process.env.TEMP;
const env={...process.env,MORPH_REVIEW:'1',NEXT_TELEMETRY_DISABLED:'1',BACKEND_URL:'http://127.0.0.1:8007',MPLCONFIGDIR:path.join(root,'.cache/matplotlib'),PYTHONUNBUFFERED:'1'};
const children=[];function start(exe,args,cwd,name){const log=fs.openSync(path.join(out,name+'.log'),'w');const p=spawn(exe,args,{cwd,env,windowsHide:true,stdio:['ignore',log,log]});children.push(p);p.on('error',e=>console.error(name,e));}
async function ready(url){for(let i=0;i<90;i++){try{if((await fetch(url,{signal:AbortSignal.timeout(1500)})).ok)return;}catch{}await new Promise(r=>setTimeout(r,700));}throw Error('Not ready '+url);}
(async()=>{let browser;const errors=[],consoleErrors=[];try{
start(path.join(root,'backend/.venv/Scripts/python.exe'),['-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8007'],path.join(root,'backend'),'backend');
start(process.execPath,[path.join(root,'frontend/node_modules/next/dist/bin/next'),'start','--hostname','127.0.0.1','--port','3107'],path.join(root,'frontend'),'frontend');
await Promise.all([ready('http://127.0.0.1:8007/api/health'),ready('http://127.0.0.1:3107')]);console.log('SERVERS READY');
browser=await chromium.launchPersistentContext(path.join(root,'.cache/upper-browser'),{executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,env,viewport:{width:1440,height:1024}});
const fixtures=Object.fromEntries(['front','side'].map(key=>[key,'data:image/png;base64,'+fs.readFileSync(path.join(__dirname,'qa/upper-'+key+'.png')).toString('base64')]));
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

await page.goto('http://127.0.0.1:3107/scan',{waitUntil:'networkidle'});
await page.getByRole('radio',{name:'Webcam · thân trên',exact:true}).waitFor();
if(!await page.getByRole('radio',{name:'Webcam · thân trên',exact:true}).isChecked())throw Error('Upper mode not default');
await page.screenshot({path:path.join(out,'input-desktop.png'),fullPage:true});
await page.getByRole('button',{name:'Chụp ảnh',exact:true}).first().click();
await page.getByRole('checkbox',{name:'Bật AI hướng dẫn và tự chụp'}).check();
await page.waitForTimeout(3500);
if(!await page.locator('.camera-dialog').isVisible())throw Error('Blank frame accepted');
await page.getByRole('button',{name:'Đóng camera',exact:true}).click();
for(const [index,view] of ['front','side'].entries()){
 await page.evaluate(v=>window.__cameraFixture=v,view);
 await page.getByRole('button',{name:'Chụp ảnh',exact:true}).nth(index).click();
 await page.getByRole('checkbox',{name:'Bật AI hướng dẫn và tự chụp'}).check();
 if(!index){await page.waitForTimeout(1500);await page.screenshot({path:path.join(out,'camera-upper.png'),fullPage:false});}
 await page.locator('.camera-dialog').waitFor({state:'detached',timeout:60000});
}
await page.getByRole('checkbox',{name:/Tôi đồng ý xử lý ảnh/}).check();
await page.getByRole('button',{name:'Tìm size phù hợp',exact:true}).click();
await page.getByRole('heading',{name:'Hình thể 3D của bạn',exact:true}).waitFor({timeout:60000});
await page.locator('.scan-stage canvas').waitFor();await page.waitForTimeout(1800);
await page.screenshot({path:path.join(out,'result-desktop.png'),fullPage:true});
if(await page.locator('.scan-data-grid>div').count()!==12)throw Error('Measurement report missing');
await page.locator('.scan-rows button').filter({hasText:'Ngực'}).click();
await page.getByRole('button',{name:'Khối đặc',exact:true}).click();await page.waitForTimeout(800);
await page.screenshot({path:path.join(out,'points-desktop.png'),fullPage:true});
await page.getByRole('button',{name:'Điểm 3D',exact:true}).click();
await page.getByRole('button',{name:'Khung lưới',exact:true}).click();
await page.getByRole('button',{name:'Tự xoay',exact:true}).click();
await page.getByRole('button',{name:'Xem nghiêng',exact:true}).click();
await page.getByRole('button',{name:'Tự xoay',exact:true}).waitFor();
const downloadPromise=page.waitForEvent('download');await page.getByRole('button',{name:'Xuất ảnh',exact:true}).click();
const download=await downloadPromise;await download.saveAs(path.join(out,'exported-body.png'));
await page.getByRole('button',{name:'Xem trước',exact:true}).click();
await page.setViewportSize({width:390,height:844});await page.screenshot({path:path.join(out,'result-mobile.png'),fullPage:true});
if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('Mobile overflow');
await page.getByText('Chưa có size khớp cả ngực và eo. Xem bảng size hoặc chụp lại.',{exact:true}).waitFor();
await page.getByRole('button',{name:'Chụp lại',exact:true}).click();
await page.getByRole('heading',{name:'Bắt đầu với hai góc chụp.',exact:true}).waitFor();
if(!await page.evaluate(()=>window.__testTracks.every(t=>t.readyState==='ended')))throw Error('Camera tracks leaked');
await page.goto('http://127.0.0.1:3107',{waitUntil:'networkidle'});
await page.getByRole('button',{name:/Bạn chưa chắc về size/}).click();
await page.getByRole('radio',{name:'Ảnh toàn thân',exact:true}).check();
await page.locator('input[type=file]').nth(0).setInputFiles(path.join(__dirname,'qa/rendered-front.png'));
await page.locator('input[type=file]').nth(1).setInputFiles(path.join(__dirname,'qa/rendered-side.png'));
await page.getByRole('checkbox',{name:/Tôi đồng ý xử lý ảnh/}).check();
await page.getByRole('button',{name:'Tìm size phù hợp',exact:true}).click();
await page.getByRole('button',{name:'Chọn size XS →',exact:true}).waitFor({timeout:60000});
await page.getByRole('button',{name:'Chọn size XS →',exact:true}).click();
if(await page.getByRole('group',{name:'Chọn kích thước'}).getByRole('button',{name:'XS',exact:true}).getAttribute('aria-pressed')!=='true')throw Error('Callback did not select product size');
await page.getByRole('button',{name:'Thêm vào giỏ',exact:true}).click();
await page.getByRole('dialog',{name:'Giỏ hàng demo'}).waitFor();
if(errors.length||consoleErrors.length)throw Error([...errors,...consoleErrors].join('\n'));
fs.writeFileSync(path.join(out,'results.json'),JSON.stringify({errors,consoleErrors,upperBodyAutoCapture:true,blankRejected:true,realReconstruction:true,measurementProvenance:true,pointMode:true,imageExport:true,mobileOverflow:false,delete:true,fixture:'Synthetic mannequin images cropped above knees; actual MediaPipe backend. Not human accuracy validation.'},null,2));
console.log('UPPER BODY UI PASSED');
}finally{if(browser)await browser.close();for(const p of children)p.kill();}})().catch(e=>{console.error(e);process.exitCode=1;});
