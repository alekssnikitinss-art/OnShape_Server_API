// API.JS - All API calls with focus on Variables, Push BOM, and Bounding Boxes
// FIXED VERSION - Removed duplicate functions and syntax errors

const API_TIMEOUT = 40000; // 40 second timeout for OnShape API slowness

async function loadUserInfo() {
    if (!userId) return;
    
    try {
        const r = await fetchWithTimeout(`/api/user/info?user_id=${userId}`, {}, API_TIMEOUT);
        const d = await r.json();
        
        if (d.email) {
            document.getElementById('userEmail').textContent = d.email;
            console.log('✅ User info loaded:', d.email);
        }
    } catch (e) {
        console.error('❌ Failed to load user info:', e);
    }
}

async function saveDocument() {
    if (!userId) {
        showResult('Please login first', 'error');
        return;
    }
    
    const did = document.getElementById('documentId').value.trim();
    const wid = document.getElementById('workspaceId').value.trim();
    const eid = document.getElementById('elementId').value.trim();
    
    if (!did || !wid) {
        showResult('Please fill in Document ID and Workspace ID', 'error');
        return;
    }
    
    try {
        const r = await fetchWithTimeout('/api/documents/save', {
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
        }, API_TIMEOUT);
        
        const result = await r.json();
        
        if (result.status === 'success') {
            showResult('✅ Document saved!', 'success');
        } else {
            showResult(`Error: ${result.message || 'Failed to save'}`, 'error');
        }
    } catch (e) {
        showResult(`Error: ${e.message}`, 'error');
        console.error('Save document error:', e);
    }
}

async function loadSavedDocuments() {
    if (!userId) {
        showResult('Please login first', 'error');
        return;
    }
    
    showResult('Loading saved documents...', 'info');
    
    try {
        const r = await fetchWithTimeout(`/api/documents/saved?user_id=${userId}`, {}, API_TIMEOUT);
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
        showResult(`Error: ${e.message}`, 'error');
        console.error('Load saved documents error:', e);
    }
}

async function getDocuments() {
    if (!userId) {
        showResult('Please login first', 'error');
        return;
    }
    
    showResult('📁 Loading documents...', 'info');
    
    try {
        const r = await fetchWithTimeout(`/api/documents/list?user_id=${userId}`, {}, API_TIMEOUT);
        const result = await r.json();
        
        if (result.status !== 'success') {
            showResult(`Error: ${result.error || 'Failed to load documents'}`, 'error');
            return;
        }
        
        currentData = result;
        displayDocuments(result.documents);
    } catch (e) {
        showResult(`Error: ${e.message}`, 'error');
        console.error('Get documents error:', e);
    }
}

async function getElements() {
    if (!userId) {
        showResult('Please login first', 'error');
        return;
    }
    
    const did = document.getElementById('documentId').value.trim();
    const wid = document.getElementById('workspaceId').value.trim();
    
    if (!did || !wid) {
        showResult('Please fill in Document ID and Workspace ID', 'error');
        return;
    }
    
    showResult('📄 Loading elements...', 'info');
    
    try {
        const r = await fetchWithTimeout(`/api/documents/${did}/elements?workspace_id=${wid}&user_id=${userId}`, {}, API_TIMEOUT);
        const result = await r.json();
        
        if (result.status !== 'success') {
            showResult(`Error: ${result.error || 'Failed to load elements'}`, 'error');
            return;
        }
        
        currentData = result;
        displayElements(result.elements);
    } catch (e) {
        showResult(`Error: ${e.message}`, 'error');
        console.error('Get elements error:', e);
    }
}

async function getBOM() {
    if (!userId) {
        showResult('Please login first', 'error');
        return;
    }
    
    const did = document.getElementById('documentId').value.trim();
    const wid = document.getElementById('workspaceId').value.trim();
    const eid = document.getElementById('elementId').value.trim();
    
    if (!did || !wid || !eid) {
        showResult('❌ Please fill all fields: Document ID, Workspace ID, Element ID', 'error');
        return;
    }
    
    currentDocId = did;
    currentWorkId = wid;
    currentElemId = eid;
    
    showResult('📊 Loading BOM...', 'info');
    
    try {
        const url = `/api/bom/fetch?doc_id=${encodeURIComponent(did)}&workspace_id=${encodeURIComponent(wid)}&element_id=${encodeURIComponent(eid)}&user_id=${encodeURIComponent(userId)}&indented=${bomIndented}`;
        console.log('🔄 Fetching BOM from:', url);
        
        const r = await fetchWithTimeout(url, {}, API_TIMEOUT);
        
        if (!r.ok) {
            const error = await r.json();
            showResult(`❌ Error: ${error.error || r.statusText}`, 'error');
            return;
        }
        
        const result = await r.json();
        
        if (result.status !== 'success') {
            showResult(`❌ Error: ${result.message || 'Failed to load BOM'}`, 'error');
            return;
        }
        
        currentData = result.data;
        displayBOM(result.data);
        document.getElementById('pushBomBtn').style.display = 'inline-block';
        console.log('✅ BOM loaded successfully with', result.data?.bomTable?.items?.length || 0, 'items');
    } catch (e) {
        showResult(`❌ Error: ${e.message}`, 'error');
        console.error('Get BOM error:', e);
    }
}

async function getBoundingBoxes() {
    if (!userId) {
        showResult('Please login first', 'error');
        return;
    }
    
    const did = document.getElementById('documentId').value.trim();
    const wid = document.getElementById('workspaceId').value.trim();
    const eid = document.getElementById('elementId').value.trim();
    
    if (!did || !wid || !eid) {
        showResult('❌ Please fill all fields: Document ID, Workspace ID, Element ID', 'error');
        return;
    }
    
    showResult('📏 Loading bounding boxes...', 'info');
    
    try {
        const url = `/api/properties/bounding-boxes?doc_id=${encodeURIComponent(did)}&workspace_id=${encodeURIComponent(wid)}&element_id=${encodeURIComponent(eid)}&user_id=${encodeURIComponent(userId)}`;
        console.log('🔄 Fetching bounding boxes from:', url);
        
        const r = await fetchWithTimeout(url, {}, API_TIMEOUT);
        
        if (!r.ok) {
            const error = await r.json();
            console.error('❌ Server error:', error);
            showResult(`❌ Error: ${error.error || r.statusText}`, 'error');
            return;
        }
        
        const result = await r.json();
        
        if (result.status !== 'success') {
            showResult(`❌ Error: ${result.message || 'Failed to load bounding boxes'}`, 'error');
            return;
        }
        
        if (!result.data || result.data.length === 0) {
            showResult('⚠️ No bounding boxes found. This might be a PartStudio (not Assembly). Try selecting an Assembly instead.', 'info');
            return;
        }
        
        currentData = result.data;
        displayBoundingBoxes(result.data);
        console.log('✅ Bounding boxes loaded successfully:', result.data.length, 'parts found');
    } catch (e) {
        showResult(`❌ Error: ${e.message}`, 'error');
        console.error('Get bounding boxes error:', e);
    }
}

async function getConfigurationVariables() {
    if (!userId) {
        showResult('Please login first', 'error');
        return;
    }
    
    const did = document.getElementById('documentId').value.trim();
    const wid = document.getElementById('workspaceId').value.trim();
    const eid = document.getElementById('elementId').value.trim();
    
    if (!did || !wid || !eid) {
        showResult('❌ Please fill all fields: Document ID, Workspace ID, Element ID', 'error');
        return;
    }
    
    showResult('📋 Loading configuration variables...', 'info');
    
    try {
        const url = `/api/properties/configuration?doc_id=${encodeURIComponent(did)}&workspace_id=${encodeURIComponent(wid)}&element_id=${encodeURIComponent(eid)}&user_id=${encodeURIComponent(userId)}`;
        console.log('🔄 Fetching variables from:', url);
        
        const r = await fetchWithTimeout(url, {}, API_TIMEOUT);
        
        if (!r.ok) {
            const error = await r.json();
            console.error('❌ Server error:', error);
            showResult(`❌ Error: ${error.error || r.statusText}`, 'error');
            return;
        }
        
        const result = await r.json();
        
        if (result.status !== 'success') {
            showResult(`⚠️ ${result.message || 'No variables found or feature not available'}`, 'info');
            return;
        }
        
        currentData = result.data;
        displayVariables(result.data);
        console.log('✅ Variables loaded successfully');
    } catch (e) {
        showResult(`❌ Error: ${e.message}`, 'error');
        console.error('Get variables error:', e);
    }
}

async function createLengthProperties() {
    if (!userId) {
        showResult('Please login first', 'error');
        return;
    }
    
    const did = document.getElementById('documentId').value.trim();
    const wid = document.getElementById('workspaceId').value.trim();
    const eid = document.getElementById('elementId').value.trim();
    
    if (!did || !wid || !eid) {
        showResult('❌ Please fill all fields', 'error');
        return;
    }
    
    if (!confirm('Create Length, Width, Height properties from bounding boxes? This will add custom properties to all parts in OnShape.')) {
        return;
    }
    
    showResult('📐 Creating length properties from bounding boxes...', 'info');
    
    try {
        const r = await fetchWithTimeout('/api/properties/create-length-properties', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: userId,
                doc_id: did,
                workspace_id: wid,
                element_id: eid
            })
        }, API_TIMEOUT);
        
        if (!r.ok) {
            const error = await r.json();
            showResult(`❌ Error: ${error.error || r.statusText}`, 'error');
            return;
        }
        
        const result = await r.json();
        
        let msg = `✅ ${result.message || 'Properties created'}`;
        if (result.errors && result.errors.length > 0) {
            msg += `<br><br><strong>⚠️ Errors (${result.errors.length}):</strong><br>`;
            msg += result.errors.slice(0, 5).join('<br>');
            if (result.errors.length > 5) {
                msg += `<br>... and ${result.errors.length - 5} more`;
            }
        }
        
        showResult(msg, result.updated_count > 0 ? 'success' : 'error');
        console.log(`✅ Updated ${result.updated_count}/${result.total_parts} parts`);
    } catch (e) {
        showResult(`❌ Error: ${e.message}`, 'error');
        console.error('Create length properties error:', e);
    }
}

async function pushBOMToOnShape() {
    if (!userId || !currentDocId || !currentWorkId || !currentElemId) {
        showResult('❌ Please load a BOM first', 'error');
        return;
    }
    
    if (!currentData || !currentData.bomTable || !currentData.bomTable.items) {
        showResult('❌ No BOM data to push', 'error');
        return;
    }
    
    if (!confirm('Push BOM changes back to OnShape? This will update the assembly. Note: Some fields may be read-only in OnShape.')) {
        return;
    }
    
    showResult('⬆️ Pushing BOM to OnShape...', 'info');
    console.log('📤 Pushing BOM data:', currentData);
    
    try {
        const r = await fetchWithTimeout('/api/bom/push', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: userId,
                doc_id: currentDocId,
                workspace_id: currentWorkId,
                element_id: currentElemId,
                bom_data: currentData.bomTable.items
            })
        }, API_TIMEOUT);
        
        if (!r.ok) {
            const error = await r.json();
            console.error('Server error:', error);
            showResult(`❌ Error: ${error.error || r.statusText}`, 'error');
            return;
        }
        
        const result = await r.json();
        
        if (result.status === 'success') {
            showResult(`✅ BOM successfully pushed to OnShape! Updated ${result.updated_count || 0} items.`, 'success');
        } else {
            showResult(`⚠️ ${result.message || 'Push completed with issues'}`, result.updated_count > 0 ? 'success' : 'error');
        }
        
        console.log('✅ Push result:', result);
    } catch (e) {
        showResult(`❌ Error pushing BOM: ${e.message}`, 'error');
        console.error('Push BOM error:', e);
    }
}

// ============= UNIT CONVERSION FUNCTIONS =============

async function convertUnit() {
    const value = document.getElementById('convertValue').value;
    const unit = document.getElementById('convertUnit').value;
    
    if (!value) {
        showResult('Please enter a value', 'error');
        return;
    }
    
    try {
        console.log(`🔄 Converting ${value} ${unit} to MM`);
        
        const response = await fetch('/api/bom/convert-unit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ value, unit })
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            document.getElementById('conversionResult').innerHTML = `
                <div class="success">
                    ✅ <strong>${result.original} ${result.unit}</strong> = 
                    <strong style="font-size: 18px;">${result.converted_mm} mm</strong>
                </div>
            `;
            console.log(`✅ Conversion successful: ${result.converted_mm} mm`);
        } else {
            document.getElementById('conversionResult').innerHTML = `
                <div class="error">❌ ${result.message || 'Conversion failed'}</div>
            `;
        }
    } catch (e) {
        document.getElementById('conversionResult').innerHTML = `
            <div class="error">❌ Error: ${e.message}</div>
        `;
        console.error('Conversion error:', e);
    }
}

async function calculateVolume() {
    const length = parseFloat(document.getElementById('lengthMM').value);
    const width = parseFloat(document.getElementById('widthMM').value);
    const height = parseFloat(document.getElementById('heightMM').value);
    
    if (!length || !width || !height) {
        showResult('Please enter all dimensions', 'error');
        return;
    }
    
    try {
        console.log(`📐 Calculating volume: ${length}×${width}×${height} mm`);
        
        const response = await fetch('/api/bom/calculate-volume', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ length_mm: length, width_mm: width, height_mm: height })
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            document.getElementById('volumeResult').innerHTML = `
                <div class="success">
                    ✅ <strong>${length}</strong> × <strong>${width}</strong> × <strong>${height}</strong> mm
                    <br>= <strong style="font-size: 18px; color: #28a745;">${result.volume_mm3} mm³</strong>
                </div>
            `;
            console.log(`✅ Volume calculated: ${result.volume_mm3} mm³`);
        }
    } catch (e) {
        document.getElementById('volumeResult').innerHTML = `
            <div class="error">❌ Error: ${e.message}</div>
        `;
        console.error('Volume calculation error:', e);
    }
}

function toggleDimensionMode() {
    const useCheckbox = document.getElementById('useBoundingBoxes').checked;
    document.getElementById('manualMode').style.display = useCheckbox ? 'none' : 'block';
    document.getElementById('bboxMode').style.display = useCheckbox ? 'block' : 'none';
    console.log(`🔄 Dimension mode toggled: ${useCheckbox ? 'Bounding Boxes' : 'Manual'}`);
}

async function addDimensionsToBOM() {
    if (!currentDocId || !currentWorkId || !currentElemId || !userId) {
        showResult('Please load a BOM first', 'error');
        return;
    }
    
    const useBbox = document.getElementById('useBoundingBoxes').checked;
    
    let lengthValues = [];
    let widthValues = [];
    let heightValues = [];
    
    if (!useBbox) {
        lengthValues = document.getElementById('lengthInput').value.split('\n').filter(v => v.trim());
        widthValues = document.getElementById('widthInput').value.split('\n').filter(v => v.trim());
        heightValues = document.getElementById('heightInput').value.split('\n').filter(v => v.trim());
        
        if (!lengthValues.length && !widthValues.length && !heightValues.length) {
            showResult('Please enter dimension values', 'error');
            return;
        }
    }
    
    showResult('Adding dimensions to BOM...', 'info');
    console.log(`📝 Adding dimensions: ${useBbox ? 'from bounding boxes' : 'from manual input'}`);
    
    try {
        const response = await fetch('/api/bom/add-dimensions-to-bom', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                doc_id: currentDocId,
                workspace_id: currentWorkId,
                element_id: currentElemId,
                user_id: userId,
                length_values: lengthValues,
                width_values: widthValues,
                height_values: heightValues,
                use_bounding_boxes: useBbox
            })
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            currentData = result.bom_items;
            displayBOM({ bomTable: { items: result.bom_items } });
            document.getElementById('dimensionResult').innerHTML = `
                <div class="success">
                    ✅ Added dimensions to <strong>${result.items_count}</strong> BOM items
                    <br>New columns added: Length (mm), Width (mm), Height (mm), Volume (mm³)
                </div>
            `;
            console.log(`✅ Dimensions added to ${result.items_count} items`);
        } else {
            showResult(`Error: ${result.message || 'Failed to add dimensions'}`, 'error');
        }
    } catch (e) {
        document.getElementById('dimensionResult').innerHTML = `
            <div class="error">❌ Error: ${e.message}</div>
        `;
        console.error('Add dimensions error:', e);
    }
}

async function showSupportedUnits() {
    try {
        console.log('📋 Fetching supported units');
        
        const response = await fetch('/api/bom/supported-units');
        const result = await response.json();
        
        let html = '<h4>Supported Units (Conversion to MM):</h4>';
        html += '<table style="width: 100%; border-collapse: collapse;">';
        html += '<tr style="background: #667eea; color: white;"><th style="padding: 10px;">Unit</th><th style="padding: 10px;">Factor</th></tr>';
        
        for (const [unit, factor] of Object.entries(result.supported_units)) {
            html += `<tr style="border-bottom: 1px solid #ddd;"><td style="padding: 8px;">${unit}</td><td style="padding: 8px;">${factor}</td></tr>`;
        }
        
        html += '</table>';
        
        document.getElementById('unitsResult').innerHTML = html;
        console.log('✅ Units displayed');
    } catch (e) {
        document.getElementById('unitsResult').innerHTML = `<div class="error">❌ Error loading units: ${e.message}</div>`;
        console.error('Show units error:', e);
    }
}

// ============= HELPER FUNCTIONS =============

async function fetchWithTimeout(url, options = {}, timeoutMs = 15000) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
    
    try {
        const response = await fetch(url, {
            ...options,
            signal: controller.signal
        });
        clearTimeout(timeoutId);
        return response;
    } catch (error) {
        clearTimeout(timeoutId);
        if (error.name === 'AbortError') {
            throw new Error(`Request timeout after ${timeoutMs}ms`);
        }
        throw error;
    }
}
