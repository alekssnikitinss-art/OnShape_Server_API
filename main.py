@app.get("/api/partstudios/{did}/w/{wid}/e/{eid}/boundingboxes")
    async def get_bounding_boxes(did: str, wid: str, eid: str, user_id: str, db: Session = Depends(get_db)):
        token = get_user_token(user_id, db)
        url = f"https://cad.onshape.com/api/partstudios/d/{did}/w/{wid}/e/{eid}/boundingboxes"
        resp = requests.get(url, headers={"Authorization": f"Bearer {token}"})
        return JSONResponse(resp.json(), resp.status_code)

    @app.get("/api/partstudios/{did}/w/{wid}/e/{eid}/variables")
    async def get_variables(did: str, wid: str, eid: str, user_id: str, db: Session = Depends(get_db)):
        """Get configuration variables from part studio"""
        token = get_user_token(user_id, db)
        
        # First, get all parts in the part studio
        parts_url = f"https://cad.onshape.com/api/parts/d/{did}/w/{wid}/e/{eid}"
        parts_resp = requests.get(parts_url, headers={"Authorization": f"Bearer {token}"})
        
        if parts_resp.status_code != 200:
            return JSONResponse({"error": "Failed to fetch parts"}, 500)
        
        parts_data = parts_resp.json()
        variables = []
        
        # Get metadata for each part to find configuration variables
        for part in parts_data:
            part_id = part.get('partId')
            if not part_id:
                continue
            
            # Get part metadata which includes configuration info
            meta_url = f"https://cad.onshape.com/api/parts/d/{did}/w/{wid}/e/{eid}/partid/{part_id}/metadata"
            meta_resp = requests.get(meta_url, headers={"Authorization": f"Bearer {token}"})
            
            if meta_resp.status_code == 200:
                metadata = meta_resp.json()
                # Extract configuration variables from metadata
                if 'properties' in metadata:
                    for prop in metadata.get('properties', []):
                        if prop.get('name', '').startswith('#') or prop.get('propertyId', '').startswith('configuration'):
                            variables.append({
                                'name': prop.get('name', ''),
                                'value': prop.get('value', ''),
                                'unit': prop.get('unit', ''),
                                'partId': part_id,
                                'partName': part.get('name', '')
                            })
        
        # Also try to get feature variables
        features_url = f"https://cad.onshape.com/api/partstudios/d/{did}/w/{wid}/e/{eid}/features"
        features_resp = requests.get(features_url, headers={"Authorization": f"Bearer {token}"})
        
        if features_resp.status_code == 200:
            features_data = features_resp.json()
            for feature in features_data.get('features', []):
                if feature.get('message', {}).get('featureType') == 'variable':
                    params = feature.get('message', {}).get('parameters', [])
                    for param in params:
                        if 'variableName' in param:
                            variables.append({
                                'name': param.get('variableName', ''),
                                'value': param.get('expression', ''),
                                'unit': '',
                                'featureId': feature.get('featureId', ''),
                                'partId': 'Global'
                            })
        
        return JSONResponse({"variables": variables, "count": len(variables)})

    @app.post("/api/partstudios/{did}/w/{wid}/e/{eid}/sync-variables")
    async def sync_variables(did: str, wid: str, eid: str, request: Request, db: Session = Depends(get_db)):
        """Sync configuration variables to custom properties so they appear in BOM"""
        data = await request.json()
        user_id = data.get("user_id")
        variables = data.get("variables", [])
        
        if not user_id or not variables:
            raise HTTPException(400, "Missing user_id or variables")
        
        token = get_user_token(user_id, db)
        synced_count = 0
        
        # Group variables by part
        parts_vars = {}
        for var in variables:
            part_id = var.get('partId', 'Global')
            if part_id not in parts_vars:
                parts_vars[part_id] = []
            parts_vars[part_id].append(var)
        
        # For each part, update metadata with custom properties
        for part_id, part_vars in parts_vars.items():
            if part_id == 'Global':
                continue
                
            # Build metadata update payload
            properties = []
            for var in part_vars:
                properties.append({
                    "name": var.get('name', '').replace('#', ''),  # Remove # prefix
                    "value": var.get('value', ''),
                    "propertyId": "custom_" + var.get('name', '').replace('#', '').lower()
                })
            
            # Update part metadata
            meta_url = f"https://cad.onshape.com/api/metadata/d/{did}/w/{wid}/e/{eid}/p/{part_id}"
            meta_payload = {"properties": properties}
            
            meta_resp = requests.post(
                meta_url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                json=meta_payload
            )
            
            if meta_resp.status_code in [200, 201, 204]:
                synced_count += len(part_vars)
        
        return JSONResponse({
            "status": "success",
            "synced_count": synced_count,
            "message": f"Synced {synced_count} variables to custom properties. Refresh BOM to see changes."
        })