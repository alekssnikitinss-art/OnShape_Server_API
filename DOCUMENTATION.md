# OnShape BOM Manager - Complete Documentation

**Version:** 2.1.0  
**Created:** December 2025  
**Status:** Active Development  
**Last Updated:** 09.12.2025

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture & Structure](#architecture--structure)
3. [Setup & Deployment](#setup--deployment)
4. [API Endpoints Reference](#api-endpoints-reference)
5. [OnShape API Integration](#onshape-api-integration)
6. [Database Schema](#database-schema)
7. [Frontend Features](#frontend-features)
8. [Known Issues & Fixes](#known-issues--fixes)
9. [Development Timeline](#development-timeline)
10. [Future Improvements](#future-improvements)

---

## Project Overview

**OnShape BOM Manager** is a web application that integrates with OnShape's REST API to manage Bills of Materials (BOMs), bounding boxes, custom properties, and metadata for CAD documents. It allows users to:

- Authenticate with OnShape via OAuth2
- Fetch and manage BOMs from Assemblies and PartStudios
- View and edit bounding box dimensions
- Access configuration variables
- Create and update custom part properties
- Export data in JSON/CSV formats
- Scan parts and view their metadata

**Tech Stack:**
- **Backend:** FastAPI (Python), SQLAlchemy ORM
- **Frontend:** Vanilla JavaScript, HTML/CSS
- **Database:** PostgreSQL (via Render) / SQLite (local)
- **Hosting:** Render.com
- **Authentication:** OAuth2

**Live Server:** https://onshape-server-api.onrender.com/

---

## Architecture & Structure

```
OnShape_API/
├── app.py                          # Main FastAPI application
├── config.py                       # Environment configuration
├── database.py                     # SQLAlchemy models & setup
│
├── routes/
│   ├── auth.py                     # OAuth login/callback
│   ├── documents.py                # Document listing & saving
│   ├── bom.py                      # BOM operations
│   ├── user.py                     # User information
│   ├── parts.py                    # Part scanning & metadata
│   └── metadata.py                 # Custom properties management
│
├── services/
│   ├── auth_service.py             # Token encryption & OAuth
│   ├── onshape_service.py          # OnShape API wrapper
│   ├── bom_service.py              # BOM processing
│   ├── bom_conversion.py           # Unit conversion
│   └── metadata_service.py         # Metadata operations
│
├── templates/
│   └── index.html                  # Main UI
│
├── static/
│   ├── css/
│   │   └── style.css               # Styling
│   └── js/
│       ├── app.js                  # App initialization
│       ├── api.js                  # API calls
│       ├── ui.js                   # Display functions
│       └── parts-scanner.js        # Part scanning
│
├── requirements.txt                # Python dependencies
├── render.yaml                     # Render.com config
├── Procfile                        # Heroku-style startup
└── .env.example                    # Environment template
```

---

## Setup & Deployment

### Local Development

```bash
# 1. Clone repository
git clone https://github.com/AleksNikitins/OnShape_Server_API.git
cd OnShape_API

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create .env file
cp .env.example .env
# Add your OnShape OAuth credentials:
# ONSHAPE_CLIENT_ID=your_client_id
# ONSHAPE_CLIENT_SECRET=your_client_secret
# ENCRYPTION_KEY=your_fernet_key
# DATABASE_URL=sqlite:///./onshape.db
```

**Generate Encryption Key:**
```python
from cryptography.fernet import Fernet
key = Fernet.generate_key().decode()
print(key)  # Add to .env as ENCRYPTION_KEY
```

**Create OnShape OAuth Application:**
1. Go to https://cad.onshape.com/appstore/dev-portal
2. Create new application with scopes: `OAuth2Read OAuth2Write`
3. Get Client ID and Secret
4. Set redirect URI: `https://onshape-server-api.onrender.com/auth/callback` (production)

### Production Deployment (Render.com)

```bash
# Push to GitHub main branch
git push origin main

# Render automatically:
# 1. Installs requirements.txt
# 2. Runs: uvicorn main:app --host 0.0.0.0 --port 10000
# 3. Deploys on onshape-server-api.onrender.com

# Typical startup time: 1-5 minutes
# Server sleeps after 15 minutes of inactivity
```

**Environment Variables (Set in Render Dashboard):**
- `DATABASE_URL` - PostgreSQL connection string
- `ONSHAPE_CLIENT_ID` - OAuth client ID
- `ONSHAPE_CLIENT_SECRET` - OAuth client secret
- `ONSHAPE_REDIRECT_URI` - Production callback URL
- `ENCRYPTION_KEY` - Fernet encryption key
- `DEBUG` - Set to "false" in production

---

## API Endpoints Reference

### Authentication Routes (`/auth`)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/auth/login` | Redirect to OnShape OAuth |
| GET | `/auth/callback` | OAuth callback handler |
| POST | `/auth/logout` | Log out user |

**Login Flow:**
1. User clicks "Login with OnShape" → `/auth/login`
2. OnShape redirects to OAuth authorization page
3. User grants permissions
4. OnShape redirects to `/auth/callback?code=xxx`
5. Backend exchanges code for access token
6. Token encrypted and stored in database
7. User ID saved to localStorage
8. Redirects to home page

### Documents Routes (`/api/documents`)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/list?user_id=xxx` | List user's OnShape documents |
| GET | `/{doc_id}/elements?workspace_id=xxx&user_id=xxx` | Get elements in document |
| POST | `/save` | Save document to user library |
| GET | `/saved?user_id=xxx` | Get user's saved documents |

**Save Document Example:**
```json
POST /api/documents/save
{
  "user_id": "user-id",
  "document_id": "doc-id",
  "workspace_id": "workspace-id",
  "element_id": "element-id",
  "document_name": "My Assembly",
  "element_name": "Main Assembly"
}
```

### BOM Routes (`/api/bom`)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/fetch?doc_id=xxx&workspace_id=xxx&element_id=xxx&user_id=xxx&indented=false` | Fetch BOM (Assembly or PartStudio) |
| POST | `/push` | Push BOM changes back to OnShape |
| POST | `/convert-unit` | Convert units to millimeters |
| POST | `/calculate-volume` | Calculate volume from dimensions |
| POST | `/add-dimensions-to-bom` | Add dimensions to BOM items |
| GET | `/supported-units` | List all supported units |

**Fetch BOM Response:**
```json
{
  "status": "success",
  "data": {
    "type": "Assembly",
    "bomTable": {
      "items": [
        {
          "item": 1,
          "partNumber": "PART-001",
          "name": "Main Body",
          "quantity": 1,
          "description": "Assembly component"
        }
      ]
    }
  }
}
```

### Parts Routes (`/api/parts`)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/scan-partstudio?...` | Scan all parts in PartStudio |
| GET | `/scan-assembly?...` | Scan all components in Assembly |
| GET | `/bounding-boxes?...` | Get bounding boxes for parts |
| GET | `/part-metadata?...` | Get metadata for specific part |
| GET | `/search?query=xxx&...` | Search parts by name/ID |

**Part Metadata Response:**
```json
{
  "status": "success",
  "data": {
    "partId": "part-id",
    "properties": [
      {
        "name": "Length",
        "value": "100",
        "propertyId": "57f3fb8efa3416c06701d60d"
      }
    ],
    "propertyCount": 1
  }
}
```

### Metadata Routes (`/api/metadata`)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/get?doc_id=xxx&...&part_id=xxx&user_id=xxx` | Get part metadata |
| POST | `/update` | Update custom properties for part |
| POST | `/batch-update` | Update multiple parts |
| GET | `/health` | Health check |

**Update Metadata:**
```json
POST /api/metadata/update
{
  "user_id": "user-id",
  "doc_id": "doc-id",
  "workspace_id": "workspace-id",
  "element_id": "element-id",
  "part_id": "part-id",
  "updates": {
    "propertyId_123": "100",
    "propertyId_456": "Aluminum"
  }
}
```

### User Routes (`/api/user`)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/info?user_id=xxx` | Get user information |

---

## OnShape API Integration

### Core Concepts

**Document Structure:**
- **Document ID (did):** Unique identifier for entire document
- **Workspace ID (wid):** Current working area
- **Element ID (eid):** Individual component (Assembly or PartStudio)
- **Part ID (pid):** Specific part within element
- **Microversion:** Automatic snapshot on each change

### Main OnShape Endpoints Used

#### 1. Get Documents
```
GET /api/documents
Headers: Authorization: Bearer {token}
```

#### 2. Get BOM (Assembly)
```
GET /api/assemblies/d/{did}/w/{wid}/e/{eid}/bom
Headers: Authorization: Bearer {token}
Params: indented=true|false
```

#### 3. Get Parts (PartStudio)
```
GET /api/parts/d/{did}/w/{wid}/e/{eid}
Headers: Authorization: Bearer {token}
```

#### 4. Get Bounding Boxes
```
GET /api/partstudios/d/{did}/w/{wid}/e/{eid}/boundingboxes
Headers: Authorization: Bearer {token}
Timeout: 120 seconds (large documents)
```

**Bounding Box Response:**
```json
{
  "lowX": -50.5,
  "lowY": -25.0,
  "lowZ": 0,
  "highX": 50.5,
  "highY": 25.0,
  "highZ": 100.0,
  "partId": "part-123"
}
```

Dimensions (mm): `Length = (highX - lowX) × 1000`, etc.

#### 5. Get Metadata
```
GET /api/metadata/d/{did}/w/{wid}/e/{eid}/p/{pid}
Headers: Authorization: Bearer {token}
Response: 404 if no custom properties exist (normal)
```

#### 6. Update Metadata
```
POST /api/metadata/d/{did}/w/{wid}/e/{eid}/p/{pid}
Headers: Authorization: Bearer {token}
Body: {
  "jsonType": "metadata-part",
  "partId": "{pid}",
  "properties": [
    {
      "value": "100",
      "propertyId": "propertyId_123"
    }
  ]
}
```

### Key Implementation Notes

**Token Management:**
- Tokens encrypted with Fernet symmetric encryption
- Stored in database with expiration time
- Auto-refresh not implemented (requires re-login)
- Timeout: 3600 seconds (1 hour)

**Error Handling:**
```python
try:
    response = requests.get(url, headers=headers, timeout=60)
    response.raise_for_status()
except HTTPError as e:
    logger.error(f"HTTP {e.response.status_code}: {e.response.text}")
except Timeout as e:
    logger.error(f"Request timeout: {str(e)}")
```

**Rate Limiting:**
- OnShape API: ~100 requests per second (no official limit)
- Large BOM documents: Increase timeout to 120 seconds

---

## Database Schema

### Users Table
```sql
CREATE TABLE users (
  id VARCHAR PRIMARY KEY,
  onshape_id VARCHAR UNIQUE,
  email VARCHAR UNIQUE,
  name VARCHAR,
  access_token TEXT (encrypted),
  refresh_token TEXT (encrypted),
  token_expires_at DATETIME,
  created_at DATETIME,
  last_login DATETIME,
  updated_at DATETIME
);
```

### Saved Documents Table
```sql
CREATE TABLE saved_documents (
  id VARCHAR PRIMARY KEY,
  user_id VARCHAR,
  document_id VARCHAR,
  workspace_id VARCHAR,
  element_id VARCHAR,
  element_type VARCHAR,
  document_name VARCHAR,
  element_name VARCHAR,
  bom_data JSON,
  bbox_data JSON,
  properties_data JSON,
  created_at DATETIME,
  last_used_at DATETIME,
  last_synced_at DATETIME
);
```

### BOM Cache Table
```sql
CREATE TABLE bom_cache (
  id VARCHAR PRIMARY KEY,
  user_id VARCHAR,
  document_id VARCHAR,
  element_id VARCHAR,
  bom_flat JSON,
  bom_structured JSON,
  part_count INTEGER,
  created_at DATETIME,
  cached_at DATETIME,
  expires_at DATETIME
);
```

### Property Syncs Table
```sql
CREATE TABLE property_syncs (
  id VARCHAR PRIMARY KEY,
  user_id VARCHAR,
  document_id VARCHAR,
  element_id VARCHAR,
  property_name VARCHAR,
  parts_updated INTEGER,
  errors JSON,
  status VARCHAR (pending|success|failed),
  created_at DATETIME,
  completed_at DATETIME
);
```

---

## Frontend Features

### Main Components

**1. Authentication Section**
- Login with OnShape button
- Display logged-in user email
- Logout button
- Load saved documents

**2. Document Information**
- Input fields for Document ID, Workspace ID, Element ID
- Buttons to fetch documents and elements
- Save documents for quick access

**3. Data Operations**
- **BOM:** Flattened or structured format, editable cells
- **Bounding Boxes:** View and edit dimensions
- **Configuration Variables:** View variables from PartStudios
- **Length Properties:** Auto-generate from bounding boxes

**4. Part Scanner (Experimental)**
- Scan PartStudio parts
- Scan Assembly components
- Search parts by name/ID/material
- View part metadata
- Export as JSON/CSV

**5. Unit Conversion**
- Convert between mm, cm, m, in, ft, yd, µm
- Calculate volumes (mm³)
- Add dimensions to BOM with formula

**6. File Operations**
- Upload JSON/CSV files
- Edit table cells inline
- Download as JSON/CSV

### Supported Units for Conversion

| Unit | Code | Factor (to mm) |
|------|------|----------------|
| Millimeter | mm | 1.0 |
| Centimeter | cm | 10.0 |
| Meter | m | 1000.0 |
| Inch | in | 25.4 |
| Foot | ft | 304.8 |
| Yard | yd | 914.4 |
| Micrometer | µm | 0.001 |

### Editable Table Features

```javascript
// Click any cell to edit
// Data automatically saves on blur
// Supports: BOM, Bounding Boxes, Variables, Generic data

// Example: Edit part number
<td class="editable-cell" 
    contenteditable="true" 
    data-row="0" 
    data-field="partNumber" 
    data-type="bom">
  PART-001
</td>
```

---

## Known Issues & Fixes

### Issue 1: Token Expiration
**Status:** ⚠️ Active  
**Description:** Access tokens expire after 1 hour; no auto-refresh  
**Workaround:** Re-login when token expires  
**Fix:** Implement refresh token flow (future)

### Issue 2: Metadata Push Failures
**Status:** ⚠️ Partial  
**Description:** Cannot update certain read-only properties (Material, Mass)  
**Cause:** OnShape API restrictions on enterprise features  
**Workaround:** Only update custom string properties  
**Note:** Free plan may have more restrictions

### Issue 3: Properties Not Visible
**Status:** ⚠️ Investigating  
**Description:** Custom properties sometimes not returned by OnShape API  
**Cause:** May require enterprise plan or specific setup  
**Investigation:** Check OnShape API Explorer for property IDs

### Issue 4: Bounding Box 404 for Assemblies
**Status:** ✅ Fixed  
**Description:** `/boundingboxes` endpoint returns 404 for Assemblies  
**Solution:** Falls back to `/parts` endpoint which works for both

### Issue 5: Large BOM Timeout
**Status:** ✅ Fixed  
**Description:** BOM fetch timeouts for large assemblies  
**Solution:** Increased timeout from 30s → 120s

### Issue 6: JavaScript Syntax Errors
**Status:** ✅ Fixed (v27)  
**Description:** Button clicks not working due to syntax errors  
**Solution:** Cleaned up event listener bindings, separated files

### Issue 7: Response Time
**Status:** ⚠️ Investigating  
**Description:** Average response time ~1250ms, ideal is 100-500ms  
**Cause:** OnShape API slowness + network latency  
**Optimization:** May add caching layer

---

## Development Timeline

### Phase 1: Setup (27.10 - 13.11.2025)
- ✅ Project structure created
- ✅ Basic frontend HTML
- ✅ OAuth2 integration started
- ⚠️ Token exchange issues

### Phase 2: Authentication (13.11 - 21.11.2025)
- ✅ Token encryption implemented
- ✅ Database setup (SQLAlchemy)
- ✅ User saving/retrieval
- ✅ Tokens working for 1 hour

### Phase 3: BOM Features (21.11 - 28.11.2025)
- ✅ BOM fetching (Assembly)
- ✅ BOM fetching fallback (PartStudio)
- ✅ Bounding box retrieval
- ✅ CSV/JSON export
- ⚠️ JavaScript syntax errors

### Phase 4: Improvements (28.11 - 05.12.2025)
- ✅ Code cleanup and refactoring
- ✅ Unit conversion service
- ✅ Editable table cells
- ✅ Parts scanner
- ⚠️ Metadata push still incomplete

### Phase 5: Metadata (05.12 - 09.12.2025)
- ✅ Metadata endpoints created
- ✅ GET metadata working
- ⚠️ POST metadata partially working
- ✅ Part scanning functional
- 🔄 Testing with enterprise plan needed

---

## Future Improvements

### High Priority
1. **Token Refresh:**
   - Implement refresh token flow
   - Auto-refresh before expiration
   - Prevent forced re-login

2. **Metadata Push:**
   - Full support for custom properties
   - Batch update optimization
   - Validation before push

3. **Configuration Variables:**
   - Sync variables to BOM
   - Create derived properties
   - Support complex expressions

### Medium Priority
4. **Caching:**
   - Redis cache for large BOMs
   - 5-minute cache expiration
   - Cache invalidation on changes

5. **Webhooks:**
   - Listen for OnShape changes
   - Auto-sync properties
   - Real-time notifications

6. **UI Improvements:**
   - Dark mode
   - Mobile responsive design
   - Drag-drop file upload

### Low Priority
7. **FeatureScript:**
   - Execute custom scripts
   - Automate property calculations
   - Complex transformations

8. **Multi-language:**
   - Support for EU languages
   - Localization framework

9. **Performance:**
   - Pagination for large BOMs
   - Lazy loading
   - WebSocket for real-time updates

---

## Testing Checklist

### Manual Testing (Before Release)

- [ ] Login with OnShape works
- [ ] Can fetch documents list
- [ ] Can fetch BOM from Assembly
- [ ] Can fetch BOM from PartStudio
- [ ] BOM displays correctly (flat/structured)
- [ ] Bounding boxes show correct dimensions
- [ ] Unit conversion works for all units
- [ ] Can add dimensions to BOM
- [ ] Can export as JSON/CSV
- [ ] Can import JSON/CSV
- [ ] Part scanner finds all parts
- [ ] Part metadata displays
- [ ] Can update custom properties
- [ ] Logout works
- [ ] Error messages are clear
- [ ] Timeout handling works (>2min response)

### API Testing

```bash
# Test without authentication
curl https://api.onrender.com/api/documents/list

# Test with token
curl -H "Authorization: Bearer TOKEN" \
  https://api.onrender.com/api/documents/list

# Test metadata endpoint
curl -H "Authorization: Bearer TOKEN" \
  "https://api.onrender.com/api/metadata/get?doc_id=xxx&part_id=xxx"
```

---

## Support & Contact

**Created by:** Aleks Ņikitins  
**Internship Period:** 27.10.2025 - 15.12.2025  
**Company:** Mechanika Engineering  
**School:** Valmieras Tehnikums  

**GitHub Repository:** https://github.com/AleksNikitins/OnShape_Server_API  
**Render Deployment:** https://onshape-server-api.onrender.com/  

**Related Documentation:**
- [OnShape API Explorer](https://cad.onshape.com/glassworks/explorer/)
- [OnShape Integration Guide](https://onshape-public.github.io/docs/tutorials/sync/)
- [OAuth2 Documentation](https://cad.onshape.com/appstore/dev-portal)

---

**Last Updated:** 09.12.2025  
**Status:** Active - Version 2.1.0