// API.JS - All API calls for refactored backend

async function loadUserInfo() {
    try {
        const r = await fetch(`/api/user/info?user_id=${userId}`);
        const d = await r.json();
        document.getElementById('userEmail').textContent = d.email || 'User';
    } catch (e) {
        console.error('Failed to load user info:', e);
    }
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
        const r = await fetch('/api/documents/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: userId,
                document_id: did,
                workspace_id: wid,
                element_id: eid,
                document_name: `Doc ${did.substring(0, 8)}`,
                element_name: `Element ${eid.substring(0, 8)}`
            })
        });
        
        const result = await r.json();
        if (result.status === 'success') {
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
        const r = await fetch(`/api/documents/saved?user_id=${userId}`);
        const result = await r.json();
        
        if (!result.documents || result.documents.length === 0) {
            showResult('No saved documents found', 'info');
            return;
        }
        
        let h = '<h3>Your Saved Documents</h3><table><tr><th>Name</th><th>Document ID</th><th>Last Used</th><th>Action</th></tr>';
        result.documents.forEach(d => {
            h += '<tr><td>' + (d.document_name || 'Unnamed') + '</td>';
            h += '<td>' + d.document_id.substring(0, 12) + '...</td>';
            h += '<td>' + new Date(d.last_used_at).toLocaleString() + '</td>';
            h += '<td><button onclick="loadDoc(\'' + d.document_id + '\',\'' + d.workspace_id + '\',\'' + d.element_id + '\')">Load</button></td></tr>';
        });
        h += '</table>';
        document.getElementById('results').innerHTML = h;
    } catch (e) {
        showResult('Error loading documents: ' + e.message, 'error');
    }
}

async function getDocuments() {
    if (!userId) {
        showResult('Please login first', 'error');
        return;
    }
    
    showResult('Loading documents...', 'info');
    try {
        const r = await fetch(`/api/documents/list?user_id=${userId}`);
        const result = await r.json();
        
        if (result.status !== 'success') {
            showResult('Failed to load documents', 'error');
            return;
        }
        
        currentData = result;
        displayDocuments(result.documents);
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
        const r = await fetch(`/api/documents/${did}/elements?workspace_id=${wid}&user_id=${userId}`);
        const result = await r.json();
        
        if (result.status !== 'success') {
            showResult('Failed to load elements', 'error');
            return;
        }
        
        currentData = result;
        displayElements(result.elements);
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
        const url = `/api/bom/fetch?doc_id=${did}&workspace_id=${wid}&element_id=${eid}&user_id=${userId}&indented=${bomIndented}`;
        const r = await fetch(url);
        const result = await r.json();
        
        if (result.status !== 'success') {
            showResult('Failed to load BOM', 'error');
            return;
        }
        
        currentData = result.data;
        displayBOM(result.data);
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
        const url = `/api/properties/bounding-boxes?doc_id=${did}&workspace_id=${wid}&element_id=${eid}&user_id=${userId}`;
        const r = await fetch(url);
        const result = await r.json();
        
        if (result.status !== 'success') {
            showResult('Failed to load bounding boxes', 'error');
            return;
        }
        
        currentData = result.data;
        displayBoundingBoxes(result.data);
    } catch (e) {
        showResult('Error: ' + e.message, 'error');
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
    
    showResult('Creating length properties from bounding boxes...', 'info');
    
    try {
        const r = await fetch('/api/properties/create-length-properties', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: userId,
                doc_id: did,
                workspace_id: wid,
                element_id: eid
            })
        });
        
        const result = await r.json();
        
        let msg = result.message || 'Properties created';
        if (result.errors && result.errors.length > 0) {
            msg += '<br><br><strong>Errors:</strong><br>' + result.errors.slice(0, 5).join('<br>');
        }
        
        showResult(msg, result.status === 'success' ? 'success' : 'error');
    } catch (e) {
        showResult('Error: ' + e.message, 'error');
    }
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
        const r = await fetch(`/api/bom/fetch`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: userId,
                bomData: currentData
            })
        });
        
        const result = await r.json();
        if (result.status === 'success') {
            showResult('✅ BOM successfully pushed to OnShape!', 'success');
        } else {
            showResult('Failed to push BOM: ' + (result.message || 'Unknown error'), 'error');
        }
    } catch (e) {
        showResult('Error pushing BOM: ' + e.message, 'error');
    }
}