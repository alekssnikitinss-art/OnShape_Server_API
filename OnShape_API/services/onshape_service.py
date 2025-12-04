def get_bounding_boxes(self, document_id: str, workspace_id: str, element_id: str) -> List[Dict]:
        """Get bounding boxes for part studio OR assembly"""
        try:
            url = f"{settings.ONSHAPE_API_URL}/partstudios/d/{document_id}/w/{workspace_id}/e/{element_id}/boundingboxes"
            
            logger.info(f"📏 Fetching bounding boxes (timeout={self.timeout}s)...")
            logger.info(f"   URL: {url}")
            
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            
            logger.info(f"   Response status: {response.status_code}")
            
            # If PartStudio works, return it
            if response.status_code == 200:
                logger.info(f"✅ Got bounding boxes from PartStudio endpoint")
                result = response.json()
                
                # Handle different response formats
                if isinstance(result, dict):
                    if "items" in result:
                        bboxes = result["items"]
                    elif "boundingBoxes" in result:
                        bboxes = result["boundingBoxes"]
                    else:
                        bboxes = result
                elif isinstance(result, list):
                    bboxes = result
                else:
                    bboxes = []
                
                return bboxes if isinstance(bboxes, list) else [bboxes]
            
            # If PartStudio fails (400), try Assembly approach
            logger.warning(f"⚠️ PartStudio endpoint returned {response.status_code}")
            logger.info(f"🔄 Trying Assembly approach: get all parts and their bboxes...")
            
            # Get all parts in the assembly
            try:
                parts_url = f"{settings.ONSHAPE_API_URL}/parts/d/{document_id}/w/{workspace_id}/e/{element_id}"
                logger.info(f"   Fetching parts from: {parts_url}")
                
                parts_response = requests.get(parts_url, headers=self.headers, timeout=self.timeout)
                parts_response.raise_for_status()
                
                parts_data = parts_response.json()
                logger.info(f"✅ Got {len(parts_data) if isinstance(parts_data, list) else '?'} parts")
                
                # If we got parts, return them as-is
                # (Assembly parts don't have traditional bounding boxes)
                if isinstance(parts_data, list):
                    logger.info(f"📦 Returning {len(parts_data)} parts from Assembly")
                    return parts_data
                else:
                    logger.warning(f"⚠️ Parts response is not a list: {type(parts_data)}")
                    return []
                    
            except Exception as e:
                logger.error(f"❌ Assembly approach also failed: {str(e)}")
                # If both fail, raise original error
                raise HTTPError(f"Element is neither PartStudio nor accessible Assembly", response=response)
        
        except Exception as e:
            logger.error(f"❌ get_bounding_boxes error: {str(e)}")
            raise