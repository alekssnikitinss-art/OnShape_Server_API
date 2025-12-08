// APP.JS - Main application initialization and event handlers

// Global variables
let currentData = null;
let userId = localStorage.getItem('userId');
let bomIndented = false;  // false = flat, true = structured
let currentDocId = '';
let currentWorkId = '';
let currentElemId = '';

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    // Load user info if logged in
    if (userId) {
        document.getElementById('userInfo').style.display = 'flex';
        loadUserInfo();
    }
    
    // Bind button click events
    bindButtonEvents();
    
    // Set BOM format buttons
    updateBOMFormatButtons();
    
    // Setup parts scanner listeners
    setupPartsScannerListeners();
}

function bindButtonEvents() {
    // Auth
    document.getElementById('loginBtn').onclick = () => window.location.href = '/auth/login';
    
    // Documents
    document.getElementById('getDocsBtn').onclick = getDocuments;
    document.getElementById('getElemsBtn').onclick = getElements;
    document.getElementById('loadSavedBtn').onclick = loadSavedDocuments;
    document.getElementById('saveDocBtn').onclick = saveDocument;
    
    // BOM & Properties
    document.getElementById('getBomBtn').onclick = getBOM;
    document.getElementById('getBboxBtn').onclick = getBoundingBoxes;
    document.getElementById('getVarsBtn').onclick = getConfigurationVariables;
    document.getElementById('createLengthPropsBtn').onclick = createLengthProperties;
    document.getElementById('pushBomBtn').onclick = pushBOMToOnShape;
    
    // File & Export
    document.getElementById('fileUpload').onchange = handleFileUpload;
    document.getElementById('clearBtn').onclick = clearData;
    document.getElementById('downloadJsonBtn').onclick = downloadAsJSON;
    document.getElementById('downloadCsvBtn').onclick = downloadAsCSV;
}

function setBomFormat(indented) {
    bomIndented = indented;
    updateBOMFormatButtons();
}

function updateBOMFormatButtons() {
    document.getElementById('flatBtn').classList.toggle('active', !bomIndented);
    document.getElementById('structBtn').classList.toggle('active', bomIndented);
}

function logout() {
    localStorage.removeItem('userId');
    userId = null;
    document.getElementById('userInfo').style.display = 'none';
    showResult('Logged out successfully', 'success');
}

function loadDoc(did, wid, eid) {
    document.getElementById('documentId').value = did;
    document.getElementById('workspaceId').value = wid || '';
    document.getElementById('elementId').value = eid || '';
    showResult('✅ Document loaded! Click Get BOM, Get Bounding Boxes, or Get Variables to fetch data.', 'success');
}

function clearData() {
    if (confirm('Clear all data?')) {
        currentData = null;
        document.getElementById('results').innerHTML = 'No data';
        document.getElementById('fileUpload').value = '';
        document.getElementById('pushBomBtn').style.display = 'none';
    }
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
    const lines = csv.split('\n').filter(l => l.trim());
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
        if (data[0]['Length X (mm)'] || data[0].lowX || data[0].dimensions) {
            displayBoundingBoxes(data);
        } else if (data[0].partNumber || data[0]['Part Number']) {
            currentData = { bomTable: { items: data } };
            displayBOM(currentData);
        } else {
            displayGenericTable(data);
        }
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
        csv = 'Item,Part Number,Name,Quantity,Description\n';
        currentData.bomTable.items.forEach(item => {
            csv += '"'+(item.item||item.Item||'')+'","'+(item.partNumber||item.PART_NUMBER||'')+'","'+(item.name||item.NAME||'')+'","'+(item.quantity||item.QUANTITY||'')+'","'+(item.description||item.DESCRIPTION||'')+'"\\n';
        });
    } else if (Array.isArray(currentData) && currentData.length > 0) {
        const headers = Object.keys(currentData[0]);
        csv = headers.join(',') + '\n';
        currentData.forEach(row => {
            csv += headers.map(h => '"'+(row[h]||'')+'"').join(',') + '\n';
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