// UI.JS - All display and UI functions (FIXED)

function showResult(msg, type) {
    const div = document.getElementById('results');
    if (!div) {
        console.error('Results element not found');
        return;
    }
    div.innerHTML = '<div class="' + (type || '') + '">' + msg + '</div>';
}

function displayDocuments(data) {
    if (!data || data.length === 0) {
        showResult('No documents found', 'error');
        return;
    }
    
    let h = '<h3>Your OnShape Documents</h3><table><tr><th>Name</th><th>Document ID</th><th>Modified</th><th>Action</th></tr>';
    
    data.forEach(d => {
        const docId = d.id || d.document_id || 'Unknown';
        const docName = d.name || 'Unnamed';
        const modDate = d.modifiedAt ? new Date(d.modifiedAt).toLocaleString() : 'Unknown';
        
        h += '<tr>';
        h += '<td>' + docName + '</td>';
        h += '<td>' + docId.substring(0, 12) + '...</td>';
        h += '<td>' + modDate + '</td>';
        h += '<td><button onclick="setDocumentId(\'' + docId + '\')">Use This</button></td>';
        h += '</tr>';
    });
    
    h += '</table>';
    document.getElementById('results').innerHTML = h;
}

function displayElements(data) {
    if (!data || data.length === 0) {
        showResult('No elements found in this document', 'error');
        return;
    }
    
    let h = '<h3>Document Elements</h3><table><tr><th>Name</th><th>Type</th><th>Element ID</th><th>Action</th></tr>';
    
    data.forEach(e => {
        const elemId = e.id || e.element_id || 'Unknown';
        const elemName = e.name || 'Unnamed';
        const elemType = e.elementType || e.type || 'Unknown';
        
        h += '<tr>';
        h += '<td>' + elemName + '</td>';
        h += '<td>' + elemType + '</td>';
        h += '<td>' + elemId.substring(0, 12) + '...</td>';
        h += '<td><button onclick="setElementId(\'' + elemId + '\')">Use This</button></td>';
        h += '</tr>';
    });
    
    h += '</table>';
    document.getElementById('results').innerHTML = h;
}

function displayBOM(data) {
    if (!data || !data.bomTable || !data.bomTable.items) {
        showResult('No BOM data found', 'error');
        return;
    }
    
    const items = data.bomTable.items;
    let h = '<h3>Bill of Materials (' + (bomIndented ? 'Structured' : 'Flattened') + ') - Editable</h3>';
    h += '<p style="color:#666;margin-bottom:10px">💡 Click any cell to edit values</p>';
    h += '<table><tr><th>Item</th><th>Part Number</th><th>Name</th><th>Quantity</th><th>Description</th></tr>';
    
    items.forEach((item, idx) => {
        const indent = item.indentLevel || 0;
        const hasChildren = item.hasChildren || false;
        const indentClass = 'indent-' + Math.min(indent, 3);
        
        h += '<tr>';
        h += '<td class="' + indentClass + '">' + (item.item || item.Item || '-') + '</td>';
        h += '<td class="editable-cell" contenteditable="true" data-row="' + idx + '" data-field="partNumber">' + (item.partNumber || item.PART_NUMBER || item['Part Number'] || '-') + '</td>';
        h += '<td class="editable-cell" contenteditable="true" data-row="' + idx + '" data-field="name">' + (item.name || item.NAME || item.Name || '-') + '</td>';
        h += '<td class="editable-cell" contenteditable="true" data-row="' + idx + '" data-field="quantity">' + (item.quantity || item.QUANTITY || item.Quantity || '-') + '</td>';
        h += '<td class="editable-cell" contenteditable="true" data-row="' + idx + '" data-field="description">' + (item.description || item.DESCRIPTION || item.Description || '-') + '</td>';
        h += '</tr>';
    });
    
    h += '</table>';
    document.getElementById('results').innerHTML = h;
    attachEditListeners();
}

function displayBoundingBoxes(data) {
    if (!data || data.length === 0) {
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
        } else if (box.dimensions) {
            x = box.dimensions.length || 0;
            y = box.dimensions.width || 0;
            z = box.dimensions.height || 0;
            vol = box.dimensions.volume || 0;
            pid = box.partId || 'Unknown';
        } else {
            x = ((box.highX || 0) - (box.lowX || 0)) * 1000;
            y = ((box.highY || 0) - (box.lowY || 0)) * 1000;
            z = ((box.highZ || 0) - (box.lowZ || 0)) * 1000;
            vol = (x * y * z);
            pid = box.partId || 'Unknown';
        }
        
        h += '<tr>';
        h += '<td class="editable-cell" contenteditable="true" data-row="' + idx + '" data-field="partId">' + pid + '</td>';
        h += '<td class="editable-cell" contenteditable="true" data-row="' + idx + '" data-field="lengthX">' + parseFloat(x).toFixed(2) + '</td>';
        h += '<td class="editable-cell" contenteditable="true" data-row="' + idx + '" data-field="lengthY">' + parseFloat(y).toFixed(2) + '</td>';
        h += '<td class="editable-cell" contenteditable="true" data-row="' + idx + '" data-field="lengthZ">' + parseFloat(z).toFixed(2) + '</td>';
        h += '<td>' + parseFloat(vol).toFixed(2) + '</td>';
        h += '</tr>';
    });
    
    h += '</table>';
    document.getElementById('results').innerHTML = h;
    attachEditListeners();
}

function displayVariables(data) {
    if (!data || !data.variables || data.variables.length === 0) {
        let msg = 'No configuration variables found';
        if (data && data.message) {
            msg = data.message;
        }
        showResult(msg, 'info');
        return;
    }
    
    let h = '<h3>Configuration Variables - Found ' + data.count + ' variables</h3>';
    h += '<p style="color:#666;margin-bottom:10px">💡 Click "Sync Variables to Properties" to add them to BOM.</p>';
    h += '<table><tr><th>Variable Name</th><th>Value</th><th>Unit</th><th>Part/Feature</th></tr>';
    
    data.variables.forEach((v, idx) => {
        h += '<tr>';
        h += '<td><strong>' + (v.name || v.variableName || 'Unknown') + '</strong></td>';
        h += '<td class="editable-cell" contenteditable="true" data-row="' + idx + '" data-field="value">' + (v.value || v.expression || '-') + '</td>';
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
    
    let h = '<h3>Length Properties Preview - ' + (data.element_type || 'Unknown') + '</h3>';
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
    if (!Array.isArray(data) || data.length === 0 || !data[0]) {
        showResult('No data to display', 'error');
        return;
    }
    
    const headers = Object.keys(data[0]);
    let h = '<h3>Data Table - Editable</h3><table><tr>';
    
    headers.forEach(header => {
        h += '<th>' + header + '</th>';
    });
    
    h += '</tr>';
    
    data.forEach((row, idx) => {
        h += '<tr>';
        headers.forEach(header => {
            h += '<td class="editable-cell" contenteditable="true" data-row="' + idx + '" data-field="' + header + '">' + (row[header] || '') + '</td>';
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
    
    if (children) {
        children.forEach(child => {
            child.classList.toggle('visible');
        });
    }
    
    if (icon) {
        icon.classList.toggle('expanded');
    }
}

function attachEditListeners() {
    const editableCells = document.querySelectorAll('.editable-cell');
    
    if (!editableCells) {
        return;
    }
    
    editableCells.forEach(cell => {
        cell.addEventListener('blur', function() {
            const row = parseInt(this.dataset.row);
            const field = this.dataset.field;
            const val = this.textContent.trim();
            
            if (currentData && currentData.bomTable && currentData.bomTable.items) {
                if (currentData.bomTable.items[row]) {
                    currentData.bomTable.items[row][field] = val;
                }
            } else if (Array.isArray(currentData) && currentData[row]) {
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
    
    try {
        const blob = new Blob([JSON.stringify(currentData, null, 2)], {type: 'application/json'});
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'onshape-data-' + Date.now() + '.json';
        a.click();
        URL.revokeObjectURL(url);
    } catch (e) {
        alert('Error downloading file: ' + e.message);
    }
}

function downloadAsCSV() {
    if (!currentData) {
        alert('No data to download');
        return;
    }
    
    try {
        let csv = '';
        
        if (currentData.bomTable && currentData.bomTable.items) {
            csv = 'Item,Part Number,Name,Quantity,Description\n';
            currentData.bomTable.items.forEach(item => {
                csv += '"' + (item.item || item.Item || '') + '","' + 
                       (item.partNumber || item.PART_NUMBER || '') + '","' + 
                       (item.name || item.NAME || '') + '","' + 
                       (item.quantity || item.QUANTITY || '') + '","' + 
                       (item.description || item.DESCRIPTION || '') + '"\n';
            });
        } else if (Array.isArray(currentData) && currentData.length > 0) {
            const headers = Object.keys(currentData[0]);
            csv = headers.join(',') + '\n';
            currentData.forEach(row => {
                csv += headers.map(h => '"' + (row[h] || '') + '"').join(',') + '\n';
            });
        }
        
        const blob = new Blob([csv], {type: 'text/csv'});
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'onshape-data-' + Date.now() + '.csv';
        a.click();
        URL.revokeObjectURL(url);
    } catch (e) {
        alert('Error downloading file: ' + e.message);
    }
}

function setDocumentId(id) {
    document.getElementById('documentId').value = id;
}

function setElementId(id) {
    document.getElementById('elementId').value = id;
}