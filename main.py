import os
import base64
import json
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
import requests

app = FastAPI()

# Load config from environment variables
CLIENT_ID = os.getenv("ONSHAPE_CLIENT_ID")
CLIENT_SECRET = os.getenv("ONSHAPE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")

AUTH_URL = "https://oauth.onshape.com/oauth/authorize"
TOKEN_URL = "https://oauth.onshape.com/oauth/token"
SCOPE = "OAuth2Read OAuth2Write"

# Single HTML file content with BOM and Bounding Box features
HTML_CONTENT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OnShape BOM & Bounding Box Manager</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
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
        
        h1 {
            color: #333;
            margin-bottom: 20px;
            text-align: center;
        }
        
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
        
        .input-group {
            margin: 15px 0;
        }
        
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
        
        tr:hover {
            background: #f5f5f5;
        }
        
        .editable-cell {
            background: #fff9e6;
            cursor: text;
        }
        
        .editable-cell:hover {
            background: #fff3cd;
        }
        
        input.cell-input {
            width: 100%;
            padding: 4px;
            border: 1px solid #667eea;
            font-size: 14px;
        }
        
        .download-btn {
            background: #28a745;
        }
        
        .download-btn:hover {
            background: #218838;
        }
        
        .grid-2 {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
        }
        
        @media (max-width: 768px) {
            .grid-2 {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔧 OnShape BOM & Bounding Box Manager</h1>
        
        <div class="section">
            <h2>Authentication</h2>
            <div class="button-group">
                <button onclick="loginWithOnShape()">🔐 Login with OnShape</button>
            </div>
            
            <div class="input-group">
                <label for="accessToken">Access Token:</label>
                <input type="text" id="accessToken" placeholder="Paste your access token here or login to get one">
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
                <label for="elementId">Element ID (for BOM/Bounding Box):</label>
                <input type="text" id="elementId" placeholder="e.g., 9z8y7x6w5v4u3t2s1r0q">
            </div>
            
            <div class="button-group">
                <button onclick="getDocuments()">📁 List My Documents</button>
                <button onclick="getElements()">📄 Get Document Elements</button>
                <button onclick="getBOM()">📊 Get BOM</button>
                <button onclick="getBoundingBoxes()">📏 Get Bounding Boxes</button>
            </div>
        </div>
        
        <div class="section">
            <h2>Upload & Edit BOM</h2>
            <div class="input-group">
                <label for="fileUpload">Upload CSV or JSON File:</label>
                <input type="file" id="fileUpload" accept=".csv,.json" onchange="handleFileUpload(event)">
            </div>
            <div class="button-group">
                <button onclick="saveEditedData()">💾 Save Edited Data</button>
                <button onclick="clearData()">🗑️ Clear All</button>
            </div>
        </div>
        
        <div class="section">
            <h2>Results</h2>
            <div class="button-group">
                <button class="download-btn" onclick="downloadAsJSON()">⬇️ Download as JSON</button>
                <button class="download-btn" onclick="downloadAsCSV()">⬇️ Download as CSV</button>
            </div>
            <div id="results">No data yet. Login and fetch some data or upload a file!</div>
        </div>
    </div>

    <script>
        let currentData = null;
        let editMode = false;
        
        // File upload handler
        function handleFileUpload(event) {
            console.log('File upload triggered');
            const file = event.target.files[0];
            if (!file) {
                console.log('No file selected');
                return;
            }
            
            console.log('File selected:', file.name);
            showResult('Loading file...', 'info');
            
            const reader = new FileReader();
            reader.onload = function(e) {
                console.log('File loaded');
                const content = e.target.result;
                
                if (file.name.endsWith('.json')) {
                    try {
                        currentData = JSON.parse(content);
                        console.log('JSON parsed:', currentData);
                        displayUploadedData(currentData);
                    } catch (error) {
                        console.error('JSON parse error:', error);
                        showResult(`Error parsing JSON: ${error.message}`, 'error');
                    }
                } else if (file.name.endsWith('.csv')) {
                    console.log('Parsing CSV');
                    parseCSV(content);
                }
            };
            
            reader.onerror = function(error) {
                console.error('File read error:', error);
                showResult('Error reading file', 'error');
            };
            
            reader.readAsText(file);
        }
        
        function parseCSV(csv) {
            console.log('Parsing CSV content');
            const lines = csv.split('\n').filter(line => line.trim());
            console.log('CSV lines:', lines.length);
            
            if (lines.length < 2) {
                showResult('CSV file is empty or invalid', 'error');
                return;
            }
            
            const headers = lines[0].split(',').map(h => h.trim().replace(/"/g, ''));
            console.log('CSV headers:', headers);
            const data = [];
            
            for (let i = 1; i < lines.length; i++) {
                const values = lines[i].split(',').map(v => v.trim().replace(/"/g, ''));
                const row = {};
                headers.forEach((header, index) => {
                    row[header] = values[index] || '';
                });
                data.push(row);
            }
            
            console.log('Parsed CSV data:', data);
            
            // Detect data type based on headers
            if (headers.includes('Part Number') || headers.includes('partNumber')) {
                currentData = { bomTable: { items: data } };
            } else if (headers.includes('Length X (mm)') || headers.includes('lowX')) {
                currentData = data;
            } else {
                currentData = data;
            }
            
            displayUploadedData(currentData);
        }
        
        function displayUploadedData(data) {
            console.log('Displaying uploaded data:', data);
            // Try to detect data type and display appropriately
            if (data.bomTable && data.bomTable.items) {
                console.log('Detected BOM data');
                displayBOM(data);
            } else if (Array.isArray(data) && data[0]) {
                console.log('Detected array data');
                if (data[0].lowX !== undefined || data[0]['Length X (mm)'] !== undefined) {
                    console.log('Detected bounding box data');
                    displayBoundingBoxes(data);
                } else if (data[0].partNumber !== undefined || data[0]['Part Number'] !== undefined) {
                    console.log('Detected BOM array format');
                    currentData = { bomTable: { items: data } };
                    displayBOM(currentData);
                } else {
                    console.log('Displaying generic table');
                    displayGenericTable(data);
                }
            } else {
                console.log('Unknown data format');
                showResult('Uploaded data format not recognized. Showing raw data:', 'error');
                document.getElementById('results').innerHTML += '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
            }
        }
        
        function displayGenericTable(data) {
            console.log('Displaying generic table');
            if (!data || data.length === 0) {
                showResult('No data to display', 'error');
                return;
            }
            
            const headers = Object.keys(data[0]);
            let html = '<h3>Data Table (Editable)</h3><table>';
            html += '<tr>';
            headers.forEach(h => html += '<th>' + h + '</th>');
            html += '</tr>';
            
            data.forEach((row, rowIndex) => {
                html += '<tr>';
                headers.forEach(header => {
                    const value = row[header] || '';
                    html += '<td class="editable-cell" contenteditable="true" data-row="' + rowIndex + '" data-field="' + header + '">' + value + '</td>';
                });
                html += '</tr>';
            });
            html += '</table>';
            html += '<p style="color: #666; margin-top: 10px;">💡 Click on any cell to edit. Changes are saved automatically.</p>';
            
            document.getElementById('results').innerHTML = html;
            attachEditListeners();
        }
        
        function loginWithOnShape() {
            window.location.href = '/login';
        }
        
        async function getDocuments() {
            console.log('Getting documents');
            const accessToken = document.getElementById('accessToken').value;
            if (!accessToken) {
                showResult('Please enter an access token or login first', 'error');
                return;
            }
            
            showResult('Loading documents...', 'info');
            try {
                const response = await fetch('/api/documents', {
                    headers: {
                        'Authorization': `Bearer ${accessToken}`
                    }
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                
                const data = await response.json();
                console.log('Documents received:', data);
                currentData = data;
                displayDocuments(data);
            } catch (error) {
                console.error('Error fetching documents:', error);
                showResult(`Error: ${error.message}`, 'error');
            }
        }
        
        async function getElements() {
            console.log('Getting elements');
            const accessToken = document.getElementById('accessToken').value;
            const documentId = document.getElementById('documentId').value;
            const workspaceId = document.getElementById('workspaceId').value;
            
            if (!accessToken || !documentId || !workspaceId) {
                showResult('Please provide access token, document ID, and workspace ID', 'error');
                return;
            }
            
            showResult('Loading elements...', 'info');
            try {
                const response = await fetch('/api/documents/' + documentId + '/w/' + workspaceId + '/elements', {
                    headers: {
                        'Authorization': 'Bearer ' + accessToken
                    }
                });
                
                if (!response.ok) {
                    throw new Error('HTTP error! status: ' + response.status);
                }
                
                const data = await response.json();
                console.log('Elements received:', data);
                currentData = data;
                displayElements(data);
            } catch (error) {
                console.error('Error fetching elements:', error);
                showResult('Error: ' + error.message, 'error');
            }
        }
        
        async function getBOM() {
            console.log('Getting BOM');
            const accessToken = document.getElementById('accessToken').value;
            const documentId = document.getElementById('documentId').value;
            const workspaceId = document.getElementById('workspaceId').value;
            const elementId = document.getElementById('elementId').value;
            
            if (!accessToken || !documentId || !workspaceId || !elementId) {
                showResult('Please provide all required IDs', 'error');
                return;
            }
            
            showResult('Loading BOM...', 'info');
            try {
                const response = await fetch('/api/assemblies/' + documentId + '/w/' + workspaceId + '/e/' + elementId + '/bom', {
                    headers: {
                        'Authorization': 'Bearer ' + accessToken
                    }
                });
                
                if (!response.ok) {
                    throw new Error('HTTP error! status: ' + response.status);
                }
                
                const data = await response.json();
                console.log('BOM received:', data);
                currentData = data;
                displayBOM(data);
            } catch (error) {
                console.error('Error fetching BOM:', error);
                showResult('Error: ' + error.message, 'error');
            }
        }
        
        async function getBoundingBoxes() {
            console.log('Getting bounding boxes');
            const accessToken = document.getElementById('accessToken').value;
            const documentId = document.getElementById('documentId').value;
            const workspaceId = document.getElementById('workspaceId').value;
            const elementId = document.getElementById('elementId').value;
            
            if (!accessToken || !documentId || !workspaceId || !elementId) {
                showResult('Please provide all required IDs', 'error');
                return;
            }
            
            showResult('Loading bounding boxes...', 'info');
            try {
                const response = await fetch('/api/partstudios/' + documentId + '/w/' + workspaceId + '/e/' + elementId + '/boundingboxes', {
                    headers: {
                        'Authorization': 'Bearer ' + accessToken
                    }
                });
                
                if (!response.ok) {
                    throw new Error('HTTP error! status: ' + response.status);
                }
                
                const data = await response.json();
                console.log('Bounding boxes received:', data);
                currentData = data;
                displayBoundingBoxes(data);
            } catch (error) {
                console.error('Error fetching bounding boxes:', error);
                showResult('Error: ' + error.message, 'error');
            }
        }
        
        function displayDocuments(data) {
            if (!data.items || data.items.length === 0) {
                showResult('No documents found', 'error');
                return;
            }
            
            let html = '<h3>Your Documents</h3><table><tr><th>Name</th><th>ID</th><th>Modified</th><th>Action</th></tr>';
            data.items.forEach(doc => {
                html += '<tr><td>' + (doc.name || 'Unnamed') + '</td><td>' + doc.id + '</td><td>' + new Date(doc.modifiedAt).toLocaleString() + '</td><td><button onclick="document.getElementById(\'documentId\').value=\'' + doc.id + '\'">Use This</button></td></tr>';
            });
            html += '</table>';
            document.getElementById('results').innerHTML = html;
        }
        
        function displayElements(data) {
            if (!data || data.length === 0) {
                showResult('No elements found', 'error');
                return;
            }
            
            let html = '<h3>Document Elements</h3><table><tr><th>Name</th><th>Type</th><th>ID</th><th>Action</th></tr>';
            data.forEach(elem => {
                html += '<tr><td>' + (elem.name || 'Unnamed') + '</td><td>' + elem.elementType + '</td><td>' + elem.id + '</td><td><button onclick="document.getElementById(\'elementId\').value=\'' + elem.id + '\'">Use This</button></td></tr>';
            });
            html += '</table>';
            document.getElementById('results').innerHTML = html;
        }
        
        function displayBOM(data) {
            if (!data.bomTable || !data.bomTable.items) {
                showResult('No BOM data found', 'error');
                return;
            }
            
            let html = '<h3>Bill of Materials (Editable)</h3><table>';
            html += '<tr><th>Item</th><th>Part Number</th><th>Name</th><th>Quantity</th><th>Description</th></tr>';
            
            data.bomTable.items.forEach((item, index) => {
                html += '<tr>';
                html += '<td class="editable-cell" contenteditable="true" data-row="' + index + '" data-field="item">' + (item.item || item.Item || '-') + '</td>';
                html += '<td class="editable-cell" contenteditable="true" data-row="' + index + '" data-field="partNumber">' + (item.partNumber || item['Part Number'] || '-') + '</td>';
                html += '<td class="editable-cell" contenteditable="true" data-row="' + index + '" data-field="name">' + (item.name || item.Name || '-') + '</td>';
                html += '<td class="editable-cell" contenteditable="true" data-row="' + index + '" data-field="quantity">' + (item.quantity || item.Quantity || '-') + '</td>';
                html += '<td class="editable-cell" contenteditable="true" data-row="' + index + '" data-field="description">' + (item.description || item.Description || '-') + '</td>';
                html += '</tr>';
            });
            html += '</table>';
            html += '<p style="color: #666; margin-top: 10px;">💡 Click on any cell to edit. Changes are saved automatically.</p>';
            document.getElementById('results').innerHTML = html;
            attachEditListeners();
        }
        
        function displayBoundingBoxes(data) {
            if (!data || data.length === 0) {
                showResult('No bounding box data found', 'error');
                return;
            }
            
            let html = '<h3>Bounding Boxes - Millimeters (Editable)</h3><table>';
            html += '<tr><th>Part ID</th><th>Length X (mm)</th><th>Length Y (mm)</th><th>Length Z (mm)</th><th>Volume (mm³)</th></tr>';
            
            data.forEach((box, index) => {
                let lengthX, lengthY, lengthZ, volume, partId;
                
                if (box['Length X (mm)']) {
                    lengthX = box['Length X (mm)'];
                    lengthY = box['Length Y (mm)'];
                    lengthZ = box['Length Z (mm)'];
                    volume = box['Volume (mm³)'];
                    partId = box['Part ID'] || 'Unknown';
                } else {
                    lengthX = ((box.highX - box.lowX) * 1000).toFixed(2);
                    lengthY = ((box.highY - box.lowY) * 1000).toFixed(2);
                    lengthZ = ((box.highZ - box.lowZ) * 1000).toFixed(2);
                    volume = (lengthX * lengthY * lengthZ).toFixed(2);
                    partId = box.partId || 'Unknown';
                }
                
                html += '<tr>';
                html += '<td class="editable-cell" contenteditable="true" data-row="' + index + '" data-field="partId">' + partId + '</td>';
                html += '<td class="editable-cell" contenteditable="true" data-row="' + index + '" data-field="lengthX">' + lengthX + '</td>';
                html += '<td class="editable-cell" contenteditable="true" data-row="' + index + '" data-field="lengthY">' + lengthY + '</td>';
                html += '<td class="editable-cell" contenteditable="true" data-row="' + index + '" data-field="lengthZ">' + lengthZ + '</td>';
                html += '<td>' + volume + '</td>';
                html += '</tr>';
            });
            html += '</table>';
            html += '<p style="color: #666; margin-top: 10px;">💡 Click on any cell to edit. Volume is auto-calculated.</p>';
            document.getElementById('results').innerHTML = html;
            attachEditListeners();
        }
        
        function downloadAsJSON() {
            if (!currentData) {
                alert('No data to download. Please fetch some data first.');
                return;
            }
            
            const dataStr = JSON.stringify(currentData, null, 2);
            const blob = new Blob([dataStr], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `onshape-data-${Date.now()}.json`;
            a.click();
            URL.revokeObjectURL(url);
        }
        
        function attachEditListeners() {
            document.querySelectorAll('.editable-cell').forEach(cell => {
                cell.addEventListener('blur', function() {
                    const row = parseInt(this.dataset.row);
                    const field = this.dataset.field;
                    const newValue = this.textContent.trim();
                    
                    // Update the data
                    if (currentData.bomTable && currentData.bomTable.items) {
                        currentData.bomTable.items[row][field] = newValue;
                    } else if (Array.isArray(currentData)) {
                        currentData[row][field] = newValue;
                    }
                });
                
                cell.addEventListener('keydown', function(e) {
                    if (e.key === 'Enter') {
                        e.preventDefault();
                        this.blur();
                    }
                });
            });
        }
        
        function saveEditedData() {
            if (!currentData) {
                alert('No data to save. Please load some data first.');
                return;
            }
            
            // Show success message
            const tempDiv = document.createElement('div');
            tempDiv.className = 'success';
            tempDiv.textContent = '✅ Data saved! Use the download buttons to save to your computer.';
            tempDiv.style.position = 'fixed';
            tempDiv.style.top = '20px';
            tempDiv.style.right = '20px';
            tempDiv.style.padding = '15px';
            tempDiv.style.borderRadius = '8px';
            tempDiv.style.zIndex = '1000';
            tempDiv.style.boxShadow = '0 4px 12px rgba(0,0,0,0.2)';
            document.body.appendChild(tempDiv);
            
            setTimeout(() => {
                tempDiv.remove();
            }, 3000);
        }
        
        function clearData() {
            if (confirm('Are you sure you want to clear all data?')) {
                currentData = null;
                document.getElementById('results').innerHTML = 'No data. Upload a file or fetch from OnShape!';
                document.getElementById('fileUpload').value = '';
            }
        }
        
        function downloadAsCSV() {
            if (!currentData) {
                alert('No data to download. Please fetch some data first.');
                return;
            }
            
            let csv = '';
            
            // Handle BOM data
            if (currentData.bomTable && currentData.bomTable.items) {
                csv = 'Item,Part Number,Name,Quantity,Description' + String.fromCharCode(10);
                currentData.bomTable.items.forEach(item => {
                    csv += '"' + (item.item || '') + '","' + (item.partNumber || '') + '","' + (item.name || '') + '","' + (item.quantity || '') + '","' + (item.description || '') + '"' + String.fromCharCode(10);
                });
            }
            // Handle bounding box data
            else if (Array.isArray(currentData) && currentData.length > 0) {
                if (currentData[0].lowX !== undefined || currentData[0].lengthX !== undefined) {
                    csv = 'Part ID,Length X (mm),Length Y (mm),Length Z (mm),Volume (mm³)' + String.fromCharCode(10);
                    currentData.forEach(box => {
                        let lengthX, lengthY, lengthZ, volume, partId;
                        
                        if (box.lengthX) {
                            lengthX = box.lengthX;
                            lengthY = box.lengthY;
                            lengthZ = box.lengthZ;
                            volume = (lengthX * lengthY * lengthZ).toFixed(2);
                            partId = box.partId || 'Unknown';
                        } else {
                            lengthX = ((box.highX - box.lowX) * 1000).toFixed(2);
                            lengthY = ((box.highY - box.lowY) * 1000).toFixed(2);
                            lengthZ = ((box.highZ - box.lowZ) * 1000).toFixed(2);
                            volume = (lengthX * lengthY * lengthZ).toFixed(2);
                            partId = box.partId || 'Unknown';
                        }
                        
                        csv += '"' + partId + '","' + lengthX + '","' + lengthY + '","' + lengthZ + '","' + volume + '"' + String.fromCharCode(10);
                    });
                } else {
                    // Generic data export
                    const headers = Object.keys(currentData[0]);
                    csv = headers.join(',') + String.fromCharCode(10);
                    currentData.forEach(row => {
                        csv += headers.map(h => '"' + (row[h] || '') + '"').join(',') + String.fromCharCode(10);
                    });
                }
            }
            else {
                alert('Current data format not supported for CSV export');
                return;
            }
            
            const blob = new Blob([csv], { type: 'text/csv' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'onshape-data-' + Date.now() + '.csv';
            a.click();
            URL.revokeObjectURL(url);
        }
        
        function showResult(message, type = 'info') {
            const resultsDiv = document.getElementById('results');
            let className = '';
            
            if (type === 'error') className = 'error';
            if (type === 'success') className = 'success';
            
            resultsDiv.innerHTML = '<div class="' + className + '">' + message + '</div>';
        }
    </script>
</body>
</html>
"""

if not CLIENT_ID or not CLIENT_SECRET or not REDIRECT_URI:
    @app.get("/", response_class=HTMLResponse)
    def missing_config():
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Configuration Error</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    padding: 50px;
                    background: #f8d7da;
                    text-align: center;
                }
                .error-box {
                    background: white;
                    padding: 30px;
                    border-radius: 8px;
                    max-width: 600px;
                    margin: 0 auto;
                }
            </style>
        </head>
        <body>
            <div class="error-box">
                <h1>❌ Configuration Error</h1>
                <p>Missing required environment variables:</p>
                <ul style="text-align: left;">
                    <li>ONSHAPE_CLIENT_ID</li>
                    <li>ONSHAPE_CLIENT_SECRET</li>
                    <li>REDIRECT_URI</li>
                </ul>
                <p>Please configure these in your Render.com dashboard.</p>
            </div>
        </body>
        </html>
        """
else:
    @app.get("/", response_class=HTMLResponse)
    def root():
        return HTML_CONTENT

    @app.get("/api/status")
    def api_status():
        return {
            "message": "Onshape OAuth API running",
            "status": "ok",
            "redirect_uri_configured": REDIRECT_URI
        }

    @app.get("/login")
    def login():
        params = {
            "response_type": "code",
            "client_id": CLIENT_ID,
            "redirect_uri": REDIRECT_URI,
            "scope": SCOPE,
            "state": "aleks_state_123"
        }
        from urllib.parse import urlencode
        url = AUTH_URL + "?" + urlencode(params)
        return RedirectResponse(url)

    @app.get("/callback", response_class=HTMLResponse)
    async def callback(request: Request):
        all_params = dict(request.query_params)
        code = request.query_params.get("code")
        error = request.query_params.get("error")
        
        if error:
            return f"""<html><body style="font-family: Arial; padding: 50px;">
                <h1>❌ OAuth Error</h1>
                <p><strong>Error:</strong> {error}</p>
                <button onclick="window.location.href='/'" style="padding: 12px 24px; background: #667eea; color: white; border: none; border-radius: 6px; cursor: pointer; margin-top: 20px;">Back to Home</button>
            </body></html>"""
        
        if not code:
            return f"""<html><body style="font-family: Arial; padding: 50px;">
                <h1>❌ Missing Authorization Code</h1>
                <p>Parameters received: {json.dumps(all_params, indent=2)}</p>
                <button onclick="window.location.href='/'" style="padding: 12px 24px; background: #667eea; color: white; border: none; border-radius: 6px; cursor: pointer; margin-top: 20px;">Back to Home</button>
            </body></html>"""

        auth_header = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
        headers = {
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI
        }
        
        try:
            resp = requests.post(TOKEN_URL, headers=headers, data=data, timeout=10)
            if resp.status_code != 200:
                return f"""<html><body style="font-family: Arial; padding: 50px;">
                    <h1>❌ Token Exchange Failed</h1>
                    <pre>{resp.text}</pre>
                    <button onclick="window.location.href='/'" style="padding: 12px 24px; background: #667eea; color: white; border: none; border-radius: 6px; cursor: pointer; margin-top: 20px;">Try Again</button>
                </body></html>"""

            token_data = resp.json()
            return f"""<html><body style="font-family: Arial; padding: 50px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
                <div style="background: white; padding: 40px; border-radius: 12px; max-width: 800px; margin: 0 auto;">
                    <h1 style="color: #28a745;">✅ Login Successful!</h1>
                    <p>Copy your access token:</p>
                    <pre style="background: #2d2d2d; color: #f8f8f2; padding: 15px; border-radius: 4px; overflow-x: auto;">{json.dumps(token_data, indent=2)}</pre>
                    <button onclick="window.location.href='/'" style="padding: 12px 24px; background: #667eea; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 16px; margin-top: 20px;">Back to Home</button>
                </div>
            </body></html>"""
        except Exception as e:
            return f"""<html><body style="font-family: Arial; padding: 50px;">
                <h1>❌ Error: {str(e)}</h1>
                <button onclick="window.location.href='/'" style="padding: 12px 24px; background: #667eea; color: white; border: none; border-radius: 6px; cursor: pointer; margin-top: 20px;">Back to Home</button>
            </body></html>"""

    # API Proxy endpoints to OnShape
    @app.get("/api/documents")
    async def get_documents(request: Request):
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            raise HTTPException(status_code=401, detail="Authorization header required")
        
        headers = {"Authorization": auth_header}
        resp = requests.get("https://cad.onshape.com/api/documents", headers=headers)
        return JSONResponse(content=resp.json(), status_code=resp.status_code)

    @app.get("/api/documents/{did}/w/{wid}/elements")
    async def get_elements(did: str, wid: str, request: Request):
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            raise HTTPException(status_code=401, detail="Authorization header required")
        
        headers = {"Authorization": auth_header}
        url = f"https://cad.onshape.com/api/documents/d/{did}/w/{wid}/elements"
        resp = requests.get(url, headers=headers)
        return JSONResponse(content=resp.json(), status_code=resp.status_code)

    @app.get("/api/assemblies/{did}/w/{wid}/e/{eid}/bom")
    async def get_bom(did: str, wid: str, eid: str, request: Request):
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            raise HTTPException(status_code=401, detail="Authorization header required")
        
        headers = {"Authorization": auth_header}
        url = f"https://cad.onshape.com/api/assemblies/d/{did}/w/{wid}/e/{eid}/bom"
        resp = requests.get(url, headers=headers)
        return JSONResponse(content=resp.json(), status_code=resp.status_code)

    @app.get("/api/partstudios/{did}/w/{wid}/e/{eid}/boundingboxes")
    async def get_bounding_boxes(did: str, wid: str, eid: str, request: Request):
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            raise HTTPException(status_code=401, detail="Authorization header required")
        
        headers = {"Authorization": auth_header}
        url = f"https://cad.onshape.com/api/partstudios/d/{did}/w/{wid}/e/{eid}/boundingboxes"
        resp = requests.get(url, headers=headers)
        return JSONResponse(content=resp.json(), status_code=resp.status_code)

    @app.get("/me")
    def me(access_token: str = None):
        if not access_token:
            return {"error": "Provide access_token as query param"}

        profile_url = "https://cad.onshape.com/api/users/session"
        headers = {"Authorization": f"Bearer {access_token}"}
        r = requests.get(profile_url, headers=headers)
        if r.status_code != 200:
            return {"status": "api call failed", "code": r.status_code, "body": r.text}
        return r.json()

    @app.get("/refresh")
    def refresh(refresh_token: str):
        if not refresh_token:
            raise HTTPException(status_code=400, detail="refresh_token required")
        auth_header = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
        headers = {
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        }
        resp = requests.post(TOKEN_URL, headers=headers, data=data)
        if resp.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Refresh failed: {resp.text}")
        return resp.json()
