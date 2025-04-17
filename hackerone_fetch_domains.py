import requests
from requests.auth import HTTPBasicAuth
import time
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Semaphore
from datetime import datetime, timedelta

# Configuration
API_USERNAME = 'your_hackerone_username'
API_TOKEN = 'your_hackerone_api_token'
STANDARD_DOMAINS_FILE = 'hackerone_standard_domains.txt'
SIMPLE_WILDCARDS_FILE = 'hackerone_simple_wildcards.txt'
WILDCARD_TLDS_FILE = 'hackerone_wildcard_tlds.txt'
PROGRAMS_CACHE_FILE = 'hackerone_programs_cache.json'
MAX_REQUESTS_PER_MINUTE = 600
RATE_LIMIT_DELAY = 60 / MAX_REQUESTS_PER_MINUTE
MAX_RETRIES = 3
PAGE_SIZE = 100
MAX_WORKERS = 10
CACHE_EXPIRY_DAYS = 30

# Rate limiter
request_semaphore = Semaphore(MAX_REQUESTS_PER_MINUTE // 60)

def is_cache_valid(cache_file):
    """Check if cache exists and is not older than CACHE_EXPIRY_DAYS"""
    if not os.path.exists(cache_file):
        return False
    
    cache_time = datetime.fromtimestamp(os.path.getmtime(cache_file))
    return (datetime.now() - cache_time) < timedelta(days=CACHE_EXPIRY_DAYS)

def make_api_request(url, params=None):
    """Thread-safe API request with strict rate limiting"""
    with request_semaphore:
        for attempt in range(MAX_RETRIES):
            try:
                response = requests.get(
                    url,
                    auth=HTTPBasicAuth(API_USERNAME, API_TOKEN),
                    headers={'Accept': 'application/json'},
                    params=params,
                    timeout=15
                )
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 10))
                    print(f"⚠️ Rate limited! Waiting {retry_after}s...")
                    time.sleep(retry_after)
                    continue
                elif response.status_code >= 400:
                    print(f"❌ Error {response.status_code} on {url}")
                    return None
                
            except Exception as e:
                print(f"⚠️ Request failed (attempt {attempt+1}): {str(e)}")
                time.sleep(RATE_LIMIT_DELAY * (attempt + 1))
        
        return None

def fetch_all_programs():
    """Fetch programs with cache validation"""
    if is_cache_valid(PROGRAMS_CACHE_FILE):
        with open(PROGRAMS_CACHE_FILE, 'r') as f:
            print("♻️ Loading programs from valid cache...")
            return json.load(f)
    
    print("🌐 Cache expired or not found, fetching fresh data...")
    base_url = "https://api.hackerone.com/v1/hackers/programs"
    programs = []
    page = 1
    
    while True:
        params = {'page[number]': page, 'page[size]': PAGE_SIZE}
        data = make_api_request(base_url, params)
        
        if not data or not data.get('data'):
            break
            
        programs.extend(data['data'])
        print(f"📥 Page {page}: {len(data['data'])} programs")
        
        if 'links' in data and 'next' in data['links']:
            page += 1
            time.sleep(RATE_LIMIT_DELAY)
        else:
            break
    
    with open(PROGRAMS_CACHE_FILE, 'w') as f:
        json.dump(programs, f)
    
    # Update cache modification time
    os.utime(PROGRAMS_CACHE_FILE, None)
    return programs

def categorize_domain(domain):
    """Enhanced domain categorization"""
    if not domain or '.' not in domain:
        return None
    
    clean_domain = domain.split(':')[0]
    
    if re.match(r'^\*\.[^.]+\..*\*', clean_domain):
        return 'wildcard_tld'
    
    if clean_domain.startswith('*.'):
        parts = clean_domain.split('.')
        if len(parts) >= 3 and '*' not in parts[-1]:
            return 'simple_wildcard'
    
    if '*' not in clean_domain:
        return 'standard'
    
    return None

def extract_domains_from_program(program):
    handle = program.get('attributes', {}).get('handle')
    if not handle:
        return {'standard': set(), 'simple_wildcard': set(), 'wildcard_tld': set()}
    
    domains = {'standard': set(), 'simple_wildcard': set(), 'wildcard_tld': set()}
    scope_url = f"https://api.hackerone.com/v1/hackers/programs/{handle}/structured_scopes"
    data = make_api_request(scope_url, {'page[size]': PAGE_SIZE})
    
    if data and data.get('data'):
        for scope in data['data']:
            if scope.get('attributes', {}).get('asset_type') == 'URL':
                url = scope['attributes']['asset_identifier']
                domain = url.split('//')[-1].split('/')[0].lower().strip()
                if domain:
                    category = categorize_domain(domain)
                    if category:
                        domains[category].add(domain)
    
    return domains

def main():
    print(f"🚀 Starting HackerOne Scanner (Cache expiry: {CACHE_EXPIRY_DAYS} days)")
    start_time = time.time()
    
    programs = fetch_all_programs()
    print(f"📊 Total programs: {len(programs)}")
    
    all_domains = {
        'standard': set(),
        'simple_wildcard': set(),
        'wildcard_tld': set()
    }
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(extract_domains_from_program, program): program 
                 for program in programs}
        
        for i, future in enumerate(as_completed(futures), 1):
            domains = future.result()
            for category in domains:
                all_domains[category].update(domains[category])
            
            if i % 50 == 0:
                elapsed = time.time() - start_time
                print(f"⏳ Processed {i}/{len(programs)} | "
                      f"Standard: {len(all_domains['standard'])} | "
                      f"Simple Wildcards: {len(all_domains['simple_wildcard'])} | "
                      f"Wildcard TLDs: {len(all_domains['wildcard_tld'])} | "
                      f"Elapsed: {elapsed:.1f}s")

    # Save results
    for file_name, category in [
        (STANDARD_DOMAINS_FILE, 'standard'),
        (SIMPLE_WILDCARDS_FILE, 'simple_wildcard'), 
        (WILDCARD_TLDS_FILE, 'wildcard_tld')
    ]:
        with open(file_name, 'w') as f:
            f.write('\n'.join(sorted(all_domains[category])))
    
    total_time = time.time() - start_time
    print(f"\n✅ Scan completed in {total_time:.1f} seconds")
    print(f"📁 Results saved to:")
    print(f"  - {STANDARD_DOMAINS_FILE} ({len(all_domains['standard'])} entries)")
    print(f"  - {SIMPLE_WILDCARDS_FILE} ({len(all_domains['simple_wildcard'])} entries)")
    print(f"  - {WILDCARD_TLDS_FILE} ({len(all_domains['wildcard_tld'])} entries)")

if __name__ == "__main__":
    main()
