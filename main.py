import os
import base64
import json
import uuid
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
import requests
from sqlalchemy import create_engine, Column, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from cryptography.fernet import Fernet

app = FastAPI()

CLIENT_ID = os.getenv("ONSHAPE_CLIENT_ID")
CLIENT_SECRET = os.getenv("ONSHAPE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
DATABASE_URL = os.getenv("DATABASE_URL")
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

AUTH_URL = "https://oauth.onshape.com/oauth/authorize"
TOKEN_URL = "https://oauth.onshape.com/oauth/token"
SCOPE = "OAuth2Read OAuth2Write"

Base = declarative_base()
engine = create_engine(DATABASE_URL) if DATABASE_URL else None
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine) if engine else None

cipher = Fernet(ENCRYPTION_KEY.encode()) if ENCRYPTION_KEY else None

def encrypt_token(token):
    if not cipher or not token:
        return token
    return cipher.encrypt(token.encode()).decode()

def decrypt_token(encrypted_token):
    if not cipher or not encrypted_token:
        return encrypted_token
    return cipher.decrypt(encrypted_token.encode()).decode()

class User(Base):
    __tablename__ = "users"
    user_id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    onshape_user_id = Column(String)
    access_token = Column(Text)
    refresh_token = Column(Text)
    token_expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, default=datetime.utcnow)

class UserDocument(Base):
    __tablename__ = "user_documents"
    id = Column(String, primary_key=True)
    user_id = Column(String, index=True)
    document_id = Column(String)
    workspace_id = Column(String)
    element_id = Column(String)
    document_name = Column(String)
    last_used_at = Column(DateTime, default=datetime.utcnow)

if engine:
    Base.metadata.create_all(bind=engine)

def get_db():
    if not SessionLocal:
        raise HTTPException(500, "Database not configured")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_html():
    return """<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>OnShape Manager</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:Arial;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);min-height:100vh;padding:20px}
.container{max-width:1200px;margin:30px auto;background:#fff;padding:30px;border-radius:12px;box-shadow:0 10px 40px rgba(0,0,0,0.2)}
h1{color:#333;margin-bottom:20px;text-align:center}
h2{color:#555;margin:25px 0 15px;padding-bottom:10px;border-bottom:2px solid #667eea}
.section{margin:20px 0;padding:20px;background:#f8f9fa;border-radius:8px}
.button-group{display:flex;gap:10px;margin:15px 0;flex-wrap:wrap}
button{padding:12px 24px;background:#667eea;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:16px;transition:all 0.3s}
button:hover{background:#5568d3;transform:translateY(-2px)}
.input-group{margin:15px 0}
input{width:100%;padding:10px;border:2px solid #ddd;border-radius:4px;font-size:14px;margin-top:5px}
label{display:block;margin-bottom:5px;color:#555;font-weight:500}
#results{margin-top:20px;padding:20px;background:#f8f9fa;border-radius:8px;min-height:100px;max-height:600px;overflow-y:auto}
.error{color:#dc3545;padding:10px;background:#f8d7da;border-radius:4px}
.success{color:#155724;padding:10px;background:#d4edda;border-radius:4px}
.info{color:#004085;padding:10px;background:#cce5ff;border-radius:4px}
table{width:100%;border-collapse:collapse;margin:15px 0;background:#fff}
th,td{padding:12px;text-align:left;border:1px solid #ddd}
th{background:#667eea;color:#fff}
tr:hover{background:#f5f5f5}
.editable-cell{background:#fff9e6;cursor:text}
.download-btn{background:#28a745}
.grid-2{display:grid;grid-template-columns:1fr 1fr;gap:15px}
.user-info{background:#e7f3ff;padding:10px;border-radius:4px;margin-bottom:15px}
</style></head><body>
<div class="container">
<h1>🔧 OnShape BOM Manager</h1>
<div class="section"><h2>Authentication</h2>
<div id="userInfo" class="user-info" style="display:none">
<strong>Logged in:</strong> <span id="userEmail"></span> | <button onclick="logout()">Logout</button>
</div>
<div class="button-group">
<button id="loginBtn">🔐 Login</button>
<button id="loadSavedBtn">📂 Load Saved</button>
</div></div>
<div class="section"><h2>Document Info</h2>
<div class="grid-2">
<div class="input-group"><label>Document ID:</label><input type="text" id="documentId"></div>
<div class="input-group"><label>Workspace ID:</label><input type="text" id="workspaceId"></div>
</div>
<div class="input-group"><label>Element ID:</label><input type="text" id="elementId"></div>
<div class="button-group">
<button id="getDocsBtn">📁 Docs</button>
<button id="getElemsBtn">📄 Elements</button>
<button id="getBomBtn">📊 BOM</button>
<button id="getBboxBtn">📏 Bbox</button>
<button id="saveDocBtn">💾 Save</button>
</div></div>
<div class="section"><h2>Upload</h2>
<input type="file" id="fileUpload" accept=".csv,.json">
<button id="clearBtn" style="margin-top:10px">🗑️ Clear</button>
</div>
<div class="section"><h2>Results</h2>
<div class="button-group">
<button class="download-btn" id="downloadJsonBtn">⬇️ JSON</button>
<button class="download-btn" id="downloadCsvBtn">⬇️ CSV</button>
</div>
<div id="results">No data</div>
</div></div>
<script>
let currentData=null;
let userId=localStorage.getItem('userId');
if(userId){document.getElementById('userInfo').style.display='block';loadUserInfo();}
document.getElementById('loginBtn').onclick=()=>window.location.href='/login';
document.getElementById('getDocsBtn').onclick=getDocuments;
document.getElementById('getElemsBtn').onclick=getElements;
document.getElementById('getBomBtn').onclick=getBOM;
document.getElementById('getBboxBtn').onclick=getBoundingBoxes;
document.getElementById('saveDocBtn').onclick=saveDocument;
document.getElementById('loadSavedBtn').onclick=loadSavedDocuments;
document.getElementById('clearBtn').onclick=clearData;
document.getElementById('downloadJsonBtn').onclick=downloadAsJSON;
document.getElementById('downloadCsvBtn').onclick=downloadAsCSV;
document.getElementById('fileUpload').onchange=handleFileUpload;
async function loadUserInfo(){
try{const r=await fetch('/api/user/info?user_id='+userId);const d=await r.json();
document.getElementById('userEmail').textContent=d.email||'User';}catch(e){}}
function logout(){localStorage.removeItem('userId');userId=null;
document.getElementById('userInfo').style.display='none';showResult('Logged out','success');}
async function saveDocument(){
if(!userId){showResult('Login first','error');return;}
const did=document.getElementById('documentId').value;
const wid=document.getElementById('workspaceId').value;
const eid=document.getElementById('elementId').value;
if(!did||!wid){showResult('Fill doc and workspace','error');return;}
try{const r=await fetch('/api/user/save-document',{method:'POST',
headers:{'Content-Type':'application/json'},
body:JSON.stringify({user_id:userId,document_id:did,workspace_id:wid,element_id:eid})});
if(r.ok)showResult('✅ Saved!','success');else showResult('Failed','error');}catch(e){showResult('Error','error');}}
async function loadSavedDocuments(){
if(!userId){showResult('Login first','error');return;}
try{const r=await fetch('/api/user/documents?user_id='+userId);
const data=await r.json();if(!data.length){showResult('No saved docs','info');return;}
let h='<h3>Saved Documents</h3><table><tr><th>Name</th><th>ID</th><th>Last Used</th><th>Action</th></tr>';
data.forEach(d=>{h+='<tr><td>'+(d.document_name||'Unnamed')+'</td><td>'+d.document_id+'</td><td>'+new Date(d.last_used_at).toLocaleString()+'</td><td><button onclick="loadDoc(\\''+d.document_id+'\\',\\''+d.workspace_id+'\\',\\''+d.element_id+'\\')">Load</button></td></tr>';});
h+='</table>';document.getElementById('results').innerHTML=h;}catch(e){showResult('Error','error');}}
function loadDoc(did,wid,eid){
document.getElementById('documentId').value=did;
document.getElementById('workspaceId').value=wid||'';
document.getElementById('elementId').value=eid||'';
showResult('✅ Loaded!','success');}
async function getDocuments(){
if(!userId){showResult('Login first','error');return;}
showResult('Loading...','info');
try{const r=await fetch('/api/documents?user_id='+userId);
const data=await r.json();currentData=data;displayDocuments(data);}catch(e){showResult('Error','error');}}
async function getElements(){
if(!userId){showResult('Login first','error');return;}
const did=document.getElementById('documentId').value;
const wid=document.getElementById('workspaceId').value;
if(!did||!wid){showResult('Fill fields','error');return;}
showResult('Loading...','info');
try{const r=await fetch('/api/documents/'+did+'/w/'+wid+'/elements?user_id='+userId);
const data=await r.json();currentData=data;displayElements(data);}catch(e){showResult('Error','error');}}
async function getBOM(){
if(!userId){showResult('Login first','error');return;}
const did=document.getElementById('documentId').value;
const wid=document.getElementById('workspaceId').value;
const eid=document.getElementById('elementId').value;
if(!did||!wid||!eid){showResult('Fill all','error');return;}
showResult('Loading...','info');
try{const r=await fetch('/api/assemblies/'+did+'/w/'+wid+'/e/'+eid+'/bom?user_id='+userId);
const data=await r.json();currentData=data;displayBOM(data);}catch(e){showResult('Error','error');}}
async function getBoundingBoxes(){
if(!userId){showResult('Login first','error');return;}
const did=document.getElementById('documentId').value;
const wid=document.getElementById('workspaceId').value;
const eid=document.getElementById('elementId').value;
if(!did||!wid||!eid){showResult('Fill all','error');return;}
showResult('Loading...','info');
try{const r=await fetch('/api/partstudios/'+did+'/w/'+wid+'/e/'+eid+'/boundingboxes?user_id='+userId);
const data=await r.json();currentData=data;displayBoundingBoxes(data);}catch(e){showResult('Error','error');}}
function handleFileUpload(e){
const file=e.target.files[0];if(!file)return;
const reader=new FileReader();reader.onload=function(ev){
const content=ev.target.result;
if(file.name.endsWith('.json')){try{currentData=JSON.parse(content);
displayUploadedData(currentData);}catch(err){showResult('Parse error','error');}}
else if(file.name.endsWith('.csv')){parseCSV(content);}};reader.readAsText(file);}
function parseCSV(csv){
const lines=csv.split('\\n').filter(l=>l.trim());
if(lines.length<2){showResult('Empty CSV','error');return;}
const headers=lines[0].split(',').map(h=>h.trim().replace(/"/g,''));
const data=[];for(let i=1;i<lines.length;i++){
const values=lines[i].split(',').map(v=>v.trim().replace(/"/g,''));
const row={};headers.forEach((h,idx)=>{row[h]=values[idx]||'';});data.push(row);}
if(headers.includes('Part Number')||headers.includes('partNumber')){currentData={bomTable:{items:data}};}
else{currentData=data;}displayUploadedData(currentData);}
function displayUploadedData(data){
if(data.bomTable&&data.bomTable.items){displayBOM(data);}
else if(Array.isArray(data)&&data[0]){
if(data[0]['Length X (mm)']||data[0].lowX){displayBoundingBoxes(data);}
else if(data[0].partNumber||data[0]['Part Number']){currentData={bomTable:{items:data}};displayBOM(currentData);}
else{displayGenericTable(data);}}}
function displayDocuments(data){
if(!data.items||!data.items.length){showResult('No docs','error');return;}
let h='<h3>Documents</h3><table><tr><th>Name</th><th>ID</th><th>Modified</th><th>Action</th></tr>';
data.items.forEach(d=>{h+='<tr><td>'+(d.name||'Unnamed')+'</td><td>'+d.id+'</td><td>'+new Date(d.modifiedAt).toLocaleString()+'</td><td><button onclick="document.getElementById(\\'documentId\\').value=\\''+d.id+'\\'">Use</button></td></tr>';});
h+='</table>';document.getElementById('results').innerHTML=h;}
function displayElements(data){
if(!data||!data.length){showResult('No elements','error');return;}
let h='<h3>Elements</h3><table><tr><th>Name</th><th>Type</th><th>ID</th><th>Action</th></tr>';
data.forEach(e=>{h+='<tr><td>'+(e.name||'Unnamed')+'</td><td>'+e.elementType+'</td><td>'+e.id+'</td><td><button onclick="document.getElementById(\\'elementId\\').value=\\''+e.id+'\\'">Use</button></td></tr>';});
h+='</table>';document.getElementById('results').innerHTML=h;}
function displayBOM(data){
if(!data.bomTable||!data.bomTable.items){showResult('No BOM','error');return;}
let h='<h3>BOM (Editable)</h3><table><tr><th>Item</th><th>Part#</th><th>Name</th><th>Qty</th><th>Desc</th></tr>';
data.bomTable.items.forEach((item,idx)=>{h+='<tr>';
h+='<td class="editable-cell" contenteditable="true" data-row="'+idx+'" data-field="item">'+(item.item||item.Item||'-')+'</td>';
h+='<td class="editable-cell" contenteditable="true" data-row="'+idx+'" data-field="partNumber">'+(item.partNumber||item['Part Number']||'-')+'</td>';
h+='<td class="editable-cell" contenteditable="true" data-row="'+idx+'" data-field="name">'+(item.name||item.Name||'-')+'</td>';
h+='<td class="editable-cell" contenteditable="true" data-row="'+idx+'" data-field="quantity">'+(item.quantity||item.Quantity||'-')+'</td>';
h+='<td class="editable-cell" contenteditable="true" data-row="'+idx+'" data-field="description">'+(item.description||item.Description||'-')+'</td>';
h+='</tr>';});h+='</table><p>💡 Click to edit</p>';
document.getElementById('results').innerHTML=h;attachEditListeners();}
function displayBoundingBoxes(data){
if(!data||!data.length){showResult('No bbox','error');return;}
let h='<h3>Bounding Boxes (mm)</h3><table><tr><th>Part</th><th>X</th><th>Y</th><th>Z</th><th>Vol</th></tr>';
data.forEach((box,idx)=>{let x,y,z,vol,pid;
if(box['Length X (mm)']){x=box['Length X (mm)'];y=box['Length Y (mm)'];z=box['Length Z (mm)'];
vol=box['Volume (mm³)'];pid=box['Part ID']||'Unknown';}else{
x=((box.highX-box.lowX)*1000).toFixed(2);y=((box.highY-box.lowY)*1000).toFixed(2);
z=((box.highZ-box.lowZ)*1000).toFixed(2);vol=(x*y*z).toFixed(2);pid=box.partId||'Unknown';}
h+='<tr>';
h+='<td class="editable-cell" contenteditable="true" data-row="'+idx+'" data-field="partId">'+pid+'</td>';
h+='<td class="editable-cell" contenteditable="true" data-row="'+idx+'" data-field="lengthX">'+x+'</td>';
h+='<td class="editable-cell" contenteditable="true" data-row="'+idx+'" data-field="lengthY">'+y+'</td>';
h+='<td class="editable-cell" contenteditable="true" data-row="'+idx+'" data-field="lengthZ">'+z+'</td>';
h+='<td>'+vol+'</td></tr>';});h+='</table><p>💡 Click to edit</p>';
document.getElementById('results').innerHTML=h;attachEditListeners();}
function displayGenericTable(data){
const headers=Object.keys(data[0]);let h='<h3>Data</h3><table><tr>';
headers.forEach(hh=>h+='<th>'+hh+'</th>');h+='</tr>';
data.forEach((row,idx)=>{h+='<tr>';
headers.forEach(hh=>h+='<td class="editable-cell" contenteditable="true" data-row="'+idx+'" data-field="'+hh+'">'+(row[hh]||'')+'</td>');
h+='</tr>';});h+='</table>';document.getElementById('results').innerHTML=h;attachEditListeners();}
function attachEditListeners(){
document.querySelectorAll('.editable-cell').forEach(cell=>{
cell.addEventListener('blur',function(){
const row=parseInt(this.dataset.row);const field=this.dataset.field;
const val=this.textContent.trim();
if(currentData.bomTable&&currentData.bomTable.items){currentData.bomTable.items[row][field]=val;}
else if(Array.isArray(currentData)){currentData[row][field]=val;}});});}
function clearData(){if(confirm('Clear?')){currentData=null;
document.getElementById('results').innerHTML='No data';
document.getElementById('fileUpload').value='';}}
function downloadAsJSON(){if(!currentData){alert('No data');return;}
const blob=new Blob([JSON.stringify(currentData,null,2)],{type:'application/json'});
const url=URL.createObjectURL(blob);const a=document.createElement('a');
a.href=url;a.download='onshape-'+Date.now()+'.json';a.click();URL.revokeObjectURL(url);}
function downloadAsCSV(){if(!currentData){alert('No data');return;}
let csv='';if(currentData.bomTable&&currentData.bomTable.items){
csv='Item,Part Number,Name,Quantity,Description\\n';
currentData.bomTable.items.forEach(item=>{
csv+='"'+(item.item||'')+'","'+(item.partNumber||'')+'","'+(item.name||'')+'","'+(item.quantity||'')+'","'+(item.description||'')+'"\\n';});}
else if(Array.isArray(currentData)&&currentData.length>0){
const headers=Object.keys(currentData[0]);csv=headers.join(',')+' \\n';
currentData.forEach(row=>{csv+=headers.map(h=>'"'+(row[h]||'')+'"').join(',')+' \\n';});}
const blob=new Blob([csv],{type:'text/csv'});const url=URL.createObjectURL(blob);
const a=document.createElement('a');a.href=url;a.download='onshape-'+Date.now()+'.csv';
a.click();URL.revokeObjectURL(url);}
function showResult(msg,type){document.getElementById('results').innerHTML='<div class="'+(type||'')+'">'+msg+'</div>';}
</script></body></html>"""

if not CLIENT_ID or not CLIENT_SECRET or not REDIRECT_URI:
    @app.get("/", response_class=HTMLResponse)
    def missing_config():
        return "<h1>Error: Missing environment variables</h1>"
else:
    @app.get("/", response_class=HTMLResponse)
    def root():
        return get_html()

    @app.get("/login")
    def login():
        from urllib.parse import urlencode
        params = {"response_type": "code", "client_id": CLIENT_ID, "redirect_uri": REDIRECT_URI, "scope": SCOPE, "state": "state123"}
        return RedirectResponse(AUTH_URL + "?" + urlencode(params))

    @app.get("/callback", response_class=HTMLResponse)
    async def callback(request: Request, db: Session = Depends(get_db)):
        code = request.query_params.get("code")
        error = request.query_params.get("error")
        if error:
            return f"<h1>Error: {error}</h1><a href='/'>Back</a>"
        if not code:
            return "<h1>Missing code</h1><a href='/'>Back</a>"
        
        auth_header = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
        headers = {"Authorization": f"Basic {auth_header}", "Content-Type": "application/x-www-form-urlencoded"}
        data = {"grant_type": "authorization_code", "code": code, "redirect_uri": REDIRECT_URI}
        
        try:
            resp = requests.post(TOKEN_URL, headers=headers, data=data, timeout=10)
            if resp.status_code != 200:
                return f"<h1>Token error</h1><pre>{resp.text}</pre>"
            
            token_data = resp.json()
            access_token = token_data.get("access_token")
            refresh_token = token_data.get("refresh_token")
            expires_in = token_data.get("expires_in", 3600)
            
            user_resp = requests.get("https://cad.onshape.com/api/users/session", headers={"Authorization": f"Bearer {access_token}"})
            user_info = user_resp.json()
            onshape_user_id = user_info.get("id")
            email = user_info.get("email", f"user_{onshape_user_id}")
            
            user = db.query(User).filter(User.onshape_user_id == onshape_user_id).first()
            if user:
                user.access_token = encrypt_token(access_token)
                user.refresh_token = encrypt_token(refresh_token) if refresh_token else None
                user.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                user.last_login = datetime.utcnow()
                user.email = email
            else:
                user = User(
                    user_id=str(uuid.uuid4()),
                    email=email,
                    onshape_user_id=onshape_user_id,
                    access_token=encrypt_token(access_token),
                    refresh_token=encrypt_token(refresh_token) if refresh_token else None,
                    token_expires_at=datetime.utcnow() + timedelta(seconds=expires_in)
                )
                db.add(user)
            db.commit()
            
            return f"""<html><body style='font-family:Arial;padding:50px'><h1 style='color:green'>✅ Success!</h1>
            <p>Logged in as <strong>{email}</strong></p><script>localStorage.setItem('userId','{user.user_id}');
            setTimeout(()=>{{window.location.href='/'}},2000);</script></body></html>"""
        except Exception as e:
            return f"<h1>Error: {str(e)}</h1>"

    def get_user_token(user_id: str, db: Session):
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            raise HTTPException(401, "User not found")
        if user.token_expires_at < datetime.utcnow():
            raise HTTPException(401, "Token expired, please login again")
        return decrypt_token(user.access_token)

    @app.get("/api/user/info")
    async def get_user_info(user_id: str, db: Session = Depends(get_db)):
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            raise HTTPException(404, "User not found")
        return {"email": user.email, "user_id": user.user_id}

    @app.post("/api/user/save-document")
    async def save_document(request: Request, db: Session = Depends(get_db)):
        data = await request.json()
        user_id = data.get("user_id")
        document_id = data.get("document_id")
        workspace_id = data.get("workspace_id")
        element_id = data.get("element_id")
        
        if not user_id or not document_id:
            raise HTTPException(400, "Missing fields")
        
        doc = db.query(UserDocument).filter(UserDocument.user_id == user_id, UserDocument.document_id == document_id).first()
        if doc:
            doc.workspace_id = workspace_id
            doc.element_id = element_id
            doc.last_used_at = datetime.utcnow()
        else:
            doc = UserDocument(
                id=str(uuid.uuid4()),
                user_id=user_id,
                document_id=document_id,
                workspace_id=workspace_id,
                element_id=element_id,
                document_name="Doc " + document_id[:8]
            )
            db.add(doc)
        db.commit()
        return {"status": "success"}

    @app.get("/api/user/documents")
    async def get_user_documents(user_id: str, db: Session = Depends(get_db)):
        docs = db.query(UserDocument).filter(UserDocument.user_id == user_id).order_by(UserDocument.last_used_at.desc()).all()
        return [{"id": d.id, "document_id": d.document_id, "workspace_id": d.workspace_id, "element_id": d.element_id, "document_name": d.document_name, "last_used_at": d.last_used_at.isoformat()} for d in docs]

    @app.get("/api/documents")
    async def get_documents(user_id: str, db: Session = Depends(get_db)):
        token = get_user_token(user_id, db)
        resp = requests.get("https://cad.onshape.com/api/documents", headers={"Authorization": f"Bearer {token}"})
        return JSONResponse(resp.json(), resp.status_code)

    @app.get("/api/documents/{did}/w/{wid}/elements")
    async def get_elements(did: str, wid: str, user_id: str, db: Session = Depends(get_db)):
        token = get_user_token(user_id, db)
        url = f"https://cad.onshape.com/api/documents/d/{did}/w/{wid}/elements"
        resp = requests.get(url, headers={"Authorization": f"Bearer {token}"})
        return JSONResponse(resp.json(), resp.status_code)

    @app.get("/api/assemblies/{did}/w/{wid}/e/{eid}/bom")
    async def get_bom(did: str, wid: str, eid: str, user_id: str, db: Session = Depends(get_db)):
        token = get_user_token(user_id, db)
        url = f"https://cad.onshape.com/api/assemblies/d/{did}/w/{wid}/e/{eid}/bom"
        resp = requests.get(url, headers={"Authorization": f"Bearer {token}"})
        return JSONResponse(resp.json(), resp.status_code)

    @app.get("/api/partstudios/{did}/w/{wid}/e/{eid}/boundingboxes")
    async def get_bounding_boxes(did: str, wid: str, eid: str, user_id: str, db: Session = Depends(get_db)):
        token = get_user_token(user_id, db)
        url = f"https://cad.onshape.com/api/partstudios/d/{did}/w/{wid}/e/{eid}/boundingboxes"
        resp = requests.get(url, headers={"Authorization": f"Bearer {token}"})
        return JSONResponse(resp.json(), resp.status_code)
