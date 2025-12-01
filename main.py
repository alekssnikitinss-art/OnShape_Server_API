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
                
                // Check if there's an error or debug message
                if (data.error) {
                    showResult('Error: ' + data.error + (data.message ? ' - ' + data.message : ''), 'error');
                    if (data.debug) {
                        console.log('Debug info:', data.debug);
                    }
                    return;
                }
                
                // Check if message exists (no variables found)
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
                    console.log('=== CREATE PROPERTIES DEBUG END ===');
                    showResult('Failed: ' + error, 'error');
                }
            } catch (e) {
                console.error('Create error:', e);
                console.log('=== CREATE PROPERTIES DEBUG END ===');
                showResult('Error: ' + e.message + ' - Check console for details', 'error');
            }
        }
        
        async function previewLengthProperties() {
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
            
            console.log('=== PREVIEW DEBUG START ===');
            console.log('Document ID:', did);
            console.log('Workspace ID:', wid);
            console.log('Element ID:', eid);
            console.log('User ID:', userId);
            
            showResult('Loading length properties preview...', 'info');
            
            try {
                const url = '/api/partstudios/' + did + '/w/' + wid + '/e/' + eid + '/preview-length-properties?user_id=' + userId;
                console.log('Fetching URL:', url);
                
                const r = await fetch(url);
                console.log('Response status:', r.status);
                console.log('Response OK:', r.ok);
                
                const result = await r.json();
                console.log('Response data:', result);
                console.log('=== PREVIEW DEBUG END ===');
                
                if (result.status === 'success' || result.parts) {
                    displayLengthPreview(result);
                } else {
                    showResult(result.message || 'Failed to load preview. Check console for details.', 'error');
                }
            } catch (e) {
                console.error('Preview error:', e);
                showResult('Error: ' + e.message + ' - Check console for details', 'error');
            }
        }
        
        function displayLengthPreview(data) {
            if (!data.parts || data.parts.length === 0) {
                showResult('No parts found in this element', 'error');
                return;
            }
            let h = '<h3>Length Properties Preview - ' + data.element_type + '</h3>';
            h += '<p style="color:#666;margin-bottom:10px">💡 These values will be added as custom properties. Click "Create Length Properties" to push to OnShape.</p>';
            h += '<table><tr><th>Part Name</th><th>Part ID</th><th>Length (mm)</th><th>Width (mm)</th><th>Height (mm)</th><th>Volume (mm³)</th></tr>';
            data.parts.forEach(function(part) {
                h += '<tr>';
                h += '<td>' + (part.name || 'Unnamed') + '</td>';
                h += '<td>' + (part.partId ? part.partId.substring(0, 12) + '...' : 'Unknown') + '</td>';
                h += '<td><strong>' + part.length + '</strong></td>';
                h += '<td><strong>' + part.width + '</strong></td>';
                h += '<td><strong>' + part.height + '</strong></td>';
                h += '<td>' + part.volume + '</td>';
                h += '</tr>';
            });
            h += '</table>';
            h += '<div style="margin-top:15px;padding:10px;background:#e7f3ff;border-radius:4px">';
            h += '<strong>ℹ️ Next Step:</strong> Click "📐 Create Length Properties" to add these values to OnShape parts.';
            h += '</div>';
            document.getElementById('results').innerHTML = h;
        }
        
        async function pushBOMToOnShape() {
            if (!userId || !currentDocId || !currentWorkId || !currentElemId) {
                showResult('Please load a BOM first', 'error');
                return;
            }
            if (!currentData || !currentData.bomTable || !currentData.bomTable.items) {
                showResult('No BOM data to push', 'error');
                return;
            }
            if (!confirm('Push BOM changes back to OnShape? This will update the assembly.')) {
                return;
            }
            showResult('Pushing BOM to OnShape...', 'info');
            try {
                const r = await fetch('/api/assemblies/' + currentDocId + '/w/' + currentWorkId + '/e/' + currentElemId + '/bom', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ user_id: userId, bomData: currentData })
                });
                if (r.ok) {
                    showResult('✅ BOM successfully pushed to OnShape!', 'success');
                } else {
                    const error = await r.text();
                    showResult('Failed to push BOM: ' + error, 'error');
                }
            } catch (e) {
                showResult('Error pushing BOM: ' + e.message, 'error');
            }
        }
        
        function toggleRow(rowId) {
            const children = document.querySelectorAll('.child-of-' + rowId);
            const icon = document.getElementById('icon-' + rowId);
            children.forEach(child => {
                child.classList.toggle('visible');
            });
            icon.classList.toggle('expanded');
        }
        
        function handleFileUpload(e) {
            const file = e.target.files[0];
            if (!file) return;
            const reader = new FileReader();
            reader.onload = function(ev) {
                const content = ev.target.result;
                if (file.name.endsWith('.json')) {
                    try {
                        currentData = JSON.parse(content);
                        displayUploadedData(currentData);
                    } catch (err) {
                        showResult('JSON parse error: ' + err.message, 'error');
                    }
                } else if (file.name.endsWith('.csv')) {
                    parseCSV(content);
                }
            };
            reader.readAsText(file);
        }
        
        function parseCSV(csv) {
            const lines = csv.split('\\n').filter(l => l.trim());
            if (lines.length < 2) {
                showResult('Empty CSV file', 'error');
                return;
            }
            const headers = lines[0].split(',').map(h => h.trim().replace(/"/g, ''));
            const data = [];
            for (let i = 1; i < lines.length; i++) {
                const values = lines[i].split(',').map(v => v.trim().replace(/"/g, ''));
                const row = {};
                headers.forEach((h, idx) => {
                    row[h] = values[idx] || '';
                });
                data.push(row);
            }
            if (headers.includes('Part Number') || headers.includes('partNumber')) {
                currentData = { bomTable: { items: data } };
            } else {
                currentData = data;
            }
            displayUploadedData(currentData);
        }
        
        function displayUploadedData(data) {
            if (data.bomTable && data.bomTable.items) {
                displayBOM(data);
            } else if (Array.isArray(data) && data[0]) {
                if (data[0]['Length X (mm)'] || data[0].lowX) {
                    displayBoundingBoxes(data);
                } else if (data[0].partNumber || data[0]['Part Number']) {
                    currentData = { bomTable: { items: data } };
                    displayBOM(currentData);
                } else {
                    displayGenericTable(data);
                }
            }
        }
        
        function displayDocuments(data) {
            if (!data.items || !data.items.length) {
                showResult('No documents found', 'error');
                return;
            }
            let h = '<h3>Your OnShape Documents</h3><table><tr><th>Name</th><th>Document ID</th><th>Modified</th><th>Action</th></tr>';
            data.items.forEach(d => {
                h += '<tr><td>' + (d.name || 'Unnamed') + '</td>';
                h += '<td>' + d.id.substring(0, 12) + '...</td>';
                h += '<td>' + new Date(d.modifiedAt).toLocaleString() + '</td>';
                h += '<td><button onclick="document.getElementById(\\'documentId\\').value=\\''+d.id+'\\'">Use This</button></td></tr>';
            });
            h += '</table>';
            document.getElementById('results').innerHTML = h;
        }
        
        function displayElements(data) {
            if (!data || !data.length) {
                showResult('No elements found in this document', 'error');
                return;
            }
            let h = '<h3>Document Elements</h3><table><tr><th>Name</th><th>Type</th><th>Element ID</th><th>Action</th></tr>';
            data.forEach(e => {
                h += '<tr><td>' + (e.name || 'Unnamed') + '</td>';
                h += '<td>' + e.elementType + '</td>';
                h += '<td>' + e.id.substring(0, 12) + '...</td>';
                h += '<td><button onclick="document.getElementById(\\'elementId\\').value=\\''+e.id+'\\'">Use This</button></td></tr>';
            });
            h += '</table>';
            document.getElementById('results').innerHTML = h;
        }
        
        function displayBOM(data) {
            if (!data.bomTable || !data.bomTable.items) {
                showResult('No BOM data found', 'error');
                return;
            }
            
            const items = data.bomTable.items;
            let h = '<h3>Bill of Materials (' + (bomFormat === 'flat' ? 'Flattened' : 'Structured') + ') - Editable</h3>';
            h += '<p style="color:#666;margin-bottom:10px">💡 Click any cell to edit values</p>';
            h += '<table><tr><th>Item</th><th>Part Number</th><th>Name</th><th>Quantity</th><th>Description</th></tr>';
            
            items.forEach((item, idx) => {
                const indent = item.indentLevel || 0;
                const hasChildren = item.hasChildren;
                const parentId = item.parentId || '';
                const rowId = 'row-' + idx;
                const rowClass = parentId ? 'child-row child-of-' + parentId : '';
                const expandable = hasChildren && bomFormat === 'structured';
                
                h += '<tr class="' + rowClass + ' ' + (expandable ? 'expandable-row' : '') + '" ' + (expandable ? 'onclick="toggleRow(\\''+rowId+'\\')"' : '') + '>';
                
                const itemCell = expandable ? '<span id="icon-'+rowId+'" class="expand-icon">▶</span>' : '';
                const indentClass = 'indent-' + Math.min(indent, 3);
                
                h += '<td class="' + indentClass + '">' + itemCell + (item.item || item.Item || '-') + '</td>';
                h += '<td class="editable-cell" contenteditable="true" data-row="'+idx+'" data-field="partNumber">' + (item.partNumber || item.PART_NUMBER || item['Part Number'] || '-') + '</td>';
                h += '<td class="editable-cell" contenteditable="true" data-row="'+idx+'" data-field="name">' + (item.name || item.NAME || item.Name || '-') + '</td>';
                h += '<td class="editable-cell" contenteditable="true" data-row="'+idx+'" data-field="quantity">' + (item.quantity || item.QUANTITY || item.Quantity || '-') + '</td>';
                h += '<td class="editable-cell" contenteditable="true" data-row="'+idx+'" data-field="description">' + (item.description || item.DESCRIPTION || item.Description || '-') + '</td>';
                h += '</tr>';
            });
            h += '</table>';
            document.getElementById('results').innerHTML = h;
            attachEditListeners();
        }
        
        function displayBoundingBoxes(data) {
            if (!data || !data.length) {
                showResult('No bounding box data found', 'error');
                return;
            }
            let h = '<h3>Bounding Boxes (Millimeters) - Editable</h3>';
            h += '<p style="color:#666;margin-bottom:10px">💡 Click cells to edit dimensions</p>';
            h += '<table><tr><th>Part ID</th><th>Length X (mm)</th><th>Length Y (mm)</th><th>Length Z (mm)</th><th>Volume (mm³)</th></tr>';
            data.forEach((box, idx) => {
                let x, y, z, vol, pid;
                if (box['Length X (mm)']) {
                    x = box['Length X (mm)'];
                    y = box['Length Y (mm)'];
                    z = box['Length Z (mm)'];
                    vol = box['Volume (mm³)'];
                    pid = box['Part ID'] || 'Unknown';
                } else {
                    x = ((box.highX - box.lowX) * 1000).toFixed(2);
                    y = ((box.highY - box.lowY) * 1000).toFixed(2);
                    z = ((box.highZ - box.lowZ) * 1000).toFixed(2);
                    vol = (x * y * z).toFixed(2);
                    pid = box.partId || 'Unknown';
                }
                h += '<tr>';
                h += '<td class="editable-cell" contenteditable="true" data-row="'+idx+'" data-field="partId">'+pid+'</td>';
                h += '<td class="editable-cell" contenteditable="true" data-row="'+idx+'" data-field="lengthX">'+x+'</td>';
                h += '<td class="editable-cell" contenteditable="true" data-row="'+idx+'" data-field="lengthY">'+y+'</td>';
                h += '<td class="editable-cell" contenteditable="true" data-row="'+idx+'" data-field="lengthZ">'+z+'</td>';
                h += '<td>'+vol+'</td></tr>';
            });
            h += '</table>';
            document.getElementById('results').innerHTML = h;
            attachEditListeners();
        }
        
        function displayVariables(data) {
            console.log('Displaying variables:', data);
            
            if (!data) {
                showResult('No data received', 'error');
                return;
            }
            
            if (!data.variables || data.variables.length === 0) {
                let msg = 'No configuration variables found';
                if (data.message) {
                    msg = data.message;
                }
                if (data.debug) {
                    msg += '<br><br><strong>Debug Info:</strong><br>';
                    msg += 'Features API status: ' + data.debug.features_status + '<br>';
                    msg += 'Parts API status: ' + data.debug.parts_status;
                }
                showResult(msg, 'info');
                return;
            }
            
            let h = '<h3>Configuration Variables - Found ' + data.count + ' variables</h3>';
            h += '<p style="color:#666;margin-bottom:10px">💡 These are configuration variables and properties. Click "Sync Variables to Properties" to add them to BOM.</p>';
            h += '<table><tr><th>Variable Name</th><th>Value</th><th>Unit</th><th>Part/Feature</th></tr>';
            data.variables.forEach((v, idx) => {
                h += '<tr>';
                h += '<td><strong>' + (v.name || v.variableName || 'Unknown') + '</strong></td>';
                h += '<td class="editable-cell" contenteditable="true" data-row="'+idx+'" data-field="value">' + (v.value || v.expression || '-') + '</td>';
                h += '<td>' + (v.unit || v.units || '-') + '</td>';
                h += '<td>' + (v.partName || v.partId || v.featureId || 'Global') + '</td>';
                h += '</tr>';
            });
            h += '</table>';
            h += '<p style="color:#0066cc;margin-top:15px;padding:10px;background:#e7f3ff;border-radius:4px">';
            h += '<strong>ℹ️ Info:</strong> After syncing, these variables will appear as custom properties in your parts and will be visible in the BOM table.';
            h += '</p>';
            document.getElementById('results').innerHTML = h;
            attachEditListeners();
        }
        
        function displayGenericTable(data) {
            const headers = Object.keys(data[0]);
            let h = '<h3>Data Table - Editable</h3><table><tr>';
            headers.forEach(hh => h += '<th>'+hh+'</th>');
            h += '</tr>';
            data.forEach((row, idx) => {
                h += '<tr>';
                headers.forEach(hh => {
                    h += '<td class="editable-cell" contenteditable="true" data-row="'+idx+'" data-field="'+hh+'">'+(row[hh]||'')+'</td>';
                });
                h += '</tr>';
            });
            h += '</table>';
            document.getElementById('results').innerHTML = h;
            attachEditListeners();
        }
        
        function attachEditListeners() {
            document.querySelectorAll('.editable-cell').forEach(cell => {
                cell.addEventListener('blur', function() {
                    const row = parseInt(this.dataset.row);
                    const field = this.dataset.field;
                    const val = this.textContent.trim();
                    if (currentData.bomTable && currentData.bomTable.items) {
                        currentData.bomTable.items[row][field] = val;
                    } else if (Array.isArray(currentData)) {
                        currentData[row][field] = val;
                    }
                });
            });
        }
        
        function clearData() {
            if (confirm('Clear all data?')) {
                currentData = null;
                document.getElementById('results').innerHTML = 'No data';
                document.getElementById('fileUpload').value = '';
                document.getElementById('pushBomBtn').style.display = 'none';
            }
        }
        
        function downloadAsJSON() {
            if (!currentData) {
                alert('No data to download');
                return;
            }
            const blob = new Blob([JSON.stringify(currentData, null, 2)], {type: 'application/json'});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'onshape-data-' + Date.now() + '.json';
            a.click();
            URL.revokeObjectURL(url);
        }
        
        function downloadAsCSV() {
            if (!currentData) {
                alert('No data to download');
                return;
            }
            let csv = '';
            if (currentData.bomTable && currentData.bomTable.items) {
                csv = 'Item,Part Number,Name,Quantity,Description\\n';
                currentData.bomTable.items.forEach(item => {
                    csv += '"'+(item.item||item.Item||'')+'","'+(item.partNumber||item.PART_NUMBER||'')+'","'+(item.name||item.NAME||'')+'","'+(item.quantity||item.QUANTITY||'')+'","'+(item.description||item.DESCRIPTION||'')+'"\\n';
                });
            } else if (Array.isArray(currentData) && currentData.length > 0) {
                const headers = Object.keys(currentData[0]);
                csv = headers.join(',') + '\\n';
                currentData.forEach(row => {
                    csv += headers.map(h => '"'+(row[h]||'')+'"').join(',') + '\\n';
                });
            }
            const blob = new Blob([csv], {type: 'text/csv'});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'onshape-data-' + Date.now() + '.csv';
            a.click();
            URL.revokeObjectURL(url);
        }
        
        function showResult(msg, type) {
            const div = document.getElementById('results');
            div.innerHTML = '<div class="' + (type || '') + '">' + msg + '</div>';
        }
    </script>
</body>
</html>"""

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
            
            return f"""<html><body style='font-family:Arial;padding:50px;text-align:center;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%)'><div style='background:white;padding:40px;border-radius:12px;max-width:500px;margin:0 auto'><h1 style='color:green'>✅ Success!</h1>
            <p>Logged in as <strong>{email}</strong></p><p>Redirecting...</p><script>localStorage.setItem('userId','{user.user_id}');
            setTimeout(()=>{{window.location.href='/'}},2000);</script></div></body></html>"""
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
    async def get_bom(did: str, wid: str, eid: str, user_id: str, format: str = "flat", db: Session = Depends(get_db)):
        token = get_user_token(user_id, db)
        if format == "flat":
            url = f"https://cad.onshape.com/api/assemblies/d/{did}/w/{wid}/e/{eid}/bom?indented=false"
        else:
            url = f"https://cad.onshape.com/api/assemblies/d/{did}/w/{wid}/e/{eid}/bom?indented=true"
        resp = requests.get(url, headers={"Authorization": f"Bearer {token}"})
        return JSONResponse(resp.json(), resp.status_code)

    @app.post("/api/assemblies/{did}/w/{wid}/e/{eid}/bom")
    async def push_bom(did: str, wid: str, eid: str, request: Request, db: Session = Depends(get_db)):
        data = await request.json()
        user_id = data.get("user_id")
        bom_data = data.get("bomData")
        
        if not user_id or not bom_data:
            raise HTTPException(400, "Missing user_id or bomData")
        
        token = get_user_token(user_id, db)
        
        # Note: OnShape API doesn't directly support BOM updates via REST API
        # This would require using the custom properties or metadata endpoints
        # For now, we'll return a message
        return JSONResponse({
            "status": "info",
            "message": "BOM push functionality requires OnShape Custom Properties API. Your edited data is saved locally and can be downloaded."
        })

    @app.get("/api/partstudios/{did}/w/{wid}/e/{eid}/boundingboxes")
    async def get_bounding_boxes(did: str, wid: str, eid: str, user_id: str, db: Session = Depends(get_db)):
        token = get_user_token(user_id, db)
        url = f"https://cad.onshape.com/api/partstudios/d/{did}/w/{wid}/e/{eid}/boundingboxes"
        resp = requests.get(url, headers={"Authorization": f"Bearer {token}"})
        return JSONResponse(resp.json(), resp.status_code)

    @app.get("/api/partstudios/{did}/w/{wid}/e/{eid}/variables")
    async def get_variables(did: str, wid: str, eid: str, user_id: str, db: Session = Depends(get_db)):
        """Get configuration variables from part studio"""
        token = get_user_token(user_id, db)
        variables = []
        
        try:
            # Method 1: Get configuration info from element
            config_url = f"https://cad.onshape.com/api/elements/d/{did}/w/{wid}/e/{eid}/configuration"
            config_resp = requests.get(config_url, headers={"Authorization": f"Bearer {token}"})
            
            if config_resp.status_code == 200:
                try:
                    config_data = config_resp.json()
                    if isinstance(config_data, dict) and 'configurationParameters' in config_data:
                        for param in config_data.get('configurationParameters', []):
                            if not isinstance(param, dict):
                                continue
                            param_type = param.get('parameterType', '')
                            if 'Quantity' in param_type or 'String' in param_type or 'Number' in param_type:
                                msg = param.get('message', {})
                                if isinstance(msg, dict):
                                    variables.append({
                                        'name': msg.get('parameterName', param.get('parameterId', 'Unknown')),
                                        'value': str(msg.get('defaultValue', '')),
                                        'unit': msg.get('units', ''),
                                        'partId': 'Configuration',
                                        'partName': 'Config Parameter'
                                    })
                except:
                    pass
            
            # Method 2: Get parts and their properties
            parts_url = f"https://cad.onshape.com/api/parts/d/{did}/w/{wid}/e/{eid}"
            parts_resp = requests.get(parts_url, headers={"Authorization": f"Bearer {token}"})
            
            if parts_resp.status_code == 200:
                try:
                    parts_data = parts_resp.json()
                    if isinstance(parts_data, list):
                        for part in parts_data:
                            if not isinstance(part, dict):
                                continue
                            part_id = part.get('partId')
                            part_name = part.get('name', 'Unknown')
                            
                            if not part_id:
                                continue
                            
                            try:
                                meta_url = f"https://cad.onshape.com/api/metadata/d/{did}/w/{wid}/e/{eid}/p/{part_id}"
                                meta_resp = requests.get(meta_url, headers={"Authorization": f"Bearer {token}"})
                                
                                if meta_resp.status_code == 200:
                                    metadata = meta_resp.json()
                                    if isinstance(metadata, dict) and 'properties' in metadata:
                                        props = metadata.get('properties', [])
                                        if isinstance(props, list):
                                            for prop in props:
                                                if not isinstance(prop, dict):
                                                    continue
                                                prop_name = prop.get('name', '')
                                                if prop_name and (prop_name.startswith('#') or 'length' in prop_name.lower() or 'width' in prop_name.lower() or 'height' in prop_name.lower()):
                                                    variables.append({
                                                        'name': prop_name,
                                                        'value': str(prop.get('value', '')),
                                                        'unit': prop.get('units', ''),
                                                        'partId': part_id,
                                                        'partName': part_name
                                                    })
                            except:
                                pass
                except:
                    pass
            
            # Method 3: Get features (variables)
            features_url = f"https://cad.onshape.com/api/partstudios/d/{did}/w/{wid}/e/{eid}/features"
            features_resp = requests.get(features_url, headers={"Authorization": f"Bearer {token}"})
            
            if features_resp.status_code == 200:
                try:
                    features_data = features_resp.json()
                    if isinstance(features_data, dict) and 'features' in features_data:
                        for feature in features_data.get('features', []):
                            if not isinstance(feature, dict):
                                continue
                            msg = feature.get('message', {})
                            if not isinstance(msg, dict):
                                continue
                            feature_type = msg.get('featureType', '')
                            if 'variable' in feature_type.lower():
                                params = msg.get('parameters', [])
                                if isinstance(params, list):
                                    for param in params:
                                        if not isinstance(param, dict):
                                            continue
                                        param_msg = param.get('message', {})
                                        if isinstance(param_msg, dict):
                                            var_name = param_msg.get('variableName') or param.get('variableName')
                                            if var_name:
                                                variables.append({
                                                    'name': var_name,
                                                    'value': param_msg.get('expression', param.get('expression', '')),
                                                    'unit': '',
                                                    'featureId': feature.get('featureId', ''),
                                                    'partId': 'Variable Feature'
                                                })
                except:
                    pass
            
            # Method 4: If still nothing, use bounding boxes as fallback
            if len(variables) == 0:
                try:
                    bbox_url = f"https://cad.onshape.com/api/partstudios/d/{did}/w/{wid}/e/{eid}/boundingboxes"
                    bbox_resp = requests.get(bbox_url, headers={"Authorization": f"Bearer {token}"})
                    
                    if bbox_resp.status_code == 200:
                        bbox_data = bbox_resp.json()
                        if isinstance(bbox_data, list):
                            for box in bbox_data:
                                if not isinstance(box, dict):
                                    continue
                                length_x = (box.get('highX', 0) - box.get('lowX', 0)) * 1000
                                length_y = (box.get('highY', 0) - box.get('lowY', 0)) * 1000
                                length_z = (box.get('highZ', 0) - box.get('lowZ', 0)) * 1000
                                
                                part_id = box.get('partId', 'Unknown')
                                dimensions = sorted([length_x, length_y, length_z], reverse=True)
                                
                                variables.append({'name': 'BBox_Length', 'value': f"{dimensions[0]:.2f}", 'unit': 'mm', 'partId': part_id, 'partName': 'From BoundingBox'})
                                variables.append({'name': 'BBox_Width', 'value': f"{dimensions[1]:.2f}", 'unit': 'mm', 'partId': part_id, 'partName': 'From BoundingBox'})
                                variables.append({'name': 'BBox_Height', 'value': f"{dimensions[2]:.2f}", 'unit': 'mm', 'partId': part_id, 'partName': 'From BoundingBox'})
                except:
                    pass
            
            if len(variables) == 0:
                return JSONResponse({
                    "variables": [],
                    "count": 0,
                    "message": "No configuration variables found. Try using 'Create Length Properties' button instead to automatically create Length/Width/Height from bounding boxes.",
                    "debug": {
                        "config_status": config_resp.status_code if 'config_resp' in locals() else "not_called",
                        "parts_status": parts_resp.status_code if 'parts_resp' in locals() else "not_called",
                        "features_status": features_resp.status_code if 'features_resp' in locals() else "not_called"
                    }
                })
            
            return JSONResponse({"variables": variables, "count": len(variables)})
            
        except Exception as e:
            return JSONResponse({
                "error": str(e)[:200],
                "variables": variables,
                "count": len(variables),
                "message": f"Found {len(variables)} variables. Error: {str(e)[:100]}"
            }, status_code=200)

    @app.get("/api/partstudios/{did}/w/{wid}/e/{eid}/preview-length-properties")
    async def preview_length_properties(did: str, wid: str, eid: str, user_id: str, db: Session = Depends(get_db)):
        """Preview Length, Width, Height for all parts WITHOUT creating properties"""
        token = get_user_token(user_id, db)
        
        try:
            # Try Part Studio first
            bbox_url = f"https://cad.onshape.com/api/partstudios/d/{did}/w/{wid}/e/{eid}/boundingboxes"
            bbox_resp = requests.get(bbox_url, headers={"Authorization": f"Bearer {token}"})
            
            bbox_data = []
            element_type = "Part Studio"
            
            if bbox_resp.status_code == 400:
                # It's an Assembly
                element_type = "Assembly"
                assembly_url = f"https://cad.onshape.com/api/assemblies/d/{did}/w/{wid}/e/{eid}"
                assembly_resp = requests.get(assembly_url, headers={"Authorization": f"Bearer {token}"})
                
                if assembly_resp.status_code != 200:
                    raise HTTPException(500, f"Failed to get assembly")
                
                assembly_data = assembly_resp.json()
                parts = assembly_data.get('parts', [])
                
                for part in parts:
                    if not isinstance(part, dict):
                        continue
                    part_id = part.get('partId')
                    part_name = part.get('name', 'Unnamed')
                    document_id = part.get('documentId', did)
                    element_id = part.get('elementId')
                    
                    if not part_id or not element_id:
                        continue
                    
                    # Get bounding box
                    part_bbox_url = f"https://cad.onshape.com/api/parts/d/{document_id}/w/{wid}/e/{element_id}/partid/{part_id}/bodyboundingbox"
                    part_bbox_resp = requests.get(part_bbox_url, headers={"Authorization": f"Bearer {token}"})
                    
                    if part_bbox_resp.status_code == 200:
                        bbox_info = part_bbox_resp.json()
                        if isinstance(bbox_info, dict):
                            bbox_data.append({
                                'partId': part_id,
                                'name': part_name,
                                'lowX': bbox_info.get('lowX', 0),
                                'lowY': bbox_info.get('lowY', 0),
                                'lowZ': bbox_info.get('lowZ', 0),
                                'highX': bbox_info.get('highX', 0),
                                'highY': bbox_info.get('highY', 0),
                                'highZ': bbox_info.get('highZ', 0)
                            })
                            
            elif bbox_resp.status_code == 200:
                # It's a Part Studio
                bbox_data_raw = bbox_resp.json()
                if isinstance(bbox_data_raw, list):
                    # Also get part names
                    parts_url = f"https://cad.onshape.com/api/parts/d/{did}/w/{wid}/e/{eid}"
                    parts_resp = requests.get(parts_url, headers={"Authorization": f"Bearer {token}"})
                    part_names = {}
                    if parts_resp.status_code == 200:
                        parts_data = parts_resp.json()
                        if isinstance(parts_data, list):
                            for p in parts_data:
                                if isinstance(p, dict):
                                    part_names[p.get('partId')] = p.get('name', 'Unnamed')
                    
                    for box in bbox_data_raw:
                        if isinstance(box, dict):
                            part_id = box.get('partId')
                            box['name'] = part_names.get(part_id, 'Unnamed')
                            bbox_data.append(box)
            else:
                raise HTTPException(500, f"Failed to get bounding boxes")
            
            if not bbox_data:
                return JSONResponse({
                    "status": "error",
                    "message": f"No parts found in this {element_type}",
                    "parts": []
                })
            
            # Process and calculate dimensions
            parts_preview = []
            for box in bbox_data:
                if not isinstance(box, dict):
                    continue
                
                length_x = (box.get('highX', 0) - box.get('lowX', 0)) * 1000
                length_y = (box.get('highY', 0) - box.get('lowY', 0)) * 1000
                length_z = (box.get('highZ', 0) - box.get('lowZ', 0)) * 1000
                
                if length_x == 0 and length_y == 0 and length_z == 0:
                    continue
                
                dimensions = sorted([length_x, length_y, length_z], reverse=True)
                length = dimensions[0]
                width = dimensions[1]
                height = dimensions[2]
                volume = length * width * height
                
                parts_preview.append({
                    'partId': box.get('partId', 'Unknown'),
                    'name': box.get('name', 'Unnamed'),
                    'length': f"{length:.2f}",
                    'width': f"{width:.2f}",
                    'height': f"{height:.2f}",
                    'volume': f"{volume:.2f}"
                })
            
            return JSONResponse({
                "status": "success",
                "element_type": element_type,
                "parts_count": len(parts_preview),
                "parts": parts_preview,
                "message": f"Found {len(parts_preview)} parts in {element_type}"
            })
            
        except HTTPException:
            raise
        except Exception as e:
            return JSONResponse({
                "status": "error",
                "message": str(e)[:200],
                "parts": []
            }, status_code=500)

    @app.post("/api/partstudios/{did}/w/{wid}/e/{eid}/create-length-properties")
    async def create_length_properties(did: str, wid: str, eid: str, request: Request, db: Session = Depends(get_db)):
        """Create Length, Width, Height custom properties - works for BOTH Part Studio AND Assembly"""
        data = await request.json()
        user_id = data.get("user_id")
        
        if not user_id:
            raise HTTPException(400, "Missing user_id")
        
        token = get_user_token(user_id, db)
        parts_count = 0
        errors = []
        
        try:
            # Try Part Studio first
            bbox_url = f"https://cad.onshape.com/api/partstudios/d/{did}/w/{wid}/e/{eid}/boundingboxes"
            bbox_resp = requests.get(bbox_url, headers={"Authorization": f"Bearer {token}"})
            
            bbox_data = []
            element_type = "Part Studio"
            
            if bbox_resp.status_code == 400:
                # It's an Assembly! Get parts from assembly
                element_type = "Assembly"
                assembly_url = f"https://cad.onshape.com/api/assemblies/d/{did}/w/{wid}/e/{eid}"
                assembly_resp = requests.get(assembly_url, headers={"Authorization": f"Bearer {token}"})
                
                if assembly_resp.status_code != 200:
                    raise HTTPException(500, f"Failed to get assembly: Status {assembly_resp.status_code}")
                
                try:
                    assembly_data = assembly_resp.json()
                except:
                    raise HTTPException(500, "Assembly response is not valid JSON")
                
                parts = assembly_data.get('parts', [])
                
                if not parts:
                    raise HTTPException(400, "Assembly has no parts. Add parts to the assembly first.")
                
                # For each part in assembly, get its bounding box
                for part in parts:
                    if not isinstance(part, dict):
                        continue
                        
                    part_id = part.get('partId')
                    document_id = part.get('documentId', did)
                    element_id = part.get('elementId')
                    
                    if not part_id or not element_id:
                        continue
                    
                    # Get bounding box from source Part Studio
                    part_bbox_url = f"https://cad.onshape.com/api/parts/d/{document_id}/w/{wid}/e/{element_id}/partid/{part_id}/bodyboundingbox"
                    part_bbox_resp = requests.get(part_bbox_url, headers={"Authorization": f"Bearer {token}"})
                    
                    if part_bbox_resp.status_code == 200:
                        try:
                            bbox_info = part_bbox_resp.json()
                            if isinstance(bbox_info, dict):
                                bbox_data.append({
                                    'partId': part_id,
                                    'documentId': document_id,
                                    'elementId': element_id,
                                    'lowX': bbox_info.get('lowX', 0),
                                    'lowY': bbox_info.get('lowY', 0),
                                    'lowZ': bbox_info.get('lowZ', 0),
                                    'highX': bbox_info.get('highX', 0),
                                    'highY': bbox_info.get('highY', 0),
                                    'highZ': bbox_info.get('highZ', 0)
                                })
                        except:
                            errors.append(f"Part {part_id}: Invalid bbox JSON")
                            
            elif bbox_resp.status_code == 200:
                # It's a Part Studio
                try:
                    bbox_data_raw = bbox_resp.json()
                    if isinstance(bbox_data_raw, list):
                        for box in bbox_data_raw:
                            if isinstance(box, dict):
                                box['documentId'] = did
                                box['elementId'] = eid
                                bbox_data.append(box)
                except:
                    raise HTTPException(500, "Bounding box response is not valid JSON")
            else:
                raise HTTPException(500, f"Failed to get bounding boxes: Status {bbox_resp.status_code}")
            
            if not bbox_data:
                return JSONResponse({
                    "status": "error",
                    "parts_count": 0,
                    "message": f"No parts with geometry found in this {element_type}.",
                    "errors": errors if errors else ["No bounding box data available"]
                })
            
            # Process each part
            for box in bbox_data:
                if not isinstance(box, dict):
                    continue
                    
                part_id = box.get('partId')
                part_doc_id = box.get('documentId', did)
                part_elem_id = box.get('elementId', eid)
                
                if not part_id:
                    continue
                
                try:
                    # Calculate dimensions in mm
                    length_x = (box.get('highX', 0) - box.get('lowX', 0)) * 1000
                    length_y = (box.get('highY', 0) - box.get('lowY', 0)) * 1000
                    length_z = (box.get('highZ', 0) - box.get('lowZ', 0)) * 1000
                    
                    if length_x == 0 and length_y == 0 and length_z == 0:
                        errors.append(f"Part {part_id[:8]}: No geometry")
                        continue
                    
                    # Sort to get Length (max), Width (mid), Height (min)
                    dimensions = sorted([length_x, length_y, length_z], reverse=True)
                    length = dimensions[0]
                    width = dimensions[1]
                    height = dimensions[2]
                    
                    # Step 1: GET existing metadata
                    get_meta_url = f"https://cad.onshape.com/api/metadata/d/{part_doc_id}/w/{wid}/e/{part_elem_id}/p/{part_id}"
                    get_meta_resp = requests.get(get_meta_url, headers={"Authorization": f"Bearer {token}"})
                    
                    if get_meta_resp.status_code != 200:
                        errors.append(f"Part {part_id[:8]}: Cannot get metadata")
                        continue
                    
                    try:
                        existing_meta = get_meta_resp.json()
                        if not isinstance(existing_meta, dict):
                            errors.append(f"Part {part_id[:8]}: Invalid metadata")
                            continue
                    except:
                        errors.append(f"Part {part_id[:8]}: Invalid metadata JSON")
                        continue
                    
                    # Build properties
                    properties_to_update = []
                    for prop_name, prop_value in [("Length", length), ("Width", width), ("Height", height)]:
                        existing_prop = None
                        if 'properties' in existing_meta and isinstance(existing_meta['properties'], list):
                            for prop in existing_meta['properties']:
                                if isinstance(prop, dict) and prop.get('name') == prop_name:
                                    existing_prop = prop
                                    break
                        
                        if existing_prop and 'propertyId' in existing_prop:
                            properties_to_update.append({
                                "propertyId": existing_prop['propertyId'],
                                "value": f"{prop_value:.2f} mm"
                            })
                        else:
                            properties_to_update.append({
                                "name": prop_name,
                                "value": f"{prop_value:.2f} mm",
                                "valueType": "STRING"
                            })
                    
                    # Step 2: POST update
                    href = existing_meta.get('href', get_meta_url)
                    update_payload = {
                        "items": [{
                            "href": href,
                            "properties": properties_to_update
                        }]
                    }
                    
                    post_meta_url = f"https://cad.onshape.com/api/metadata/d/{part_doc_id}/w/{wid}/e/{part_elem_id}"
                    post_meta_resp = requests.post(
                        post_meta_url,
                        headers={
                            "Authorization": f"Bearer {token}",
                            "Content-Type": "application/json"
                        },
                        json=update_payload
                    )
                    
                    if post_meta_resp.status_code in [200, 201, 204]:
                        parts_count += 1
                    else:
                        errors.append(f"Part {part_id[:8]}: POST failed {post_meta_resp.status_code}")
                        
                except Exception as e:
                    errors.append(f"Part {part_id[:8] if part_id else 'unknown'}: {str(e)[:50]}")
                    continue
            
            result = {
                "status": "success" if parts_count > 0 else "error",
                "parts_count": parts_count,
                "element_type": element_type,
                "message": f"✅ Updated {parts_count} parts in {element_type}! Open BOM in OnShape and click 'Update BOM' to see Length, Width, Height columns." if parts_count > 0 else "Failed to update any parts. Check errors below."
            }
            
            if errors:
                result["errors"] = errors[:10]
                result["total_errors"] = len(errors)
            
            return JSONResponse(result)
            
        except HTTPException:
            raise
        except Exception as e:
            return JSONResponse({
                "status": "error",
                "parts_count": 0,
                "message": f"Server error: {str(e)[:200]}",
                "errors": [str(e)]
            }, status_code=500)

    async def sync_variables(did: str, wid: str, eid: str, request: Request, db: Session = Depends(get_db)):
        """Sync configuration variables to custom properties so they appear in BOM"""
        data = await request.json()
        user_id = data.get("user_id")
        variables = data.get("variables", [])
        
        if not user_id or not variables:
            raise HTTPException(400, "Missing user_id or variables")
        
        token = get_user_token(user_id, db)
        synced_count = 0
        
        # Group variables by part
        parts_vars = {}
        for var in variables:
            part_id = var.get('partId', 'Global')
            if part_id not in parts_vars:
                parts_vars[part_id] = []
            parts_vars[part_id].append(var)
        
        # For each part, update metadata with custom properties
        for part_id, part_vars in parts_vars.items():
            if part_id == 'Global':
                continue
                
            # Build metadata update payload
            properties = []
            for var in part_vars:
                properties.append({
                    "name": var.get('name', '').replace('#', ''),  # Remove # prefix
                    "value": var.get('value', ''),
                    "propertyId": "custom_" + var.get('name', '').replace('#', '').lower()
                })
            
            # Update part metadata
            meta_url = f"https://cad.onshape.com/api/metadata/d/{did}/w/{wid}/e/{eid}/p/{part_id}"
            meta_payload = {"properties": properties}
            
            meta_resp = requests.post(
                meta_url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                json=meta_payload
            )
            
            if meta_resp.status_code in [200, 201, 204]:
                synced_count += len(part_vars)
        
        return JSONResponse({
            "status": "success",
            "synced_count": synced_count,
            "message": f"Synced {synced_count} variables to custom properties. Refresh BOM to see changes."
        })
