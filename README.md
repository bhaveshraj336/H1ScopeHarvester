# 🕵️‍♂️ HackerOne Domain Fetcher

This Python script fetches all public programs from [HackerOne](https://hackerone.com) using their API, extracts domains in scope, categorizes them, and saves them into structured `.txt` files.

---

## 📦 Features

- 🚀 Fetches all public HackerOne programs
- 📂 Categorizes domains into:
  - `Standard Domains` (e.g., example.com)
  - `Simple Wildcards` (e.g., *.example.com)
  - `Wildcard TLDs` (e.g., *.something.*)
- 💾 Caches program metadata to reduce API usage
- 🚦 Handles rate limiting & retries automatically
- 🧵 Multi-threaded for faster extraction

---

## 📁 Output

After running the script, it generates:

- `hackerone_standard_domains.txt`
- `hackerone_simple_wildcards.txt`
- `hackerone_wildcard_tlds.txt`

---

## 🛠️ Setup

### 1. Clone the Repository

git clone [https://github.com/yourusername/hackerone-domain-fetcher.git](https://github.com/bhaveshraj336/H1ScopeHarvester.git) 
cd hackerone-domain-fetcher


### 2. Install Requirements

pip3 install requests

### 3. Configure Authentication

Edit the script and provide your HackerOne API credentials:

```python
API_USERNAME = 'your_hackerone_username'
API_TOKEN = 'your_hackerone_api_token'
▶️ Usage
python3 hackerone_fetch_domains.py
⏱️ Notes
API rate limit is respected (600 reads/minute)

Cache is valid for 30 days by default

You can adjust MAX_WORKERS, CACHE_EXPIRY_DAYS, and PAGE_SIZE in the script

🤝 Contributing
Pull requests and feature suggestions are welcome!

🛡️ License
MIT License
