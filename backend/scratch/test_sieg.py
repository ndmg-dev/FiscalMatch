import os
import json
import urllib.request
import urllib.error

# Parse .env
api_key = None
try:
    with open("../.env", "r") as f:
        for line in f:
            if line.startswith("SIEG_API_KEY="):
                api_key = line.split("=", 1)[1].strip()
except FileNotFoundError:
    pass

if not api_key:
    print("API Key not found in .env")
    exit(1)

url1 = "https://api.sieg.com/api/Arquivos/Download"
url2 = "https://api.sieg.com/api/Arquivos/BaixarXml"

payload_1 = {
    "apikey": api_key,
    "email": "teste@sieg.com",
    "dataInicio": "2023-01-01",
    "dataFim": "2023-01-05",
    "cnpj": "00000000000000",
    "tipoXml": "nfe"
}
payload_2 = {
    "apikey": api_key,
    "email": "teste@sieg.com",
    "dataInicio": "2023-01-01",
    "dataFim": "2023-01-05",
    "cnpjEmit": "00000000000000",
    "tipoXml": "nfe"
}



def try_url(url, method="POST", json_data=None):
    try:
        data = json.dumps(json_data).encode("utf-8") if json_data else None
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=10.0) as response:
            print(f"[{method}] {url} -> Status: {response.status}")
            body = response.read().decode("utf-8")
            try:
                print("Response JSON:", json.loads(body))
            except:
                print("Response Text:", body[:500])
    except urllib.error.HTTPError as e:
        print(f"[{method}] {url} -> HTTP Error: {e.code}")
        body = e.read().decode("utf-8", errors="ignore")
        try:
            print("Response JSON:", json.loads(body))
        except:
            print("Response Text:", body[:500])
    except Exception as e:
        print(f"Error calling {url}: {e}")

print("--- TRY 1 (POST JSON cnpj) ---")
try_url(url1, "POST", payload_1)

print("--- TRY 2 (POST JSON cnpjEmit) ---")
try_url(url1, "POST", payload_2)

