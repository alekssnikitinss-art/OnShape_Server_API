// static/js/advanced.js - Advanced Features JavaScript
// COMPLETELY INDEPENDENT FILE - Can be loaded after other JS files

// Global state for advanced features
let advancedBOMData = null;
let advancedColumnSettings = {};

// Setup event listeners when document is ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('🔧 Setting up advanced features listeners');
    
    // Save Named
    const saveNamedBtn = document.getElementById('saveNamedBtn');
    if (saveNamedBtn) {
        saveNamedBtn.onclick = saveNamed;
        console.log('✅ Bound saveNamedBtn');
    }
    
    // Search Elements
    const searchElementsBtn = document.getElementById('searchElementsBtn');
    if (searchElementsBtn) {
        searchElementsBtn.onclick = searchElements;
        console.log('✅ Bound searchElementsBtn');
    }
    
    // Complete BOM
    const completeBomBtn = document.getElementById('completeBomBtn');
    if (completeBomBtn) {
        completeBomBtn.onclick = getCompleteBOM;
        console.log('✅ Bound completeBomBtn');
    }
    
    // Rename Columns
    const renameColumnsBtn = document.getElementById('renameColumnsBtn');
    if (renameColumnsBtn) {
        renameColumnsBtn.onclick = renameColumns;
        console.log('✅ Bound renameColumnsBtn');
    }
    
    // Add Custom Column
    const addCustomColumnBtn = document.getElementById('addCustomColumnBtn');
    if (addCustomColumnBtn) {
        addCustomColumnBtn.onclick = addCustomColumn;
        console.log('✅ Bound addCustomColumnBtn');
    }
    
    // Load Saved
    const loadSavedBtn = document.getElementById('loadSavedBtn');
    if (loadSavedBtn) {
        loadSavedBtn.onclick = loadSavedDocuments;
        console.log('✅ Bound loadSavedBtn');
    }
    
    console.log('✅ Advanced features setup complete');
});

// ============= 1. SAVE WITH CUSTOM NAME =============

async function saveNamed() {
    if (!userId) {
        showResult('Please login first', 'error');
        return;
    }
    
    const did = document.getElementById('documentId').value.trim();
    const wid = document.getElementById('workspaceId').value.trim();
    const eid = document.getElementById('elementId').value.trim();
    
    if (!did || !wid || !eid) {
        showResult('❌ Please fill: Document ID, Workspace ID, Element ID', 'error');
        return;
    }
    
    const customName = prompt('💾 Enter custom name for this document:', 'My Assembly v1');
    if (!customName) return;
    
    const tags = prompt('📌 Tags (comma-separated, optional):', 'production').split(',').map(t => t.trim()).filter(t => t);
    const notes = prompt('📝 Notes (optional):', '');
    
    showResult('💾 Saving document with custom name...', 'info');
    console.log(`💾 Saving: "${customName}" | Tags: ${tags.join(', ')}`);
    
    try {
        const response = await fetch('/api/advanced/save-named', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: userId,
                document_id: did,
                workspace_id: wid,
                element_id: eid,
                custom_name: customName,
                tags: tags,
                notes: notes
            })
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            const tagStr = tags.length > 0 ? `<br>📌 Tags: ${tags.join(', ')}` : '';
            const noteStr = notes ? `<br>📝 Notes: ${notes}` : '';
            
            showResult(
                `✅ Document saved as "<strong>${customName}</strong>"${tagStr}${noteStr}`,
                'success'
            );
            console.log('✅ Document saved:', result.document);
        } else {
            showResult(`❌ Error: ${result.message}`, 'error');
        }
    } catch (e) {
        showResult(`❌ Error: ${e.message}`, 'error');
        console.error('❌ Save error:', e);
    }
}

// ============= 2. SEARCH ELEMENTS =============

async function searchElements() {
    if (!userId) {
        showResult('Please login first', 'error');
        return;
    }
    
    const did = document.getElementById('documentId').value.trim();
    const wid = document.getElementById('workspaceId').value.trim();
    
    if (!did || !wid) {
        showResult('❌ Please fill: Document ID, Workspace ID', 'error');
        return;
    }
    
    const searchTerm = prompt('🔍 Search by name (leave blank for all):', '');
    const elemType = prompt('🏷️ Filter by type:\n- Assembly\n- PartStudio\n- BLOB\n- APPLICATION\n\n(leave blank for all):', '');
    
    showResult('🔍 Searching elements...', 'info');
    console.log(`🔍 Searching: term="${searchTerm}" | type="${elemType}"`);
    
    try {
        const params = new URLSearchParams({
            doc_id: did,
            workspace_id: wid,
            user_id: userId,
            search_term: searchTerm || '',
            element_type: elemType || ''
        });
        
        const response = await fetchWithTimeout(`/api/advanced/search-elements?${params}`, {}, 30000);
        const result = await response.json();
        
        if (result.status === 'success') {
            displaySearchResults(result);
            console.log(`✅ Found ${result.count} elements`);
        } else {
            showResult(`❌ Error: ${result.message}`, 'error');
        }
    } catch (e) {
        showResult(`❌ Error: ${e.message}`, 'error');
        console.error('❌ Search error:', e);
    }
}

function displaySearchResults(result) {
    if (!result.elements || result.elements.length === 0) {
        showResult('❌ No elements found matching your search', 'info');
        return;
    }
    
    let h = `<h3>🔍 Found ${result.count}/${result.total} Elements</h3>`;
    
    // Type summary
    if (result.types && Object.keys(result.types).length > 0) {
        h += '<div style="background:#e7f3ff; padding:10px; border-radius:4px; margin-bottom:15px;">';
        h += '<strong>Types:</strong> ';
        for (const [type, count] of Object.entries(result.types)) {
            h += `${type} (${count}), `;
        }
        h = h.slice(0, -2);
        h += '</div>';
    }
    
    h += '<table style="width:100%; border-collapse:collapse;"><tr style="background:#667eea; color:white;"><th style="padding:12px; text-align:left;">Name</th><th style="padding:12px; text-align:left;">Type</th><th style="padding:12px; text-align:left;">Element ID</th><th style="padding:12px; text-align:left;">Action</th></tr>';
    
    result.elements.forEach(elem => {
        h += `<tr style="border-bottom:1px solid #ddd;">`;
        h += `<td style="padding:12px;"><strong>${elem.name}</strong></td>`;
        h += `<td style="padding:12px;"><span style="background:#667eea; color:white; padding:4px 8px; border-radius:3px; font-size:12px;">${elem.type}</span></td>`;
        h += `<td style="padding:12px; font-family:monospace; font-size:12px;">${elem.id.substring(0, 16)}...</td>`;
        h += `<td style="padding:12px;"><button onclick="setElementFromSearch('${elem.id}')" style="padding:6px 12px; font-size:12px; background:#667eea; color:white; border:none; border-radius:4px; cursor:pointer;">Use</button></td>`;
        h += '</tr>';
    });
    
    h += '</table>';
    document.getElementById('results').innerHTML = h;
}

function setElementFromSearch(elemId) {
    document.getElementById('elementId').value = elemId;
    showResult(`✅ Loaded element ID: ${elemId.substring(0, 16)}...`, 'success');
}

// ============= 3. COMPLETE BOM WITH ALL COLUMNS =============

async function getCompleteBOM() {
    if (!userId) {
        showResult('Please login first', 'error');
        return;
    }
    
    const did = document.getElementById('documentId').value.trim();
    const wid = document.getElementById('workspaceId').value.trim();
    const eid = document.getElementById('elementId').value.trim();
    
    if (!did || !wid || !eid) {
        showResult('❌ Please fill: Document ID, Workspace ID, Element ID', 'error');
        return;
    }
    
    showResult('📊 Loading complete BOM with ALL available columns...', 'info');
    console.log('📊 Fetching complete BOM');
    
    try {
        const url = `/api/advanced/bom-complete?doc_id=${encodeURIComponent(did)}&workspace_id=${encodeURIComponent(wid)}&element_id=${encodeURIComponent(eid)}&user_id=${encodeURIComponent(userId)}`;
        
        const response = await fetchWithTimeout(url, {}, 60000);
        const result = await response.json();
        
        if (result.status === 'success') {
            advancedBOMData = result;
            displayCompleteBOM(result);
            console.log(`✅ BOM loaded: ${result.count} items, ${result.column_count} columns`);
        } else {
            showResult(`❌ Error: ${result.message}`, 'error');
        }
    } catch (e) {
        showResult(`❌ Error: ${e.message}`, 'error');
        console.error('❌ BOM fetch error:', e);
    }
}

function displayCompleteBOM(data) {
    if (!data.items || data.items.length === 0) {
        showResult('⚠️ BOM is empty', 'info');
        return;
    }
    
    const cols = data.columns;
    const items = data.items;
    
    let h = `<h3>📊 Complete BOM: ${items.length} items × ${cols.length} columns</h3>`;
    
    // Column summary
    h += '<div style="background:#e7f3ff; padding:10px; border-radius:4px; margin-bottom:15px;">';
    h += `<strong>Column Summary:</strong><br>`;
    h += `✓ Present in all items: ${data.grouping.all_100_percent.length} columns<br>`;
    h += `✓ Present in most items: ${data.grouping.most_50_percent.length} columns<br>`;
    h += `✓ Present in few items: ${data.grouping.few_under_50.length} columns`;
    h += '</div>';
    
    h += '<table style="width:100%; border-collapse:collapse;"><tr style="background:#667eea; color:white;">';
    
    cols.forEach(col => {
        const bgColor = col.presence_percent === 100 ? '#667eea' : col.presence_percent >= 50 ? '#7b8ed8' : '#9aaee6';
        h += `<th style="padding:10px; background:${bgColor}; text-align:left; white-space:nowrap;">`;
        h += `${col.name}<br><span style="font-size:9px; opacity:0.8;">${col.presence_percent}%</span>`;
        h += `</th>`;
    });
    
    h += '</tr>';
    
    items.forEach((item, idx) => {
        h += '<tr style="border-bottom:1px solid #ddd;">';
        cols.forEach(col => {
            const val = item[col.key] !== undefined ? item[col.key] : '-';
            const isMissing = val === '-' ? 'opacity:0.5;' : '';
            h += `<td style="padding:10px; ${isMissing}" class="editable-cell" contenteditable="true" data-row="${idx}" data-field="${col.key}" data-type="bom">${val}</td>`;
        });
        h += '</tr>';
    });
    
    h += '</table>';
    document.getElementById('results').innerHTML = h;
    attachEditListeners();
}

// ============= 4. RENAME COLUMNS =============

async function renameColumns() {
    if (!advancedBOMData || !advancedBOMData.columns) {
        showResult('❌ Please load BOM first', 'error');
        return;
    }
    
    const eid = document.getElementById('elementId').value.trim();
    if (!eid) {
        showResult('❌ Element ID missing', 'error');
        return;
    }
    
    const current = advancedBOMData.columns.map(c => `${c.key} -> ${c.name}`).join('\n');
    const input = prompt('🏷️ Rename columns (format: old_name -> new_name):\n\nLeave blank or use null to hide column\n\n', current);
    
    if (!input) return;
    
    const renames = {};
    const lines = input.split('\n').filter(l => l.trim());
    
    lines.forEach(line => {
        const parts = line.split('->').map(s => s.trim());
        if (parts.length === 2 && parts[0] && parts[1]) {
            if (parts[1].toLowerCase() !== 'null') {
                renames[parts[0]] = parts[1];
            }
        }
    });
    
    showResult('🏷️ Processing column renames...', 'info');
    console.log('🏷️ Renaming columns:', renames);
    
    try {
        const response = await fetch('/api/advanced/column-settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                element_id: eid,
                renames: renames
            })
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            advancedColumnSettings.renames = renames;
            localStorage.setItem(`bom_columns_${eid}`, JSON.stringify(renames));
            showResult(
                `✅ ${Object.keys(renames).length} columns renamed<br>✅ Saved to browser storage`,
                'success'
            );
            console.log('✅ Column renames applied:', renames);
        }
    } catch (e) {
        showResult(`❌ Error: ${e.message}`, 'error');
        console.error('❌ Rename error:', e);
    }
}

// ============= 5. ADD CUSTOM COLUMN =============

async function addCustomColumn() {
    if (!advancedBOMData) {
        showResult('❌ Please load BOM first', 'error');
        return;
    }
    
    const eid = document.getElementById('elementId').value.trim();
    if (!eid) {
        showResult('❌ Element ID missing', 'error');
        return;
    }
    
    const colName = prompt('➕ Column name:', 'Unit Cost');
    if (!colName) return;
    
    const colType = prompt('📊 Data type:\n- string\n- number\n- boolean\n- date\n- currency\n\nSelect one:', 'number');
    if (!colType) return;
    
    const defaultVal = prompt('🔧 Default value:', '0');
    
    showResult('➕ Adding custom column...', 'info');
    console.log(`➕ Adding column: ${colName} (${colType})`);
    
    try {
        const response = await fetch('/api/advanced/column-settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                element_id: eid,
                custom_columns: [
                    {
                        key: colName.toLowerCase().replace(/\s+/g, '_'),
                        name: colName,
                        type: colType,
                        default: defaultVal
                    }
                ]
            })
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            localStorage.setItem(`bom_custom_${eid}`, JSON.stringify(result.custom_columns));
            showResult(
                `✅ Custom column "${colName}" created<br>✅ Type: ${colType}<br>✅ Saved to browser storage`,
                'success'
            );
            console.log('✅ Custom column added:', result.custom_columns);
        }
    } catch (e) {
        showResult(`❌ Error: ${e.message}`, 'error');
        console.error('❌ Add column error:', e);
    }
}

// ============= 6. LOAD SAVED DOCUMENTS =============

async function loadSavedDocuments() {
    if (!userId) {
        showResult('❌ Please login first', 'error');
        return;
    }
    
    const search = prompt('📂 Search by name (leave blank for all):', '');
    const type = prompt('🏷️ Filter by type:\n- Assembly\n- PartStudio\n\n(leave blank for all):', '');
    const sort = prompt('📊 Sort by:\n- last_used (default)\n- name\n- created\n\n', 'last_used');
    
    showResult('📂 Loading saved documents...', 'info');
    console.log(`📂 Loading: search="${search}" | type="${type}" | sort="${sort}"`);
    
    try {
        const params = new URLSearchParams({
            user_id: userId,
            search: search || '',
            element_type: type || '',
            sort_by: sort || 'last_used'
        });
        
        const response = await fetchWithTimeout(`/api/advanced/saved-filtered?${params}`, {}, 15000);
        const result = await response.json();
        
        if (result.status === 'success') {
            displaySavedDocuments(result);
            console.log(`✅ Loaded ${result.count} saved documents`);
        } else {
            showResult(`❌ Error: ${result.message}`, 'error');
        }
    } catch (e) {
        showResult(`❌ Error: ${e.message}`, 'error');
        console.error('❌ Load saved error:', e);
    }
}

function displaySavedDocuments(result) {
    if (!result.documents || result.documents.length === 0) {
        showResult('⚠️ No saved documents found', 'info');
        return;
    }
    
    let h = `<h3>📂 Saved Documents (${result.count})</h3>`;
    h += '<table style="width:100%; border-collapse:collapse;"><tr style="background:#667eea; color:white;"><th style="padding:12px; text-align:left;">Name</th><th style="padding:12px; text-align:left;">Type</th><th style="padding:12px; text-align:left;">Last Used</th><th style="padding:12px; text-align:left;">Action</th></tr>';
    
    result.documents.forEach(doc => {
        const lastUsed = new Date(doc.last_used_at).toLocaleDateString();
        h += `<tr style="border-bottom:1px solid #ddd;">`;
        h += `<td style="padding:12px;"><strong>${doc.document_name}</strong></td>`;
        h += `<td style="padding:12px;">${doc.element_type || 'Unknown'}</td>`;
        h += `<td style="padding:12px;">${lastUsed}</td>`;
        h += `<td style="padding:12px;"><button onclick="loadSavedDoc('${doc.document_id}','${doc.workspace_id}','${doc.element_id}')" style="padding:6px 12px; font-size:12px; background:#667eea; color:white; border:none; border-radius:4px; cursor:pointer;">Load</button></td>`;
        h += '</tr>';
    });
    
    h += '</table>';
    document.getElementById('results').innerHTML = h;
}

function loadSavedDoc(docId, workId, elemId) {
    document.getElementById('documentId').value = docId;
    document.getElementById('workspaceId').value = workId;
    document.getElementById('elementId').value = elemId;
    showResult(`✅ Loaded saved document`, 'success');
    console.log(`✅ Loaded: doc=${docId.substring(0, 8)} | work=${workId.substring(0, 8)} | elem=${elemId.substring(0, 8)}`);
}