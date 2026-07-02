import httpx
import re

r = httpx.get('https://api.sieg.com/swagger/', follow_redirects=True)
print('Status:', r.status_code)
if r.status_code == 200:
    matches = re.findall(r'"([^"]+\.json)"', r.text)
    print('Found JSON URLs:', matches)
    for m in matches:
        url = m if m.startswith('http') else 'https://api.sieg.com' + m
        print('Fetching:', url)
        r2 = httpx.get(url, follow_redirects=True)
        print('Status:', r2.status_code)
        if r2.status_code == 200:
            print('JSON Content:', r2.text[:200])
