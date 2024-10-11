import requests
from F import DICT
from rdflib.plugins.sparql.parserutils import prettify_parsetree

url = "https://fhir-open.cerner.com/r4/ec2458f2-1e24-41c8-b71b-0e701af7583d/Schedule?_id=24477854-21304876-62852027-0"


headers = {
    "Accept": "application/fhir+json",
    "Content-Type": "application/fhir+json"
}

data = {
    "active": True
}

response = requests.get(url, data=data, headers=headers)

if response.status_code == 200:

    data = response.json()
    for k in data:
        print(f"Key: {k} | Value: {data[k]}")  # or handle the data as needed
    entries = data.get("entry", [])
    print("\n")
    for item in entries:
        print(item)
else:
    print(f"Failed to retrieve data: {response.text}")



