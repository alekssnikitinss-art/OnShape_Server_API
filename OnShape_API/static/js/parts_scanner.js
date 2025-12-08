// PARTS SCANNER - Part scanning and metadata browser functions

let partsData = [];
let filteredPartsData = [];

async function scanPartstudioParts() {
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
    
    showResult('📦 Scanning PartStudio...', 'info');
    console.log('🔍 Starting PartStudio scan');
    
    try {
        const url = `/api/parts/scan-partstudio?doc_id=${encodeURIComponent(did)}&workspace_id=${encodeURIComponent(wid)}&element_id=${encodeURIComponent(eid)}&user_id=${encodeURIComponent(userId)}`;
        
        console.log('🔄 Fetching from:', url);
        const r = await fetchWithTimeout(url, {}, API_TIMEOUT);
        
        if (!r.ok) {
            const error = await r.json();
            console.error('❌ Server error:', error);
            showResult(`❌ Error: ${error.error || r.statusText}`, 'error');
            return;
        }
        
        const result = await r.json();
        console.log('📊 API Response:', result);
        
        if (result.status !== 'success') {
            showResult(`❌ Error: ${result.message}`, 'error');
            return;
        }
        
        partsData = result.parts || [];
        filteredPartsData = [...partsData];
        displayPartsList(partsData, result.type);
        showResult(`✅ Successfully scanned ${result.count} parts`, 'success');
        console.log(`✅ Scanned ${result.count} parts`);
        
    } catch (e) {
        showResult(`❌ Error: ${e.message}`, 'error');
        console.error('Scan error:', e);
    }
}

async function scanAssemblyComponents() {
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
    
    showResult('🏗️ Scanning Assembly...', 'info');
    console.log('🔍 Starting Assembly scan');
    
    try {
        const url = `/api/parts/scan-assembly?doc_id=${encodeURIComponent(did)}&workspace_id=${encodeURIComponent(wid)}&element_id=${encodeURIComponent(eid)}&user_id=${encodeURIComponent(userId)}`;
        
        console.log('🔄 Fetching from:', url);
        const r = await fetchWithTimeout(url, {}, API_TIMEOUT);
        
        if (!r.ok) {
            const error = await r.json();
            console.error('❌ Server error:', error);
            showResult(`❌ Error: ${error.error || r.statusText}`, 'error');
            return;
        }
        
        const result = await r.json();
        console.log('📊 API Response:', result);
        
        if (result.status !== 'success') {
            showResult(`❌ Error: ${result.message}`, 'error');
            return;
        }
        
        partsData = result.components || [];
        filteredPartsData = [...partsData];
        displayPartsList(partsData, result.type);
        showResult(`✅ Successfully scanned ${result.count} components`, 'success');
        console.log(`✅ Scanned ${result.count} components`);
        
    } catch (e) {
        showResult(`❌ Error: ${e.message}`, 'error');
        console.error('Scan error:', e);
    }
}

function displayPartsList(parts, type) {
    if (!parts || parts.length === 0) {
        document.getElementById('partsResults').innerHTML = '<div class="error">No parts found</div>';
        return;
    }
    
    let h = `<h3>${type} Parts List - ${parts.length} items</h3>`;
    h += '<table style="width:100%; border-collapse:collapse; background:white;">';
    h += '<tr style="background:#667eea; color:white;"><th style="padding:12px; text-align:left;">Name</th><th style="padding:12px; text-align:left;">Part ID</th><th style="padding:12px; text-align:left;">Material</th><th style="padding:12px; text-align:left;">Volume (mm³)</th><th style="padding:12px; text-align:left;">Props</th><th style="padding:12px; text-align:left;">Action</th></tr>';
    
    parts.forEach((part, idx) => {
        const name = part.name || 'Unknown';
        const partId = part.partId || part.componentId || 'N/A';
        const material = part.material || 'N/A';
        const volume = part.dimensions?.volume ? parseFloat(part.dimensions.volume).toFixed(2) : 'N/A';
        const propCount = part.propertyCount || 0;
        
        h += '<tr style="border-bottom:1px solid #ddd;">';
        h += `<td style="padding:12px;">${name}</td>`;
        h += `<td style="padding:12px;">${partId.substring(0, 12)}...</td>`;
        h += `<td style="padding:12px;">${material}</td>`;
        h += `<td style="padding:12px;">${volume}</td>`;
        h += `<td style="padding:12px;">📋 ${propCount}</td>`;
        h += `<td style="padding:12px;"><button onclick="viewPartMetadata('${partId}', '${name}')" style="padding:6px 12px; font-size:12px;">View</button></td>`;
        h += '</tr>';
    });
    
    h += '</table>';
    document.getElementById('partsResults').innerHTML = h;
}

async function viewPartMetadata(partId, partName) {
    const did = document.getElementById('documentId').value.trim();
    const wid = document.getElementById('workspaceId').value.trim();
    const eid = document.getElementById('elementId').value.trim();
    
    if (!did || !wid || !eid) {
        showResult('❌ Please fill all fields first', 'error');
        return;
    }
    
    console.log(`📋 Getting metadata for ${partName} (${partId})`);
    
    try {
        const url = `/api/parts/part-metadata?doc_id=${encodeURIComponent(did)}&workspace_id=${encodeURIComponent(wid)}&element_id=${encodeURIComponent(eid)}&part_id=${encodeURIComponent(partId)}&user_id=${encodeURIComponent(userId)}`;
        
        const r = await fetch(url);
        const result = await r.json();
        
        console.log('📊 Metadata response:', result);
        
        if (result.properties && result.properties.length > 0) {
            let h = `<h4>📋 Metadata for ${partName}</h4>`;
            h += '<table style="width:100%; border-collapse:collapse;"><tr style="background:#f0f0f0;"><th style="padding:10px; text-align:left;">Property</th><th style="padding:10px; text-align:left;">Value</th></tr>';
            result.properties.forEach(prop => {
                const propName = typeof prop === 'object' ? (prop.name || 'N/A') : prop;
                const propValue = typeof prop === 'object' ? (prop.value || 'N/A') : 'N/A';
                h += `<tr style="border-bottom:1px solid #ddd;"><td style="padding:10px;">${propName}</td><td style="padding:10px;">${propValue}</td></tr>`;
            });
            h += '</table>';
            document.getElementById('results').innerHTML = h;
            console.log(`✅ Found ${result.count} properties`);
        } else {
            showResult(`ℹ️ No custom properties found for ${partName}`, 'info');
            console.log('ℹ️ No properties');
        }
        
    } catch (e) {
        showResult(`❌ Error: ${e.message}`, 'error');
        console.error('Get metadata error:', e);
    }
}

function searchParts() {
    const searchTerm = document.getElementById('searchParts').value.trim().toLowerCase();
    
    if (!searchTerm) {
        filteredPartsData = [...partsData];
        displayPartsList(partsData, 'Filtered');
        return;
    }
    
    filteredPartsData = partsData.filter(part => {
        const name = (part.name || '').toLowerCase();
        const id = (part.partId || part.componentId || '').toLowerCase();
        const material = (part.material || '').toLowerCase();
        
        return name.includes(searchTerm) || 
               id.includes(searchTerm) || 
               material.includes(searchTerm);
    });
    
    displayPartsList(filteredPartsData, `Filtered (${filteredPartsData.length})`);
    console.log(`🔍 Found ${filteredPartsData.length} matching parts`);
}

function exportPartsListJSON() {
    if (!partsData || partsData.length === 0) {
        alert('No parts data to export');
        return;
    }
    
    try {
        const blob = new Blob([JSON.stringify(partsData, null, 2)], {type: 'application/json'});
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'parts-list-' + Date.now() + '.json';
        a.click();
        URL.revokeObjectURL(url);
        console.log('✅ Parts exported as JSON');
    } catch (e) {
        alert('Error exporting: ' + e.message);
    }
}

function exportPartsListCSV() {
    if (!partsData || partsData.length === 0) {
        alert('No parts data to export');
        return;
    }
    
    try {
        let csv = 'Name,Part ID,Material,Volume (mm³),Properties\n';
        
        partsData.forEach(part => {
            const name = part.name || 'Unknown';
            const partId = part.partId || part.componentId || 'N/A';
            const material = part.material || 'N/A';
            const volume = part.dimensions?.volume ? parseFloat(part.dimensions.volume).toFixed(2) : 'N/A';
            const propCount = part.propertyCount || 0;
            
            csv += `"${name}","${partId}","${material}","${volume}","${propCount}"\n`;
        });
        
        const blob = new Blob([csv], {type: 'text/csv'});
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'parts-list-' + Date.now() + '.csv';
        a.click();
        URL.revokeObjectURL(url);
        console.log('✅ Parts exported as CSV');
    } catch (e) {
        alert('Error exporting: ' + e.message);
    }
}

// Setup event listeners (called from app.js)
function setupPartsScannerListeners() {
    const scanPartstudioBtn = document.getElementById('scanPartstudioBtn');
    const scanAssemblyBtn = document.getElementById('scanAssemblyBtn');
    const searchParts = document.getElementById('searchParts');
    const exportPartsBtn = document.getElementById('exportPartsBtn');
    const exportMetadataBtn = document.getElementById('exportMetadataBtn');
    
    if (scanPartstudioBtn) {
        scanPartstudioBtn.onclick = scanPartstudioParts;
    }
    
    if (scanAssemblyBtn) {
        scanAssemblyBtn.onclick = scanAssemblyComponents;
    }
    
    if (searchParts) {
        searchParts.addEventListener('keyup', searchParts);
    }
    
    if (exportPartsBtn) {
        exportPartsBtn.onclick = exportPartsListJSON;
    }
    
    if (exportMetadataBtn) {
        exportMetadataBtn.onclick = exportPartsListCSV;
    }
}

// Auto-setup when document loads
document.addEventListener('DOMContentLoaded', setupPartsScannerListeners);