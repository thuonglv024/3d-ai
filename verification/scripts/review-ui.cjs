const {chromium}=require('./playwright-runtime.cjs');
const {spawn}=require('node:child_process');const fs=require('node:fs');const path=require('node:path');
const root=path.resolve(__dirname,'..','..'),out=path.join(root,'verification/review-20261012');fs.mkdirSync(out,{recursive:true});
process.env.TEMP=path.join(root,'.cache/tmp');process.env.TMP=process.env.TEMP;
const env={...process.env,MORPH_REVIEW:'1',NEXT_TELEMETRY_DISABLED:'1',BACKEND_URL:'http://127.0.0.1:8007',MPLCONFIGDIR:path.join(root,'.cache/matplotlib'),PYTHONUNBUFFERED:'1'};
const children=[];function start(exe,args,cwd,name){const log=fs.openSync(path.join(out,name+'.log'),'w');const p=spawn(exe,args,{cwd,env,windowsHide:true,stdio:['ignore',log,log]});children.push(p);p.on('error',e=>console.error(name,e));}
async function ready(url){for(let i=0;i<90;i++){try{if((await fetch(url,{signal:AbortSignal.timeout(1500)})).ok)return;}catch{}await new Promise(r=>setTimeout(r,700));}throw Error('Not ready '+url);}
(async()=>{let browser;const errors=[],consoleErrors=[];try{
start(path.join(root,'backend/.venv/Scripts/python.exe'),['-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8007'],path.join(root,'backend'),'backend');
start(process.execPath,[path.join(root,'frontend/node_modules/next/dist/bin/next'),'start','--hostname','127.0.0.1','--port','3107'],path.join(root,'frontend'),'frontend');
await Promise.all([ready('http://127.0.0.1:8007/api/health'),ready('http://127.0.0.1:3107')]);console.log('SERVERS READY');
browser=await chromium.launchPersistentContext(path.join(root,'.cache/review-browser'),{executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,env,viewport:{width:1440,height:1024}});
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
await page.getByText('Backend sẵn sàng',{exact:true}).waitFor({timeout:45000});
await page.locator('canvas').waitFor();await page.waitForTimeout(1800);
await page.screenshot({path:path.join(out,'desktop.png'),fullPage:true});
await page.evaluate(()=>{window.__cameraDenied=true;});
await page.getByRole('button',{name:'Chụp ảnh',exact:true}).first().click();
await page.getByText('Chưa được phép dùng camera.',{exact:false}).waitFor();
await page.evaluate(()=>{window.__cameraDenied=false;});
await page.getByRole('button',{name:'Thử lại camera'}).click();
await page.getByRole('button',{name:'Mở rộng tối đa camera này'}).click();
await page.waitForFunction(()=>document.querySelector('#camera-zoom')?.value==='1');
await page.getByRole('combobox',{name:'Chọn camera'}).selectOption('qa-second');
await page.getByText('1920 × 1080',{exact:false}).waitFor();
await page.waitForFunction(()=>window.__testTracks.slice(0,-1).every(t=>t.readyState==='ended'));
await page.getByRole('button',{name:'Mở rộng tối đa camera này'}).waitFor();
await page.setViewportSize({width:390,height:844});await page.screenshot({path:path.join(out,'camera-mobile.png'),fullPage:true});
if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth||document.querySelector('dialog').scrollWidth>document.querySelector('dialog').clientWidth))throw Error('Camera mobile overflow');
await page.setViewportSize({width:1440,height:1024});
await page.getByRole('checkbox',{name:'Bật AI hướng dẫn và tự chụp'}).check();await page.waitForTimeout(7500);
if(!await page.locator('dialog').isVisible())throw Error('Blank camera incorrectly auto-captured');
await page.screenshot({path:path.join(out,'camera-empty.png'),fullPage:true});
await page.getByRole('button',{name:'Đóng camera'}).click();
if(!await page.evaluate(()=>window.__testTracks.every(t=>t.readyState==='ended')))throw Error('Camera tracks leaked');
console.log('EMPTY CAMERA REJECTED');
await page.evaluate(()=>{window.__noZoom=true;});
for(const [index,view] of ['front','side'].entries()){
  await page.evaluate(v=>{window.__cameraFixture=v;},view);
  await page.getByRole('button',{name:'Chụp ảnh',exact:true}).nth(index).click();
  await page.getByRole('checkbox',{name:'Bật AI hướng dẫn và tự chụp'}).check();
  if(index===0){await page.waitForTimeout(1800);await page.screenshot({path:path.join(out,'camera-front.png'),fullPage:true});}
  await page.locator('dialog').waitFor({state:'detached',timeout:50000});console.log('AUTO CAPTURE',view);
}
await page.getByRole('checkbox',{name:/Tôi đồng ý xử lý ảnh/}).check();
await page.getByRole('button',{name:'Tạo mô hình 3D',exact:true}).click();
await page.getByText('Kết quả từ ảnh của bạn',{exact:true}).waitFor({timeout:60000});
await page.getByRole('heading',{name:'Số đo ước lượng từ hai ảnh'}).waitFor();
await page.waitForTimeout(2000);
await page.screenshot({path:path.join(out,'result-desktop.png'),fullPage:true});
const rotateButton=page.getByRole('button',{name:'Tự xoay mô hình'});
await rotateButton.click();
await page.getByRole('button',{name:'Xem nghiêng',exact:true}).click();
if(await rotateButton.getAttribute('aria-pressed')!=='false')throw Error('Preset must turn auto-rotation off in parent UI');
await rotateButton.click();
if(await rotateButton.getAttribute('aria-pressed')!=='true')throw Error('One click must resume rotation');
await rotateButton.click();
for(const view of ['nghiêng','sau','3/4','trước']){
  await page.getByRole('button',{name:`Xem ${view}`,exact:true}).click();await page.waitForTimeout(250);
  if(view==='nghiêng')await page.locator('.viewport').screenshot({path:path.join(out,'avatar-side.png')});
}
await page.getByRole('button',{name:'Khung lưới',exact:true}).click();
await page.getByRole('button',{name:'Khối đặc',exact:true}).click();
await page.getByRole('button',{name:'Bật tắt vòng đo 3D'}).click();
if(await page.locator('.body-legend').count())throw Error('Rings legend not hidden');
await page.getByRole('button',{name:'Bật tắt vòng đo 3D'}).click();
const report=await(await page.request.get(new URL(await page.getByRole('link',{name:'Xuất số đo'}).getAttribute('href'),'http://127.0.0.1:3107').href)).json();
if(report.measurements.inseam_cm!==null)throw Error('Inseam invented');
if(!report.body_fit.sections.every(s=>s.points_m.length>3))throw Error('Missing real section contours');
await page.getByRole('button',{name:'Đối chiếu số đo với bảng',exact:true}).click();
await page.locator('.size-result').waitFor();
await page.getByRole('checkbox',{name:'Tôi nhập bảng của nhãn hàng'}).check();
await page.getByLabel('Tên nhãn hàng / sản phẩm').fill('QA test chart');
for(const [label,key] of [['Ngực','chest_cm'],['Eo','waist_cm']]){
  await page.getByRole('spinbutton',{name:`M ${label} từ`,exact:true}).fill(String(Math.floor(report.measurements[key]-2)));
  await page.getByRole('spinbutton',{name:`M ${label} đến`,exact:true}).fill(String(Math.ceil(report.measurements[key]+2)));
}
await page.getByRole('button',{name:'Đối chiếu số đo với bảng',exact:true}).click();
await page.locator('.size-result strong').filter({hasText:/M/}).waitFor();
await page.setViewportSize({width:390,height:844});await page.screenshot({path:path.join(out,'result-mobile.png'),fullPage:true});
if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('Mobile horizontal overflow');
await page.getByRole('button',{name:'Xóa phiên & bắt đầu lại'}).click();
await page.getByText('Mô hình minh họa',{exact:true}).waitFor();
const requests=await page.evaluate(()=>window.__cameraRequests);
if(requests.some(r=>r.video.aspectRatio||r.video.resizeMode?.ideal!=='none'))throw Error('Unexpected crop constraint');
fs.writeFileSync(path.join(out,'browser-results.json'),JSON.stringify({fixture:'synthetic mannequin camera feed; not a real-person accuracy test',mode:'Next production build',errors,consoleErrors,permissionRetry:true,cameraSwitchStopsOldTracks:true,zoomCapabilities:true,noZoomFallback:true,nativeAspect:true,viewerPresets:true,rotationPresetStateSynced:true,emptyCameraRejected:true,cameraTracksStopped:true,frontAndSideAutoCapture:true,scan:true,measurementExport:true,customSizeChart:true,delete:true,mobileOverflow:false,measurements:report.measurements,fitStatus:report.body_fit.fit_status,maxFitErrorCm:report.body_fit.max_fit_error_cm},null,2));
if(errors.length)throw Error(errors.join('\n'));console.log('UI FLOW PASSED');
}finally{if(browser)await browser.close();for(const p of children)p.kill();}})().catch(e=>{console.error(e);process.exitCode=1;});
