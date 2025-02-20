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


# Register API Endpoints (Example APIs)
@register_api_group("news")
def news_api_endpoints():
    return {
        "top_headlines": {
            "url": "https://newsapi.org/v2/top-headlines",
            "method": "GET",
            "params": {"country": "us", "category": "technology"},
            "headers": {"Authorization": "Bearer YOUR_NEWS_API_KEY"}
        },
        "everything": {
            "url": "https://newsapi.org/v2/everything",
            "method": "GET",
            "params": {"q": "AI"},
            "headers": {"Authorization": "Bearer YOUR_NEWS_API_KEY"}
        }
    }


@register_api_group("stocks")
def stocks_api_endpoints():
    return {
        "market_summary": {
            "url": "https://query1.finance.yahoo.com/v7/finance/quote",
            "method": "GET",
            "params": {"symbols": "AAPL,MSFT,GOOG"}
        },
        "historical_data": {
            "url": "https://query1.finance.yahoo.com/v8/finance/chart/AAPL",
            "method": "GET",
            "params": {"interval": "1d", "range": "1mo"}
        }
    }


@register_api_group("graphql_example")
def graphql_api_endpoints():
    return {
        "fetch_user": {
            "url": "https://api.example.com/graphql",
            "method": "POST",
            "json": {
                "query": """query { user(id: "123") { name, email, posts { title } } }"""
            },
            "headers": {"Authorization": "Bearer YOUR_API_TOKEN"}
        }
    }

@register_api_group("cerner")
def cerner_api_endpoints():
    """FHIR API Configuration for Cerner"""
    base_url = "https://fhir-open.cerner.com/r4/ec2458f2-1e24-41c8-b71b-0e701af7583d"

    return {
        "schedule_by_id": {
            "url": f"{base_url}/Schedule",
            "method": "GET",
            "params": {"_id": "24477854-21304876-62852027-0"},
            "headers": {
                "Accept": "application/fhir+json",
                "Content-Type": "application/fhir+json"
            }
        }
    }

class APIDataLoader:
    lock = threading.Lock()

    @classmethod
    def get_registry(cls, name: str) -> Dict[str, Any]:
        """Retrieves registered API endpoints for a group."""
        return API_REGISTRY.get(name, {})

    @classmethod
    def execute(cls, group: str, command: str, custom_params: Optional[Dict[str, Any]] = None):
        """
        Executes an API request based on the registry.

        :param group: The API group name (e.g., 'news', 'stocks').
        :param command: The specific API request to execute.
        :param custom_params: Optional parameters to override defaults.
        :return: API response data.
        """
        self = cls()

        if group == 'group':
            return self.run_group(command)

        api_details = self.get_registry(group).get(command, None)
        if not api_details:
            raise ValueError(f"API command '{command}' not found in group '{group}'")

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


# Example Usage
if __name__ == "__main__":
    # print("Fetching News Headlines...")
    # news_data = APIDataLoader.execute('news', 'top_headlines')
    # print(json.dumps(news_data, indent=4))

    print("\nFetching Cerner Data...")
    stock_data = APIDataLoader.execute('cerner', 'schedule_by_id')
    print(json.dumps(stock_data, indent=4))
    #
    # print("\nRunning All GraphQL Requests...")
    # graphql_data = APIDataLoader.execute('group', 'graphql_example')
    # print(json.dumps(graphql_data, indent=4))
