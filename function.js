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
