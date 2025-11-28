import os
import base64
import json
import uuid
import logging
import time
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
import requests
from sqlalchemy import create_engine, Column, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from cryptography.fernet import Fernet
from pydantic import BaseModel, validator
from slowapi import Limiter
from slowapi.util import get_remote_address

# === LOGGING SETUP ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === CACHING SETUP ===
cache_storage = {}

def cache_key(prefix, *args):
    return f"{prefix}:{'_'.join(str(a) for a in args)}"

def get_cached(key, max_age_seconds=300):
    if key in cache_storage:
        cached_data, timestamp = cache_storage[key]
        if datetime.utcnow() - timestamp < timedelta(seconds=max_age_seconds):
            logger.info(f"Cache HIT: {key}")
            return cached_data
        else:
            del cache_storage[key]
    return None

def set_cache(key, value):
    cache_storage[key] = (value, datetime.utcnow())
    logger.info(f"Cache SET: {key}")

# === SAFE API CALL WRAPPER ===
def safe_api_call(url, headers, method="get", timeout=10, json_data=None):
    try:
        if method == "get":
            resp = requests.get(url, headers=headers, timeout=timeout)
        elif method == "post":
            resp = requests.post(url, headers=headers, json=json_data, timeout=timeout)
        elif method == "delete":
            resp = requests.delete(url, headers=headers, timeout=timeout)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        resp.raise_for_status()
        return resp
    except requests.Timeout:
        logger.error(f"API timeout: {url}")
        raise HTTPException(504, "OnShape API timeout - try again")
    except requests.ConnectionError:
        logger.error(f"Connection error: {url}")
        raise HTTPException(503, "Cannot connect to OnShape API")
    except requests.HTTPError as e:
        logger.error(f"HTTP error {e.response.status_code}: {url}")
        raise HTTPException(e.response.status_code, f"OnShape API error: {str(e)[:100]}")
    except Exception as e:
        logger.error(f"API call failed: {str(e)}")
        raise HTTPException(500, f"API call failed: {str(e)[:100]}")

# === VALIDATION MODELS ===
class DocumentRequest(BaseModel):
    document_id: str
    workspace_id: str
    element_id: str
    
    @validator('document_id', 'workspace_id', 'element_id')
    def ids_not_empty(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('IDs cannot be empty')
        if len(v) > 100:
            raise ValueError('IDs too long')
        return v.strip()

# === RATE LIMITING ===
limiter = Limiter(key_func=get_remote_address)

app = FastAPI()
app.state.limiter = limiter

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
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OnShape BOM Manager</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 30px auto;
            background: white;
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }
        h1 {
            color: #333;
            margin-bottom: 20px;
            text-align: center;
            font-size: 28px;
        }
        h2 {
            color: #555;
            margin: 25px 0 15px 0;
            padding-bottom: 10px;
            border-bottom: 2px solid #667eea;
            font-size: 20px;
        }
        .section {
            margin: 20px 0;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
        }
        .button-group {
            display: flex;
            gap: 10px;
            margin: 15px 0;
            flex-wrap: wrap;
        }
        button {
            padding: 12px 24px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 16px;
            transition: all 0.3s;
            font-weight: 500;
        }
        button:hover {
            background: #5568d3;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }
        button:disabled {
            background: #ccc;
            cursor: not-allowed;
            transform: none;
        }
        .input-group { margin: 15px 0; }
        input, select {
            width: 100%;
            padding: 10px;
            border: 2px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
            margin-top: 5px;
        }
        input:focus, select:focus {
            outline: none;
            border-color: #667eea;
        }
        label {
            display: block;
            margin-bottom: 5px;
            color: #555;
            font-weight: 500;
        }
        #results {
            margin-top: 20px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
            min-height: 100px;
            max-height: 600px;
            overflow-y: auto;
        }
        .error {
            color: #dc3545;
            padding: 10px;
            background: #f8d7da;
            border-radius: 4px;
            margin: 10px 0;
        }
        .success {
            color: #155724;
            padding: 10px;
            background: #d4edda;
            border-radius: 4px;
            margin: 10px 0;
        }
        .info {
            color: #004085;
            padding: 10px;
            background: #cce5ff;
            border-radius: 4px;
            margin: 10px 0;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
            background: white;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border: 1px solid #ddd;
        }
        th {
            background: #667eea;
            color: white;
            font-weight: 600;
        }
        tr:hover { background: #f5f5f5; }
        .editable-cell {
            background: #fff9e6;
            cursor: text;
            min-width: 80px;
        }
        .editable-cell:hover { background: #fff3cd; }
        .editable-cell:focus {
            background: #fffacd;
            outline: 2px solid #667eea;
        }
        .download-btn { background: #28a745; }
        .download-btn:hover { background: #218838; }
        .push-btn { background: #ff6b6b; }
        .push-btn:hover { background: #ee5a52; }
        .grid-2 {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
        }
        .user-info {
            background: #e7f3ff;
            padding: 12px;
            border-radius: 4px;
            margin-bottom: 15px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .toggle-group {
            display: flex;
            gap: 10px;
            align-items: center;
            margin: 10px 0;
        }
        .toggle-btn {
            padding: 8px 16px;
            background: #f0f0f0;
            color: #333;
            border: 2px solid #ddd;
            font-size: 14px;
        }
        .toggle-btn.active {
            background: #667eea;
            color: white;
            border-color: #667eea;
        }
        .expandable-row {
            cursor: pointer;
            user-select: none;
        }
        .expandable-row:hover {
            background: #e9ecef !important;
        }
        .expand-icon {
            display: inline-block;
            margin-right: 5px;
            transition: transform 0.2s;
        }
        .expand-icon.expanded {
            transform: rotate(90deg);
        }
        .child-row {
            display: none;
            background: #f8f9fa;
        }
        .child-row.visible {
            display: table-row;
        }
        .indent-1 { padding-left: 30px; }
        .indent-2 { padding-left: 50px; }
        .indent-3 { padding-left: 70px; }
        @media (max-width: 768px) {
            .grid-2 { grid-template-columns: 1fr; }
            .container { padding: 15px; }
            h1 { font-size: 22px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔧 OnShape BOM & Bounding Box Manager</h1>
        
        <div class="section">
            <h2>🔐 Authentication</h2>
            <div id="userInfo" class="user-info" style="display:none">
                <div>
                    <strong>Logged in as:</strong> <span id="userEmail"></span>
                </div>
                <button onclick="logout()" style="padding: 8px 16px; font-size: 14px;">Logout</button>
            </div>
            <div class="button-group">
                <button id="loginBtn">🔐 Login with OnShape</button>
                <button id="loadSavedBtn">📂 Load Saved Documents</button>
            </div>
        </div>
        
        <div class="section">
            <h2>📄 Document Information</h2>
            <div class="grid-2">
                <div class="input-group">
                    <label for="documentId">Document ID:</label>
                    <input type="text" id="documentId" placeholder="e.g., 5f4b3c2a1e0d9c8b7a6f5e4d">
                </div>
                <div class="input-group">
                    <label for="workspaceId">Workspace ID:</label>
                    <input type="text" id="workspaceId" placeholder="e.g., 1a2b3c4d5e6f7g8h9i0j">
                </div>
            </div>
            <div class="input-group">
                <label for="elementId">Element ID (Assembly/Part Studio):</label>
                <input type="text" id="elementId" placeholder="e.g., 9z8y7x6w5v4u3t2s1r0q">
            </div>
            <div class="button-group">
                <button id="getDocsBtn">📁 List My Documents</button>
                <button id="getElemsBtn">📄 Get Elements</button>
                <button id="saveDocBtn">💾 Save This Document</button>
            </div>
        </div>
        
        <div class="section">
            <h2>📊 Data Operations</h2>
            <div class="toggle-group">
                <label><strong>BOM Format:</strong></label>
                <button class="toggle-btn active" id="flatBtn" onclick="setBomFormat('flat')">Flattened</button>
                <button class="toggle-btn" id="structBtn" onclick="setBomFormat('structured')">Structured</button>
            </div>
            <div class="button-group">
                <button id="getBomBtn">📊 Get BOM</button>
                <button id="getBboxBtn">📏 Get Bounding Boxes</button>
                <button id="getVarsBtn">🔢 Get Configuration Variables</button>
                <button id="previewLengthsBtn">👁️ Preview Length Properties</button>
                <button id="createLengthPropsBtn">📐 Create Length Properties</button>
                <button class="push-btn" id="syncVarsBtn" style="display:none">🔄 Sync Variables to Properties</button>
                <button class="push-btn" id="pushBomBtn" style="display:none">⬆️ Push BOM to OnShape</button>
            </div>
        </div>
        
        <div class="section">
            <h2>📤 Upload & Edit</h2>
            <div class="input-group">
                <label for="fileUpload">Upload CSV or JSON File:</label>
                <input type="file" id="fileUpload" accept=".csv,.json">
            </div>
            <div class="button-group">
                <button id="clearBtn">🗑️ Clear All Data</button>
            </div>
        </div>
        
        <div class="section">
            <h2>📥 Results & Export</h2>
            <div class="button-group">
                <button class="download-btn" id="downloadJsonBtn">⬇️ Download JSON</button>
                <button class="download-btn" id="downloadCsvBtn">⬇️ Download CSV</button>
            </div>
            <div id="results">No data yet. Login and fetch data or upload a file!</div>
        </div>
    </div>

    <script>
        let currentData = null;
        let userId = localStorage.getItem('userId');
        let bomFormat = 'flat';
        let currentDocId = '';
        let currentWorkId = '';
        let currentElemId = '';
        
        if (userId) {
            document.getElementById('userInfo').style.display = 'flex';
            loadUserInfo();
        }
        
        document.getElementById('loginBtn').onclick = () => window.location.href = '/login';
        document.getElementById('getDocsBtn').onclick = getDocuments;
        document.getElementById('getElemsBtn').onclick = getElements;
        document.getElementById('getBomBtn').onclick = getBOM;
        document.getElementById('getBboxBtn').onclick = getBoundingBoxes;
        document.getElementById('getVarsBtn').onclick = getConfigurationVariables;
        document.getElementById('previewLengthsBtn').onclick = previewLengthProperties;
        document.getElementById('createLengthPropsBtn').onclick = createLengthProperties;
        document.getElementById('syncVarsBtn').onclick = syncVariablesToProperties;
        document.getElementById('saveDocBtn').onclick = saveDocument;
        document.getElementById('loadSavedBtn').onclick = loadSavedDocuments;
        document.getElementById('clearBtn').onclick = clearData;
        document.getElementById('downloadJsonBtn').onclick = downloadAsJSON;
        document.getElementById('downloadCsvBtn').onclick = downloadAsCSV;
        document.getElementById('pushBomBtn').onclick = pushBOMToOnShape;
        document.getElementById('fileUpload').onchange = handleFileUpload;
        
        function setBomFormat(format) {
            bomFormat = format;
            document.getElementById('flatBtn').classList.toggle('active', format === 'flat');
            document.getElementById('structBtn').classList.toggle('active', format === 'structured');
        }
        
        async function loadUserInfo() {
            try {
                const r = await fetch('/api/user/info?user_id=' + userId);
                const d = await r.json();
                document.getElementById('userEmail').textContent = d.email || 'User';
            } catch (e) {
                console.error('Failed to load user info');
            }
        }
        
        function logout() {
            localStorage.removeItem('userId');
            userId = null;
            document.getElementById('userInfo').style.display = 'none';
            showResult('Logged out successfully', 'success');
        }
        
        async function saveDocument() {
            if (!userId) {
                showResult('Please login first', 'error');
                return;
            }
            const did = document.getElementById('documentId').value;
            const wid = document.getElementById('workspaceId').value;
            const eid = document.getElementById('elementId').value;
            if (!did || !wid) {
                showResult('Please fill document and workspace ID', 'error');
                return;
            }
            try {
                const r = await fetch('/api/user/save-document', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ user_id: userId, document_id: did, workspace_id: wid, element_id: eid })
                });
                if (r.ok) showResult('✅ Document saved!', 'success');
                else showResult('Failed to save document', 'error');
            } catch (e) {
                showResult('Error: ' + e.message, 'error');
            }
        }
        
        async function loadSavedDocuments() {
            if (!userId) {
                showResult('Please login first', 'error');
                return;
            }
            try {
                const r = await fetch('/api/user/documents?user_id=' + userId);
                const data = await r.json();
                if (!data.length) {
                    showResult('No saved documents found', 'info');
                    return;
                }
                let h = '<h3>Your Saved Documents</h3><table><tr><th>Name</th><th>Document ID</th><th>Last Used</th><th>Action</th></tr>';
                data.forEach(d => {
                    h += '<tr><td>' + (d.document_name || 'Unnamed') + '</td>';
                    h += '<td>' + d.document_id.substring(0, 12) + '...</td>';
                    h += '<td>' + new Date(d.last_used_at).toLocaleString() + '</td>';
                    h += '<td><button onclick="loadDoc(\\''+d.document_id+'\\',\\''+d.workspace_id+'\\',\\''+d.element_id+'\\')">Load</button></td></tr>';
                });
                h += '</table>';
                document.getElementById('results').innerHTML = h;
            } catch (e) {
                showResult('Error loading documents: ' + e.message, 'error');
            }
        }
        
        function loadDoc(did, wid, eid) {
            document.getElementById('documentId').value = did;
            document.getElementById('workspaceId').value = wid || '';
            document.getElementById('elementId').value = eid || '';
            showResult('✅ Document loaded! Click Get BOM or Get Bounding Boxes to fetch data.', 'success');
        }
        
        async function getDocuments() {
            if (!userId) {
                showResult('Please login first', 'error');
                return;
            }
            showResult('Loading documents...', 'info');
            try {
                const r = await fetch('/api/documents?user_id=' + userId);
                const data = await r.json();
                currentData = data;
                displayDocuments(data);
            } catch (e) {
                showResult('Error: ' + e.message, 'error');
            }
        }
        
        async function getElements() {
            if (!userId) {
                showResult('Please login first', 'error');
                return;
            }
            const did = document.getElementById('documentId').value;
            const wid = document.getElementById('workspaceId').value;
            if (!did || !wid) {
                showResult('Please fill document and workspace ID', 'error');
                return;
            }
            showResult('Loading elements...', 'info');
            try {
                const r = await fetch('/api/documents/' + did + '/w/' + wid + '/elements?user_id=' + userId);
                const data = await r.json();
                currentData = data;
                displayElements(data);
            } catch (e) {
                showResult('Error: ' + e.message, 'error');
            }
        }
        
        async function getBOM() {
            if (!userId) {
                showResult('Please login first', 'error');
                return;
            }
            const did = document.getElementById('documentId').value;
            const wid = document.getElementById('workspaceId').value;
            const eid = document.getElementById('elementId').value;
            if (!did || !wid || !eid) {
                showResult('Please fill all fields (Document ID, Workspace ID, Element ID)', 'error');
                return;
            }
            currentDocId = did;
            currentWorkId = wid;
            currentElemId = eid;
            showResult('Loading BOM...', 'info');
            try {
                const r = await fetch('/api/assemblies/' + did + '/w/' + wid + '/e/' + eid + '/bom?user_id=' + userId + '&format=' + bomFormat);
                const data = await r.json();
                currentData = data;
                displayBOM(data);
                document.getElementById('pushBomBtn').style.display = 'inline-block';
            } catch (e) {
                showResult('Error: ' + e.message, 'error');
            }
        }
        
        async function getBoundingBoxes() {
            if (!userId) {
                showResult('Please login first', 'error');
                return;
            }
            const did = document.getElementById('documentId').value;
            const wid = document.getElementById('workspaceId').value;
            const eid = document.getElementById('elementId').value;
            if (!did || !wid || !eid) {
                showResult('Please fill all fields', 'error');
                return;
            }
            showResult('Loading bounding boxes...', 'info');
            try {
                const r = await fetch('/api/partstudios/' + did + '/w/' + wid + '/e/' + eid + '/boundingboxes?user_id=' + userId);
                const data = await r.json();
                currentData = data;
                displayBoundingBoxes(data);
            } catch (e) {
                showResult('Error: ' + e.message, 'error');
            }
        }
        
        async function getConfigurationVariables() {
            if (!userId) {
                showResult('Please login first', 'error');
                return;
            }
            const did = document.getElementById('documentId').value;
            const wid = document.getElementById('workspaceId').value;
            const eid = document.getElementById('elementId').value;
            if (!did || !wid || !eid) {
                showResult('Please fill all fields', 'error');
                return;
            }
            currentDocId = did;
            currentWorkId = wid;
            currentElemId = eid;
            showResult('Loading configuration variables...', 'info');
            try {
                const r = await fetch('/api/partstudios/' + did + '/w/' + wid + '/e/' + eid + '/variables?user_id=' + userId);
                const data = await r.json();
                console.log('Variables response:', data);
                
                if (data.error) {
                    showResult('Error: ' + data.error + (data.message ? ' - ' + data.message : ''), 'error');
                    if (data.debug) {
                        console.log('Debug info:', data.debug);
                    }
                    return;
                }
                
                if (data.message && data.count === 0) {
                    showResult(data.message, 'info');
                    if (data.debug) {
                        console.log('Debug info:', data.debug);
                    }
                    return;
                }
                
                currentData = data;
                displayVariables(data);
                document.getElementById('syncVarsBtn').style.display = 'inline-block';
            } catch (e) {
                console.error('Error fetching variables:', e);
                showResult('Error: ' + e.message, 'error');
            }
        }
        
        async function syncVariablesToProperties() {
            if (!userId || !currentDocId || !currentWorkId || !currentElemId) {
                showResult('Please load configuration variables first', 'error');
                return;
            }
            if (!currentData || !currentData.variables) {
                showResult('No variables to sync', 'error');
                return;
            }
            if (!confirm('Sync configuration variables to custom properties? This will update part metadata in OnShape.')) {
                return;
            }
            showResult('Syncing variables to properties...', 'info');
            try {
                const r = await fetch('/api/partstudios/' + currentDocId + '/w/' + currentWorkId + '/e/' + currentElemId + '/sync-variables', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ user_id: userId, variables: currentData.variables })
                });
                if (r.ok) {
                    const result = await r.json();
                    showResult('✅ Successfully synced ' + result.synced_count + ' variables to properties! They will now appear in BOM.', 'success');
                } else {
                    const error = await r.text();
                    showResult('Failed to sync: ' + error, 'error');
                }
            } catch (e) {
                showResult('Error syncing: ' + e.message, 'error');
            }
        }
        
        async function createLengthProperties() {
            if (!userId) {
                showResult('Please login first', 'error');
                return;
            }
            const did = document.getElementById('documentId').value;
            const wid = document.getElementById('workspaceId').value;
            const eid = document.getElementById('elementId').value;
            if (!did || !wid || !eid) {
                showResult('Please fill all fields', 'error');
                return;
            }
            if (!confirm('Create Length, Width, Height properties from bounding boxes? This will add custom properties to all parts in OnShape.')) {
                return;
            }
            
            console.log('=== CREATE PROPERTIES DEBUG START ===');
            console.log('Document ID:', did);
            console.log('Workspace ID:', wid);
            console.log('Element ID:', eid);
            console.log('User ID:', userId);
            
            showResult('Creating length properties from bounding boxes...', 'info');
            
            try {
                const url = '/api/partstudios/' + did + '/w/' + wid + '/e/' + eid + '/create-length-properties';
                console.log('Posting to URL:', url);
                
                const r = await fetch(url, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ user_id: userId })
                });
                
                console.log('Response status:', r.status);
                console.log('Response OK:', r.ok);
                
                if (r.ok) {
                    const result = await r.json();
                    console.log('Response data:', result);
                    console.log('=== CREATE PROPERTIES DEBUG END ===');
                    
                    let msg = result.message;
                    if (result.errors && result.errors.length > 0) {
                        msg += '<br><br><strong>Errors:</strong><br>' + result.errors.slice(0, 5).join('<br>');
                        console.log('Errors found:', result.errors);
                    }
                    showResult(msg, result.status === 'success' ? 'success' : 'error');
                } else {
                    const error = await r.text();
                    console.error('Request failed:', error);
                    console.log('=== CREATE PROPERTIES
