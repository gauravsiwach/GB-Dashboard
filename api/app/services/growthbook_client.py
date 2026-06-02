import httpx
import os
import logging
import json
from typing import Optional, Dict, Any
from app.services.growthbook_error import GrowthBookError

logger = logging.getLogger(__name__)

GROWTHBOOK_API_KEY = os.getenv("GROWTHBOOK_API_KEY")
GROWTHBOOK_BASE_URL = os.getenv("GROWTHBOOK_BASE_URL")
GROWTHBOOK_PROJECT_ID = os.getenv("GROWTHBOOK_PROJECT_ID")


class GrowthBookClient:
    """Async client for GrowthBook API operations."""
    
    def __init__(self):
        if not GROWTHBOOK_API_KEY or not GROWTHBOOK_BASE_URL:
            raise ValueError("GROWTHBOOK_API_KEY and GROWTHBOOK_BASE_URL must be set")
        
        self.api_key = GROWTHBOOK_API_KEY
        self.base_url = GROWTHBOOK_BASE_URL.rstrip('/')
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
    
    async def _request(self, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make an async HTTP request to GrowthBook API."""
        url = f"{self.base_url}{endpoint}"
        
        async with httpx.AsyncClient() as client:
            try:
                if method == "GET":
                    response = await client.get(url, headers=self.headers)
                elif method == "POST":
                    response = await client.post(url, headers=self.headers, json=data)
                elif method == "PUT":
                    response = await client.put(url, headers=self.headers, json=data)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                response.raise_for_status()
                return response.json()
            
            except httpx.HTTPStatusError as e:
                logger.info(f"HTTP error {e.response.status_code} for {method} {url}: {e.response.text}")
                raise GrowthBookError(
                    message=f"HTTP error: {e.response.status_code}",
                    status_code=e.response.status_code,
                    response_data=e.response.json() if e.response.content else None
                )
            except httpx.RequestError as e:
                raise GrowthBookError(message=f"Request error: {str(e)}")
            except Exception as e:
                raise GrowthBookError(message=f"Unexpected error: {str(e)}")
    
    async def get_feature(self, feature_id: str) -> Dict[str, Any]:
        """Get a feature from GrowthBook by ID."""
        logger.info(f"GET request to /v2/features/{feature_id}")
        response = await self._request("GET", f"/v2/features/{feature_id}")
        logger.info(f"GET /v2/features/{feature_id} response: {response}")
        return response
    
    async def get_all_features(self) -> Dict[str, Any]:
        """Get all features from GrowthBook (optionally filtered by configured project)."""
        params = {}
        if GROWTHBOOK_PROJECT_ID:
            params["projectId"] = GROWTHBOOK_PROJECT_ID
            logger.info(f"Filtering features by project_id: {GROWTHBOOK_PROJECT_ID}")
        
        async with httpx.AsyncClient() as client:
            try:
                url = f"{self.base_url}/v2/features"
                response = await client.get(url, headers=self.headers, params=params)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                raise GrowthBookError(
                    message=f"HTTP error: {e.response.status_code}",
                    status_code=e.response.status_code,
                    response_data=e.response.json() if e.response.content else None
                )
            except httpx.RequestError as e:
                raise GrowthBookError(message=f"Request error: {str(e)}")
            except Exception as e:
                raise GrowthBookError(message=f"Unexpected error: {str(e)}")
    
    async def create_feature(self, feature_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new feature in GrowthBook."""
        async with httpx.AsyncClient() as client:
            try:
                url = f"{self.base_url}/v2/features"
                response = await client.post(url, headers=self.headers, json=feature_data)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                raise GrowthBookError(
                    message=f"HTTP error: {e.response.status_code}",
                    status_code=e.response.status_code,
                    response_data=e.response.json() if e.response.content else None
                )
            except httpx.RequestError as e:
                raise GrowthBookError(message=f"Request error: {str(e)}")
            except Exception as e:
                raise GrowthBookError(message=f"Unexpected error: {str(e)}")
    
    async def update_feature(self, feature_id: str, feature_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing feature in GrowthBook."""
        logger.info(f"PUT request to /v2/features/{feature_id}")
        logger.info(f"PUT request body: {feature_data}")
        response = await self._request("PUT", f"/v2/features/{feature_id}", feature_data)
        logger.info(f"PUT /v2/features/{feature_id} response: {response}")
        return response
    
    async def toggle_feature(self, feature_id: str, environments: Dict[str, bool], reason: str = "") -> Dict[str, Any]:
        """Toggle a feature in one or more environments."""
        payload = {
            "environments": environments,
            "reason": reason
        }
        logger.info(f"POST request to /v2/features/{feature_id}/toggle")
        logger.info(f"POST request body: {payload}")
        response = await self._request("POST", f"/v2/features/{feature_id}/toggle", payload)
        logger.info(f"POST /v2/features/{feature_id}/toggle response: {response}")
        return response
    
    async def update_feature_environment(self, feature_id: str, environment: str, enabled: bool, default_value: str = "false") -> Dict[str, Any]:
        """Update a feature's configuration for a specific environment using correct endpoints."""
        # Get current feature state to compare
        current_feature = await self._request("GET", f"/v2/features/{feature_id}")
        
        # Extract current values
        current_env = current_feature.get("environments", {}).get(environment, {})
        current_enabled = current_env.get("enabled", False)
        current_default = current_env.get("defaultValue", "false")
        
        # Determine what changed
        enabled_changed = current_enabled != enabled
        default_changed = current_default != default_value
        
        # Use correct endpoints based on operation type
        if enabled_changed and default_changed:
            # Both changed - use POST call with correct schema: environments for enabled, top-level for defaultValue
            # Prepare environments with only enabled (defaultValue not allowed here)
            if "environments" not in current_feature:
                current_feature["environments"] = {}
            if environment not in current_feature["environments"]:
                current_feature["environments"][environment] = {}
                
            current_feature["environments"][environment]["enabled"] = enabled
            
            # Update defaultValue at top level - use plain string format like working example
            # The working format is: "defaultValue": "{'id': 'testid', 'value': '1234', 'value1': '1234'}"
            if isinstance(default_value, str):
                # If it's already in the correct format with single quotes, use as-is
                if default_value.startswith("{") and "'" in default_value:
                    formatted_default_value = default_value
                else:
                    # Convert JSON string to single-quoted format
                    try:
                        parsed_value = json.loads(default_value)
                        # Build the single-quoted string manually
                        if isinstance(parsed_value, dict):
                            items = [f"'{k}': '{v}'" for k, v in parsed_value.items()]
                            formatted_default_value = "{" + ", ".join(items) + "}"
                        else:
                            formatted_default_value = f"'{parsed_value}'"
                    except json.JSONDecodeError:
                        # If parsing fails, wrap with single quotes
                        formatted_default_value = f"'{default_value}'"
            else:
                # Convert non-string to single quotes format
                formatted_default_value = f"'{default_value}'"
            
            current_feature["defaultValue"] = formatted_default_value
            
            # Manually construct the JSON payload to match the exact working format
            env_json = json.dumps(current_feature["environments"])
            payload_json = f'{{"environments": {env_json}, "defaultValue": "{formatted_default_value}"}}'
            
            # Parse the manual JSON back to dict for the request
            update_payload = json.loads(payload_json)
            
            response = await self._request("POST", f"/v2/features/{feature_id}", update_payload)
            
        elif enabled_changed:
            # Only enabled changed - use toggle endpoint (correct for on/off operations)
            payload = {
                "environments": {environment: enabled},
                "reason": f"Updated via dashboard - enabled={enabled}"
            }
            response = await self._request("POST", f"/v2/features/{feature_id}/toggle", payload)
            
        elif default_changed:
            # Only default_value changed - use feature update endpoint with top-level defaultValue
            
            # Update defaultValue at top level - use plain string format like working example
            # The working format is: "defaultValue": "{'id': 'testid', 'value': '1234', 'value1': '1234'}"
            if isinstance(default_value, str):
                # If it's already in the correct format with single quotes, use as-is
                if default_value.startswith("{") and "'" in default_value:
                    formatted_default_value = default_value
                else:
                    # Convert JSON string to single-quoted format
                    try:
                        parsed_value = json.loads(default_value)
                        # Build the single-quoted string manually
                        if isinstance(parsed_value, dict):
                            items = [f"'{k}': '{v}'" for k, v in parsed_value.items()]
                            formatted_default_value = "{" + ", ".join(items) + "}"
                        else:
                            formatted_default_value = f"'{parsed_value}'"
                    except json.JSONDecodeError:
                        # If parsing fails, wrap with single quotes
                        formatted_default_value = f"'{default_value}'"
            else:
                # Convert non-string to single quotes format
                formatted_default_value = f"'{default_value}'"
            
            current_feature["defaultValue"] = formatted_default_value
            
            # Manually construct the JSON payload to match the exact working format
            payload_json = f'{{"defaultValue": "{formatted_default_value}"}}'
            
            # Parse the manual JSON back to dict for the request
            update_payload = json.loads(payload_json)
            
            response = await self._request("POST", f"/v2/features/{feature_id}", update_payload)
            
        else:
            # Nothing changed
            return current_feature
        
        return response
    
    async def archive_feature(self, feature_id: str) -> Dict[str, Any]:
        """Archive a feature in GrowthBook using the documented archive pattern."""
        payload = {"archived": True}
        logger.info(f"POST request to /v1/features/{feature_id} to archive")
        logger.info(f"POST request body: {payload}")
        response = await self._request("POST", f"/v1/features/{feature_id}", payload)
        logger.info(f"POST /v1/features/{feature_id} archive response: {response}")
        return response
    
    async def delete_feature(self, feature_id: str) -> Dict[str, Any]:
        """Delete a feature from GrowthBook."""
        return await self._request("DELETE", f"/api/features/{feature_id}")
    
    async def add_rule(self, feature_id: str, environment: str, rule_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add a rule to a feature in a specific environment."""
        # Get current feature state
        current_feature = await self._request("GET", f"/v2/features/{feature_id}")
        
        # Extract the feature data from the response (GrowthBook wraps it in a "feature" key)
        if "feature" in current_feature:
            current_feature = current_feature["feature"]
        
        # Ensure environment exists
        if "environments" not in current_feature:
            current_feature["environments"] = {}
        if environment not in current_feature["environments"]:
            current_feature["environments"][environment] = {}
        
        # Remove definition string so GrowthBook uses rules array
        if "definition" in current_feature["environments"][environment]:
            del current_feature["environments"][environment]["definition"]
        
        # Add rule to global rules array with environment specification
        if "rules" not in current_feature:
            current_feature["rules"] = []
        
        # Add environment to the rule's environments array if not present
        if "environments" not in rule_data:
            rule_data["environments"] = []
        if environment not in rule_data["environments"]:
            rule_data["environments"].append(environment)
        
        current_feature["rules"].append(rule_data)
        
        # Filter the payload to only include editable fields that GrowthBook accepts
        update_payload = {
            "description": current_feature.get("description", ""),
            "defaultValue": current_feature.get("defaultValue"),
            "environments": current_feature.get("environments", {}),
            "rules": current_feature.get("rules", []),
            "prerequisites": current_feature.get("prerequisites", []),
            "tags": current_feature.get("tags", []),
            "customFields": current_feature.get("customFields", {})
        }
        
        # Update feature with new rule
        logger.info(f"Adding rule to feature {feature_id} in environment {environment}")
        response = await self._request("POST", f"/v2/features/{feature_id}", update_payload)
        logger.info(f"Rule added successfully")
        return response
    
    async def update_rule(self, feature_id: str, environment: str, rule_index: int, rule_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing rule in a feature's environment."""
        # Get current feature state
        current_feature = await self._request("GET", f"/v2/features/{feature_id}")
        
        # Ensure environment and rules exist
        if "environments" not in current_feature:
            raise GrowthBookError(message=f"Environment {environment} not found in feature")
        if environment not in current_feature["environments"]:
            raise GrowthBookError(message=f"Environment {environment} not found in feature")
        if "rules" not in current_feature["environments"][environment]:
            raise GrowthBookError(message=f"No rules found in environment {environment}")
        if rule_index >= len(current_feature["environments"][environment]["rules"]):
            raise GrowthBookError(message=f"Rule index {rule_index} out of bounds")
        
        # Update rule at specified index
        current_feature["environments"][environment]["rules"][rule_index] = rule_data
        
        # Update feature with modified rule
        logger.info(f"Updating rule {rule_index} in feature {feature_id} environment {environment}")
        response = await self._request("POST", f"/v2/features/{feature_id}", current_feature)
        logger.info(f"Rule updated successfully")
        return response
    
    async def delete_rule(self, feature_id: str, environment: str, rule_index: int) -> Dict[str, Any]:
        """Delete a rule from a feature's environment."""
        # Get current feature state
        current_feature = await self._request("GET", f"/v2/features/{feature_id}")
        
        # Ensure environment and rules exist
        if "environments" not in current_feature:
            raise GrowthBookError(message=f"Environment {environment} not found in feature")
        if environment not in current_feature["environments"]:
            raise GrowthBookError(message=f"Environment {environment} not found in feature")
        if "rules" not in current_feature["environments"][environment]:
            raise GrowthBookError(message=f"No rules found in environment {environment}")
        if rule_index >= len(current_feature["environments"][environment]["rules"]):
            raise GrowthBookError(message=f"Rule index {rule_index} out of bounds")
        
        # Delete rule at specified index
        del current_feature["environments"][environment]["rules"][rule_index]
        
        # Update feature without the deleted rule
        logger.info(f"Deleting rule {rule_index} from feature {feature_id} environment {environment}")
        response = await self._request("POST", f"/v2/features/{feature_id}", current_feature)
        logger.info(f"Rule deleted successfully")
        return response
