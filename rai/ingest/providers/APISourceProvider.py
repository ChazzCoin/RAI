from abc import abstractmethod

import requests
import threading
import json
from typing import Dict, Any, Optional, Callable

# Central registry to hold all API endpoints
API_REGISTRY: Dict[str, Dict[str, Any]] = {}


def register_api_group(group_name: str):
    def decorator(func: Callable[[], Dict[str, Any]]):
        API_REGISTRY[group_name] = func()
        return func  # Returns the function unmodified

    return decorator


API_PROVIDER_REGISTRY = {}

def register_api_provider(name: str):
    def decorator(cls):
        API_PROVIDER_REGISTRY.setdefault(name, []).append(cls)
        return cls
    return decorator



class APIDataLoader:
    lock = threading.Lock()

    @abstractmethod
    def base_url(self) -> str: pass
    @abstractmethod
    def main_endpoint(self) -> str: pass
    @abstractmethod
    def endpoints(self) -> dict: pass
    @abstractmethod
    def get_endpoint(self, endpoint) -> dict: pass

    @classmethod
    def get_registry(cls, name: str) -> Dict[str, Any]:
        """Retrieves registered API endpoints for a group."""
        return API_PROVIDER_REGISTRY.get(name, {})

    @classmethod
    def execute(cls, name: str, endpoint: str=None, custom_params: Optional[Dict[str, Any]] = None):
        self = API_PROVIDER_REGISTRY.get(name)[0]()

        if name == 'group':
            return self.run_group(endpoint)

        api_details = self.get_endpoint(endpoint)
        if not api_details:
            raise ValueError(f"API command '{endpoint}' not found in group '{name}'")

        return self.run(api_details, custom_params)

    def run(self, api_details: Dict[str, Any], custom_params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Executes a single API request.

        :param api_details: The API configuration from the registry.
        :param custom_params: Optional parameters to override.
        :return: API response data.
        """
        method = api_details["method"].upper()
        url = api_details["url"]
        headers = api_details.get("headers", {})
        params = api_details.get("params", {})
        json_data = api_details.get("json", {})

        # Override default parameters if provided
        if custom_params:
            params.update(custom_params)

        with self.lock:  # Ensuring thread safety
            try:
                if method == "GET":
                    response = requests.get(url, headers=headers, params=params, timeout=10)
                elif method == "POST":
                    response = requests.post(url, headers=headers, json=json_data, timeout=10)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                return {"error": str(e)}

    def run_group(self, name: str) -> Dict[str, Any]:
        """Executes all API calls within a group and returns results."""
        results = {}
        try:
            for key, api_details in self.get_registry(name).items():
                try:
                    results[key] = self.run(api_details)
                except Exception as e:
                    results[key] = {"error": str(e)}
            return results
        except Exception as e:
            return {"error": str(e)}


@register_api_provider("cerner")
class CernerProvider(APIDataLoader):
    """FHIR API Configuration for Cerner"""
    def base_url(self) -> str:
        return "https://fhir-open.cerner.com/r4/ec2458f2-1e24-41c8-b71b-0e701af7583d"

    def main_endpoint(self): return 'schedule_by_id'

    def get_endpoint(self, endpoint: str=None) -> dict:
        if endpoint is None: return self.endpoints()[self.main_endpoint()]
        return self.endpoints()[endpoint]

    def endpoints(self) -> dict:
        return {
            "schedule_by_id": {
                "url": f"{self.base_url()}/Schedule",
                "method": "GET",
                "params": {"_id": "24477854-21304876-62852027-0"},
                "headers": {
                    "Accept": "application/fhir+json",
                    "Content-Type": "application/fhir+json"
                }
            }
        }
# Example Usage
if __name__ == "__main__":
    # print("Fetching News Headlines...")
    # news_data = APIDataLoader.execute('news', 'top_headlines')
    # print(json.dumps(news_data, indent=4))

    print("\nFetching Cerner Data...")
    stock_data = APIDataLoader.execute('cerner')
    print(json.dumps(stock_data, indent=4))
    #
    # print("\nRunning All GraphQL Requests...")
    # graphql_data = APIDataLoader.execute('group', 'graphql_example')
    # print(json.dumps(graphql_data, indent=4))
