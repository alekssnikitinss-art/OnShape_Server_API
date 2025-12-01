// UI.JS - All display and UI functions

function showResult(msg, type) {
    const div = document.getElementById('results');
    div.innerHTML = '<div class="' + (type || '') + '">' + msg + '</div>';
}

function displayDocuments(data) {
    if (!data || !data.length) {
        showResult('No documents found', 'error');
        return;
    }
    let h = '<h3>Your OnShape Documents</h3><table><tr><th>Name</th><th>Document ID</th><th>Modified</th><th>Action</th></tr>';
    data.forEach(d => {
        h += '<tr><td>' + (d.name || 'Unnamed') + '</td>';
        h += '<td>' + d.id.substring(0, 12) + '...</td>';
        h += '<td>' + new Date(d.modifiedAt).toLocaleString() + '</td>';
        h += '<td><button onclick="document.getElementById(\'documentId\').value=\'' + d.id + '\'">Use This</button></td></tr>';
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
        h += '<td><button onclick="document.getElementById(\'elementId\').value=\'' + e.id + '\'">Use This</button></td></tr>';
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
    if (!data.variables || data.variables.length === 0) {
        let msg = 'No configuration variables found';
        if (data.message) msg = data.message;
        showResult(msg, 'info');
        return;
    }
    
    let h = '<h3>Configuration Variables - Found ' + data.count + ' variables</h3>';
    h += '<p style="color:#666;margin-bottom:10px">💡 Click "Sync Variables to Properties" to add them to BOM.</p>';
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
    document.getElementById('results').innerHTML = h;
    attachEditListeners();
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

function toggleRow(rowId) {
    const children = document.querySelectorAll('.child-of-' + rowId);
    const icon = document.getElementById('icon-' + rowId);
    children.forEach(child => {
        child.classList.toggle('visible');
    });
    icon.classList.toggle('expanded');
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