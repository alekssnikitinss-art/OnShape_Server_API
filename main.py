import os
import base64
import json
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
import requests
from sqlalchemy import create_engine, Column, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from cryptography.fernet import Fernet

app = FastAPI()

# Environment variables
CLIENT_ID = os.getenv("ONSHAPE_CLIENT_ID")
CLIENT_SECRET = os.getenv("ONSHAPE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
DATABASE_URL = os.getenv("DATABASE_URL")
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

AUTH_URL = "https://oauth.onshape.com/oauth/authorize"
TOKEN_URL = "https://oauth.onshape.com/oauth/token"
SCOPE = "OAuth2Read OAuth2Write"

# Database setup
Base = declarative_base()
engine = create_engine(DATABASE_URL) if DATABASE_URL else None
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine) if engine else None

# Encryption
cipher = Fernet(ENCRYPTION_KEY.encode()) if ENCRYPTION_KEY else None

def encrypt_token(token):
    if not cipher:
        return token
    return cipher.encrypt(token.encode()).decode()

def decrypt_token(encrypted_token):
    if not cipher:
        return encrypted_token
    return cipher.decrypt(encrypted_token.encode()).decode()

# Database Models
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

# Create tables
if engine:
    Base.metadata.create_all(bind=engine)

# Dependency
def get_db():
    if not SessionLocal:
        raise HTTPException(500, "Database not configured")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_html_content():
    html = """<!DOCTYPE html>
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
            max-width: 1200px;
            margin: 30px auto;
            background: white;
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }
        h1 { color: #333; margin-bottom: 20px; text-align: center; }
        h2 {
            color: #555;
            margin: 25px 0 15px 0;
            padding-bottom: 10px;
            border-bottom: 2px solid #667eea;
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
        }
        .success {
            color: #155724;
            padding: 10px;
            background: #d4edda;
            border-radius: 4px;
        }
        .info {
            color: #004085;
            padding: 10px;
            background: #cce5ff;
            border-radius: 4px;
        }
        pre {
            background: #2d2d2d;
            color: #f8f8f2;
            padding: 15px;
            border-radius: 4px;
            overflow-x: auto;
            font-size: 12px;
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
        }
        .editable-cell:hover { background: #fff3cd; }
        .download-btn { background: #28a745; }
        .download-btn:hover { background: #218838; }
        .grid-2 {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
        }
        @media (max-width: 768px) {
            .grid-2 { grid-template-columns: 1fr; }
        }
        .user-info {
            background: #e7f3ff;
            padding: 10px;
            border-radius: 4px;
            margin-bottom: 15px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔧 OnShape BOM Manager (with Database)</h1>
        
        <div class="section">
            <h2>Authentication</h2>
            <div id="userInfo" class="user-info" style="display:none;">
                <strong>Logged in as:</strong> <span id="userEmail"></span> |
                <button onclick="logout()" style="padding: 5px 10px; font-size: 14px;">Logout</button>
            </div>
            <div class="button-group">
                <button id="loginBtn">🔐 Login with OnShape</button>
                <button id="loadSavedDocsBtn">📂 Load Saved Documents</button>
            </div>
        </div>
        
        <div class="section">
            <h2>Document Information</h2>
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
                <label for="elementId">Element ID:</label>
                <input type="text" id="elementId" placeholder="e.g., 9z8y7x6w5v4u3t2s1r0q">
            </div>
            <div class="button-group">
                <button id="getDocsBtn">📁 List My Documents</button>
                <button id="getElemsBtn">📄 Get Elements</button>
                <button id="getBomBtn">📊 Get BOM</button>
                <button id="getBboxBtn">📏 Get Bounding Boxes</button>
                <button id="saveDocBtn">💾 Save This Document</button>
            </div>
        </div>
        
        <div class="section">
            <h2>Upload & Edit BOM</h2>
            <div class="input-group">
                <label for="fileUpload">Upload CSV or JSON:</label>
                <input type="file" id="fileUpload" accept=".csv,.json">
            </div>
            <div class="button-group">
                <button id="clearBtn">🗑️ Clear All</button>
            </div>
        </div>
        
        <div class="section">
            <h2>Results</h2>
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
        
        // Check if user is logged in
        if (userId) {
            document.getElementById('userInfo').style.display = 'block';
            loadUserInfo();
        }
        
        document.getElementById('loginBtn').addEventListener('click', function() {
            window.location.href = '/login';
        });
        
        document.getElementById('getDocsBtn').addEventListener('click', getDocuments);
        document.getElementById('getElemsBtn').addEventListener('click', getElements);
        document.getElementById('getBomBtn').addEventListener('click', getBOM);
        document.getElementById('getBboxBtn').addEventListener('click', getBoundingBoxes);
        document.getElementById('saveDocBtn').addEventListener('click', saveDocument);
        document.getElementById('loadSavedDocsBtn').addEventListener('click', loadSavedDocuments);
        document.getElementById('clearBtn').addEventListener('click', clearData);
        document.getElementById('downloadJsonBtn').addEventListener('click', downloadAsJSON);
        document.getElementById('downloadCsvBtn').addEventListener('click', downloadAsCSV);
        document.getElementById('fileUpload').addEventListener('change', handleFileUpload);
        
        async function loadUserInfo() {
            try {
                const res = await fetch('/api/user/info?user_id=' + userId);
                const data = await res.json();
                document.getElementById('userEmail').textContent = data.email || 'User';
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
                const res = await fetch('/api/user/save-document', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        user_id: userId,
                        document_id: did,
                        workspace_id: wid,
                        element_id: eid
                    })
                });
                if (res.ok) {
                    showResult('✅ Document saved!', 'success');
                } else {
                    showResult('Failed to save document', 'error');
                }
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
                const res = await fetch('/api/user/documents?user_id=' + userId);
                const data = await res.json();
                if (data.length === 0) {
                    showResult('No saved documents', 'info');
                    return;
                }
                let html = '<h3>Your Saved Documents</h3><table>';
                html += '<tr><th>Document Name</th><th>Document ID</th><th>Last Used</th><th>Action</th></tr>';
                data.forEach(function(doc) {
                    html += '<tr><td>' + (doc.document_name || 'Unnamed') + '</td>';
                    html += '<td>' + doc.document_id + '</td>';
                    html += '<td>' + new Date(doc.last_used_at).toLocaleString() + '</td>';
                    html += '<td><button onclick="loadDoc(\\''+doc.document_id+'\\',\\''+doc.workspace_id+'\\',\\''+doc.element_id+'\\')">Load</button></td></tr>';
                });
                html += '</table>';
                document.getElementById('results').innerHTML = html;
            } catch (e) {
                showResult('Error: ' + e.message, 'error');
            }
        }
        
        function loadDoc(did, wid, eid) {
            document.getElementById('documentId').value = did;
            document.getElementById('workspaceId').value = wid || '';
            document.getElementById('elementId').value = eid || '';
            showResult('✅ Document loaded! Click Get BOM or Get Bounding Boxes', 'success');
        }
        
        async function getDocuments() {
            if (!userId) {
                showResult('Please login first', 'error');
                return;
            }
            showResult('Loading...', 'info');
            try {
                const res = await fetch('/api/documents?user_id=' + userId);
                const data = await res.json();
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
            showResult('Loading...', 'info');
            try {
                const res = await fetch('/api/documents/' + did + '/w/' + wid + '/elements?user_id=' + userId);
                const data = await res.json();
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
                showResult('Please fill all fields', 'error');
                return;
            }
            showResult('Loading BOM...', 'info');
            try {
                const res = await fetch('/api/assemblies/' + did + '/w/' + wid + '/e/' + eid + '/bom?user_id=' + userId);
                const data = await res.json();
                currentData = data;
                displayBOM(data);
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
            showResult('Loading...', 'info');
            try {
                const res = await fetch('/api/partstudios/' + did + '/w/' + wid + '/e/' + eid + '/boundingboxes?user_id=' + userId);
                const data = await res.json();
                currentData = data;
                displayBoundingBoxes(data);
            } catch (e) {
                showResult('Error: ' + e.message, 'error');
            }
        }
        
        function handleFileUpload(event) {
            const file = event.target.files[0];
            if (!file) return;
            const reader = new FileReader();
            reader.onload = function(e) {
                const content = e.target.result;
                if (file.name.endsWith('.json')) {
                    try {
                        currentData = JSON.parse(content);
                        displayUploadedData(currentData);
                    } catch (err) {
                        showResult('JSON parse error', 'error');
                    }
                } else if (file.name.endsWith('.csv')) {
                    parseCSV(content);
                }
            };
            reader.readAsText(file);
        }
        
        function parseCSV(csv) {
            const lines = csv.split('\\n').filter(function(l) { return l.trim(); });
            if (lines.length < 2) {
                showResult('Empty CSV', 'error');
                return;
            }
            const headers = lines[0].split(',').map(function(h) { return h.trim().replace(/"/g, ''); });
            const data = [];
            for (let i = 1; i < lines.length; i++) {
                const values = lines[i].split(',').map(function(v) { return v.trim().replace(/"/g, ''); });
                const row = {};
                headers.forEach(function(h, idx) {
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
                showResult('No documents', 'error');
                return;
            }
            let html = '<h3>Documents</h3><table><tr><th>Name</th><th>ID</th><th>Modified</th><th>Action</th></tr>';
            data.items.forEach(function(doc) {
                html += '<tr><td>' + (doc.name || 'Unnamed') + '</td>';
                html += '<td>' + doc.id + '</td>';
                html += '<td>' + new Date(doc.modifiedAt).toLocaleString() + '</td>';
                html += '<td><button onclick="document.getElementById(\\'documentId\\').value=\\''+doc.id+'\\'">Use</button></td></tr>';
            });
            html += '</table>';
            document.getElementById('results').innerHTML = html;
        }
        
        function displayElements(data) {
            if (!data || !data.length) {
                showResult('No elements', 'error');
                return;
            }
            let html = '<h3>Elements</h3><table><tr><th>Name</th><th>Type</th><th>ID</th><th>Action</th></tr>';
            data.forEach(function(elem) {
                html += '<tr><td>' + (elem.name || 'Unnamed') + '</td>';
                html += '<td>' + elem.elementType + '</td>';
                html += '<td>' + elem.id + '</td>';
                html += '<td><button onclick="document.getElementById(\\'elementId\\').value=\\''+elem.id+'\\'">Use</button></td></tr>';
            });
            html += '</table>';
            document.getElementById('results').innerHTML = html;
        }
        
        function displayBOM(data) {
            if (!data.bomTable || !data.bomTable.items) {
                showResult('No BOM data', 'error');
                return;
            }
            let html = '<h3>BOM (Editable)</h3><table>';
            html += '<tr><th>Item</th><th>Part Number</th><th>Name</th><th>Quantity</th><th>Description</th></tr>';
            data.bomTable.items.forEach(function(item, idx) {
                html += '<tr>';
                html += '<td class="editable-cell" contenteditable="true" data-row="'+idx+'" data-field="item">' + (item.item || item.Item || '-') + '</td>';
                html += '<td class="editable-cell" contenteditable="true" data-row="'+idx+'" data-field="partNumber">' + (item.partNumber || item['Part Number'] || '-') + '</td>';
                html += '<td class="editable-cell" contenteditable="true" data-row="'+idx+'" data-field="name">' + (item.name || item.Name || '-') + '</td>';
                html += '<td class="editable-cell" contenteditable="true" data-row="'+idx+'" data-field="quantity">' + (item.quantity || item.Quantity || '-') + '</td>';
                html += '<td class="editable-cell" contenteditable="true" data-row="'+idx+'" data-field="description">' + (item.description || item.Description || '-') + '</td>';
                html += '</tr>';
            });
            html += '</table><p>💡 Click cells to edit</p>';
            document.getElementById('results').innerHTML = html;
            attachEditListeners();
        }
        
        function displayBoundingBoxes(data) {
            if (!data || !data.length) {
                showResult('No bbox data', 'error');
                return;
            }
            let html = '<h3>Bounding Boxes (mm)</h3><table>';
            html += '<tr><th>Part ID</th><th>X (mm)</th><th>Y (mm)</th><th>Z (mm)</th><th>Volume</th></tr>';
            data.forEach(function(box, idx) {
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
                html += '<tr>';
                html += '<td class="editable-cell" contenteditable="true" data-row="'+idx+'" data-field="partId">'+pid+'</td>';
                html += '<td class="editable-cell" contenteditable="true" data-row="'+idx+'" data-field="lengthX">'+x+'</td>';
                html += '<td class="editable-cell" contenteditable="true" data-row="'+idx+'" data-field="lengthY">'+y+'</td>';
                html += '<td class="editable-cell" contenteditable="true" data-row="'+idx+'" data-field="lengthZ">'+z+'</td>';
                html += '<td>'+vol+'</td></tr>';
            });
            html += '</table><p>💡 Click cells to edit</p>';
            document.getElementById('results').innerHTML = html;
            attachEditListeners();
        }
        
        function displayGenericTable(data) {
            const headers = Object.keys(data[0]);
            let html = '<h3>Data Table</h3><table><tr>';
            headers.forEach(function(h) { html += '<th>'+h+'</th>'; });
            html += '</tr>';
            data.forEach(function(row, idx) {
                html += '<tr>';
                headers.forEach(function(h) {
                    html += '<td class="editable-cell" contenteditable="true" data-row="'+idx+'" data-field="'+h+'">'+(row[h]||'')+'</td>';
                });
                html += '</tr>';
            });
            html += '</table>';
            document.getElementById('results').innerHTML = html;
            attachEditListeners();
        }
        
        function attachEditListeners() {
            document.querySelectorAll('.editable-cell').forEach(function(cell) {
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
            }
        }
        
        function downloadAsJSON() {
            if (!currentData) {
                alert('No data');
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
                alert('No data');
                return;
            }
            let csv = '';
            if (currentData.bomTable && currentData.bomTable.items) {
                csv = 'Item,Part Number,Name,Quantity,Description\\n';
                currentData.bomTable.items.forEach(function(item) {
                    csv += '"'+(
