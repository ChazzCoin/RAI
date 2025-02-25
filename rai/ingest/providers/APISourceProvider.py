import asyncio
from abc import abstractmethod
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable, List

import httpx

# -------------------------------
# Provider & Group Registries
# -------------------------------

API_REGISTRY: Dict[str, Dict[str, Any]] = {}

def register_api_group(group_name: str):
    def decorator(func: Callable[[], Dict[str, Any]]):
        API_REGISTRY[group_name] = func()
        return func  # Returns the function unmodified
    return decorator

API_PROVIDER_REGISTRY: Dict[str, List[type]] = {}

def register_api_provider(name: str):
    def decorator(cls):
        API_PROVIDER_REGISTRY.setdefault(name, []).append(cls)
        return cls
    return decorator

# -------------------------------
# Optimized Base Provider (Async)
# -------------------------------

class BaseAPIProvider:
    """
    Abstract base provider for asynchronous API calls,
    error handling, and pipelining.
    """
    client: httpx.AsyncClient = httpx.AsyncClient(timeout=10)

    @abstractmethod
    def base_url(self) -> str:
        pass

    @abstractmethod
    def api_key(self) -> str:
        pass

    @abstractmethod
    def main_endpoint(self) -> str:
        pass

    @abstractmethod
    def endpoints(self) -> dict:
        pass

    @abstractmethod
    def get_endpoint(self, endpoint: str, **kwargs) -> dict:
        pass

    @staticmethod
    def date_now() -> str:
        return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    async def execute_request(self, endpoint_config: Dict[str, Any], custom_params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Asynchronously executes a single API request.
        """
        method = endpoint_config.get("method", "GET").upper()
        url = endpoint_config.get("url")
        headers = endpoint_config.get("headers", {})
        params = endpoint_config.get("params", {}).copy()  # Copy to avoid side effects
        json_data = endpoint_config.get("json", {})

        if custom_params:
            params.update(custom_params)

        try:
            response = await self.client.request(method, url, headers=headers, params=params, json=json_data)
            response.raise_for_status()
            # Optionally, add retry logic here for transient errors.
            return response.json()
        except httpx.RequestError as exc:
            return {"error": f"An error occurred while requesting {exc.request.url}: {exc}"}
        except httpx.HTTPStatusError as exc:
            return {"error": f"HTTP error {exc.response.status_code} while requesting {exc.request.url}"}

    async def pipeline(self, endpoints: List[tuple]) -> Dict[str, Any]:
        """
        Executes multiple API calls concurrently and returns a dictionary
        with keys mapped to their corresponding results.
        """
        tasks = {key: asyncio.create_task(self.execute_request(ep)) for key, ep in endpoints}
        results = {}
        for key, task in tasks.items():
            results[key] = await task
        return results

    @classmethod
    async def execute(cls, provider_name: str, endpoint: str = None, custom_params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Class method to instantiate the first registered provider for the given name
        and execute the specified endpoint.
        """
        provider_cls = API_PROVIDER_REGISTRY.get(provider_name, [None])[0]
        if provider_cls is None:
            raise ValueError(f"No provider registered with name '{provider_name}'")
        instance = provider_cls()
        # For group requests, you could handle them here.
        api_details = instance.get_endpoint(endpoint, **(custom_params or {}))
        if not api_details:
            raise ValueError(f"Endpoint '{endpoint}' not found in provider '{provider_name}'")
        return await instance.execute_request(api_details, custom_params)

# -------------------------------
# Example Providers
# -------------------------------

@register_api_provider("cerner")
class CernerProvider(BaseAPIProvider):
    """FHIR API Configuration for Cerner"""
    def base_url(self) -> str:
        return "https://fhir-open.cerner.com/r4/ec2458f2-1e24-41c8-b71b-0e701af7583d"

    def api_key(self) -> str:
        return "<CERNER_API_KEY>"

    def main_endpoint(self) -> str:
        return "schedule_by_id"

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

    def get_endpoint(self, endpoint: str = None, **kwargs) -> dict:
        if endpoint is None:
            endpoint = self.main_endpoint()
        return self.endpoints().get(endpoint, {})

@register_api_provider("congress")
class CongressProvider(BaseAPIProvider):
    """Congress API Configuration for retrieving bill data."""
    def api_key(self) -> str:
        return "bZPawMlkJnoj7VnvGzVNgmZoTeafdqjxA03Xpwqr"

    def base_url(self) -> str:
        return "https://api.congress.gov/v3"

    def main_endpoint(self) -> str:
        return "bill"

    def endpoints(self) -> dict:
        return {
            "bill": {
                "url": f"{self.base_url()}/bill",
                "method": "GET",
                "params": {
                    "api_key": self.api_key(),
                    "format": "json",
                    "limit": 5,
                },
                "headers": {
                    "Accept": "application/json",
                    "Content-Type": "application/json"
                }
            },
            "latest": {
                "url": f"{self.base_url()}/bill",
                "method": "GET",
                "params": {
                    "api_key": self.api_key(),
                    "format": "json",
                    "limit": 5,
                    "sort": "updateDate+desc",
                    "toDateTime": self.date_now(),
                },
                "headers": {
                    "Accept": "application/json",
                    "Content-Type": "application/json"
                }
            }
        }

    def get_endpoint(self, endpoint: str = None, **kwargs) -> dict:
        if endpoint is None:
            endpoint = self.main_endpoint()
        return self.endpoints().get(endpoint, {})

@register_api_provider("patents")
class PatentsProvider(BaseAPIProvider):
    """Patents API Configuration for retrieving USPTO patent data."""
    def api_key(self) -> str:
        return "<PATENTS_API_KEY>"

    def base_url(self) -> str:
        return "https://developer.uspto.gov/ibd-api/v2/application"

    def main_endpoint(self) -> str:
        return "by_date_range"

    def endpoints(self) -> dict:
        # This provider uses dynamic endpoints; static endpoints are minimal.
        return {}

    def get_endpoint(self, endpoint: str = None, **kwargs) -> dict:
        # For dynamic endpoints, generate the config on the fly.
        if endpoint is None or endpoint == self.main_endpoint():
            patent_type = kwargs.get("patent_type", "publications")
            last_n_months = kwargs.get("last_n_months", 24)
            end_date = datetime.today()
            start_date = end_date - timedelta(days=last_n_months * 30)
            return {
                "url": f"{self.base_url()}/{patent_type}",
                "method": "GET",
                "params": {
                    "filingDateFromDate": start_date.strftime('%Y-%m-%d'),
                    "filingDateToDate": end_date.strftime('%Y-%m-%d'),
                    "start": 300,
                    "rows": 100
                },
                "headers": {
                    "Accept": "application/json"
                }
            }
        elif endpoint == "download_pdf":
            pdf_url = kwargs.get("url")
            if not pdf_url:
                raise ValueError("download_pdf endpoint requires a 'url' parameter.")
            return {
                "url": pdf_url,
                "method": "GET",
                "headers": {
                    "Accept": "application/pdf"
                }
            }
        return {}

# -------------------------------
# Example Usage (Async)
# -------------------------------

async def main():
    print("Fetching Congress Latest Data...")
    data = await BaseAPIProvider.execute("patents")
    print(data)

    # print("\nFetching USPTO Patents Data (Last 12 Months)...")
    # patents_provider = PatentsProvider()
    # patents_endpoint = patents_provider.get_endpoint("by_date_range", patent_type="publications", last_n_months=12)
    # patents_data = await patents_provider.execute_request(patents_endpoint)
    # print(patents_data)
    #
    # # Example of pipelined calls:
    # print("\nExecuting Pipelined Requests...")
    # # Define endpoints to call concurrently. The keys are arbitrary.
    # pipeline_endpoints = [
    #     ("congress_bill", CongressProvider().get_endpoint("bill")),
    #     ("congress_latest", CongressProvider().get_endpoint("latest"))
    # ]
    # congress_provider = CongressProvider()
    # pipeline_results = await congress_provider.pipeline(pipeline_endpoints)
    # print(pipeline_results)

if __name__ == "__main__":
    asyncio.run(main())
