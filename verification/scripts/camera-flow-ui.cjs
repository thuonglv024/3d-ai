const {chromium}=require('./playwright-runtime.cjs');
const {spawn}=require('node:child_process');const fs=require('node:fs');const path=require('node:path');
const root=path.resolve(__dirname,'..','..'),out=path.join(root,'output/playwright/camera-flow-20261012');fs.mkdirSync(out,{recursive:true});
process.env.TEMP=path.join(root,'.cache/tmp');process.env.TMP=process.env.TEMP;
const env={...process.env,MORPH_REVIEW:'1',NEXT_TELEMETRY_DISABLED:'1',BACKEND_URL:'http://127.0.0.1:8007',MPLCONFIGDIR:path.join(root,'.cache/matplotlib'),PYTHONUNBUFFERED:'1'};
const children=[];function start(exe,args,cwd,name){const log=fs.openSync(path.join(out,name+'.log'),'w');const p=spawn(exe,args,{cwd,env,windowsHide:true,stdio:['ignore',log,log]});children.push(p);p.on('error',e=>console.error(name,e));}
async function ready(url){for(let i=0;i<90;i++){try{if((await fetch(url,{signal:AbortSignal.timeout(1500)})).ok)return;}catch{}await new Promise(r=>setTimeout(r,700));}throw Error('Not ready '+url);}
(async()=>{let browser;const errors=[],consoleErrors=[];try{
start(path.join(root,'backend/.venv/Scripts/python.exe'),['-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8007'],path.join(root,'backend'),'backend');
start(process.execPath,[path.join(root,'frontend/node_modules/next/dist/bin/next'),'start','--hostname','127.0.0.1','--port','3107'],path.join(root,'frontend'),'frontend');
await Promise.all([ready('http://127.0.0.1:8007/api/health'),ready('http://127.0.0.1:3107')]);console.log('SERVERS READY');
browser=await chromium.launchPersistentContext(path.join(root,'.cache/camera-flow-browser'),{executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,env,viewport:{width:1440,height:1024}});
const fixtures=Object.fromEntries(['front','side'].map(key=>[key,'data:image/png;base64,'+fs.readFileSync(path.join(__dirname,'qa/upper-'+key+'.png')).toString('base64')]));
await browser.addInitScript(({fixtures})=>{
 window.__cameraFixture='blank';window.__testTracks=[];window.__cameraRequests=[];
 Object.defineProperty(navigator.mediaDevices,'enumerateDevices',{value:async()=>[{kind:'videoinput',deviceId:'qa',label:'QA laptop camera'}]});
 Object.defineProperty(navigator.mediaDevices,'getUserMedia',{value:async request=>{
  window.__cameraRequests.push(request);const images={};for(const k of ['front','side']){const img=new Image();img.src=fixtures[k];await img.decode();images[k]=img;}
  const canvas=document.createElement('canvas');canvas.width=images.front.width;canvas.height=images.front.height;const ctx=canvas.getContext('2d');
  const draw=()=>{ctx.fillStyle='#aaaaaa';ctx.fillRect(0,0,canvas.width,canvas.height);if(images[window.__cameraFixture])ctx.drawImage(images[window.__cameraFixture],0,0,canvas.width,canvas.height);};draw();const timer=setInterval(draw,100),stream=canvas.captureStream(10);
  window.__testTracks.push(...stream.getTracks());for(const t of stream.getTracks()){const stop=t.stop.bind(t);t.stop=()=>{clearInterval(timer);stop();};}return stream;
 }});
},{fixtures});
const page=await browser.newPage();page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')consoleErrors.push(m.text());});
await page.goto('http://127.0.0.1:3107/scan',{waitUntil:'networkidle'});
if(await page.locator('input[type=file]').count())throw Error('Upload still exposed');
if(await page.locator('canvas').count())throw Error('Sample mannequin still exposed');
await page.screenshot({path:path.join(out,'onboarding-desktop.png'),fullPage:true});
await page.setViewportSize({width:390,height:844});await page.screenshot({path:path.join(out,'onboarding-mobile.png'),fullPage:true});
await page.setViewportSize({width:1440,height:1024});
await page.getByRole('checkbox',{name:/Tôi đồng ý gửi khung hình/}).check();
await page.getByRole('button',{name:'Mở camera & bắt đầu',exact:true}).click();
await page.getByRole('button',{name:'Bắt đầu quét',exact:true}).click();
await page.waitForTimeout(3500);
if(await page.locator('.capture-count').count())throw Error('Blank frame started countdown');
await page.evaluate(()=>window.__cameraFixture='front');
await page.locator('.capture-count').waitFor({timeout:20000});
await page.screenshot({path:path.join(out,'camera-front.png'),fullPage:true});
await page.getByRole('heading',{name:'Xoay người 90°',exact:true}).waitFor({timeout:30000});
await page.screenshot({path:path.join(out,'camera-transition.png'),fullPage:true});
if(await page.evaluate(()=>window.__cameraRequests.length)!==1)throw Error('Camera restarted between views');
await page.evaluate(()=>window.__cameraFixture='side');
await page.locator('.capture-count').waitFor({timeout:20000});
await page.screenshot({path:path.join(out,'camera-side.png'),fullPage:true});
await page.getByRole('heading',{name:'Hình thể 3D của bạn',exact:true}).waitFor({timeout:60000});
await page.locator('.scan-stage canvas').waitFor();await page.waitForTimeout(1800);
if(!await page.evaluate(()=>window.__testTracks.every(t=>t.readyState==='ended')))throw Error('Camera not stopped after pair');
await page.screenshot({path:path.join(out,'result-desktop.png'),fullPage:true});
await page.setViewportSize({width:390,height:844});
await page.screenshot({path:path.join(out,'result-mobile.png'),fullPage:true});
await page.getByRole('button',{name:'Khối đặc',exact:true}).click();await page.waitForTimeout(600);
await page.screenshot({path:path.join(out,'points-mobile.png'),fullPage:true});
const toolsRect=await page.locator('.scan-tools').boundingBox(),modelRect=await page.locator('.scan-stage .body-viewer').boundingBox();
if(toolsRect.y+toolsRect.height>modelRect.y+1)throw Error('Toolbar overlaps canvas');
if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('Mobile overflow');
await page.getByRole('button',{name:'Chụp lại',exact:true}).click();
await page.getByRole('heading',{name:'Tìm size từ hình thể của bạn.',exact:true}).waitFor();
await page.getByRole('checkbox',{name:/Tôi đồng ý gửi khung hình/}).check();
await page.getByRole('button',{name:'Mở camera & bắt đầu',exact:true}).click();
await page.getByRole('button',{name:'Bắt đầu quét',exact:true}).waitFor();
await page.screenshot({path:path.join(out,'camera-mobile.png'),fullPage:true});
await page.getByRole('button',{name:'Hủy phiên',exact:true}).click();
if(!await page.evaluate(()=>window.__testTracks.every(t=>t.readyState==='ended')))throw Error('Cancel leaked camera');
await page.goto('http://127.0.0.1:3107',{waitUntil:'networkidle'});
await page.getByRole('button',{name:/Bạn chưa chắc về size/}).click();
await page.getByRole('heading',{name:'Tìm size từ hình thể của bạn.',exact:true}).waitFor();
if(await page.locator('input[type=file]').count())throw Error('Store dialog still exposes uploads');
await page.getByRole('button',{name:'Đóng Tìm size của tôi',exact:true}).click();
if(errors.length||consoleErrors.length)throw Error([...errors,...consoleErrors].join('\n'));
fs.writeFileSync(path.join(out,'results.json'),JSON.stringify({errors,consoleErrors,cameraOnly:true,noSampleMannequin:true,singleCameraSession:true,frontToSideAutomatic:true,countdownsBothViews:true,blankRejected:true,autoProcessing:true,realUpperBodyReconstruction:true,streamsStopped:true,cancelCleanup:true,storefrontModal:true,mobileToolsOutsideCanvas:true,fixture:'Synthetic upper-body mannequin frames; real MediaPipe backend; not human accuracy validation.'},null,2));
console.log('CAMERA-ONLY SEQUENCE PASSED');
}finally{if(browser)await browser.close();for(const p of children)p.kill();}})().catch(e=>{console.error(e);process.exitCode=1;});

