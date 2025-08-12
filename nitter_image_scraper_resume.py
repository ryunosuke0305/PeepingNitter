import os
import json
import time
import logging
from datetime import datetime
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

try:
    from tqdm import tqdm
except Exception:  # pragma: no cover - tqdmなしでも動作可能
    def tqdm(iterable, *args, **kwargs):
        return iterable


logger = logging.getLogger(__name__)


CONFIG = {
    "USERNAME": "jack",
    "INSTANCE": "https://nitter.net",
    "OUT_DIR": "./downloads",
    "MAX_PAGES": 5,
    "PAGE_DELAY": 1.0,
    "DL_DELAY": 0.1,
    "TIMEOUT": 30,
    "LOG_FILENAME": "download_log.json",
}


def setup_logger(dest_dir: str) -> None:
    log_file = os.path.join(dest_dir, "error.log")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
    )


def init_log(log_path: str) -> dict:
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8") as f:
            return json.load(f)
    now = datetime.utcnow().isoformat() + "Z"
    data = {"created_at": now, "updated_at": now, "downloaded": {}, "errors": {}}
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data


def save_log(log_path: str, data: dict) -> None:
    data["updated_at"] = datetime.utcnow().isoformat() + "Z"
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def fetch_page(session: requests.Session, username: str, page: int) -> str:
    base = CONFIG["INSTANCE"].rstrip("/")
    if page == 1:
        url = f"{base}/{username}"
    else:
        url = f"{base}/{username}?page={page}"
    for attempt in range(3):
        try:
            res = session.get(url, timeout=CONFIG["TIMEOUT"])
            if res.status_code == 200:
                return res.text
            logger.warning(
                "Failed to fetch %s (status %s) [attempt %s]",
                url,
                res.status_code,
                attempt + 1,
            )
        except requests.RequestException as e:
            logger.error("Error fetching %s: %s", url, e)
        time.sleep(CONFIG["PAGE_DELAY"])
    logger.error("Giving up fetching %s after 3 attempts", url)
    return ""


def extract_image_urls(html: str) -> list:
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a in soup.select('a[href^="/pic/"]'):
        href = a.get("href")
        if not href:
            continue
        abs_url = urljoin(CONFIG["INSTANCE"], href)
        if "name=orig" not in abs_url:
            delimiter = "&" if "?" in abs_url else "?"
            abs_url = f"{abs_url}{delimiter}name=orig"
        links.append(abs_url)
    return links


def guess_filename(url: str, content_type: str) -> str:
    name = os.path.basename(urlparse(url).path)
    if "." in name:
        return name
    mapping = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/gif": ".gif",
    }
    ext = mapping.get(content_type.split(";")[0].lower(), "")
    return name + ext


def download_image(session: requests.Session, url: str, dest_dir: str, log: dict) -> None:
    if url in log["downloaded"]:
        return
    for attempt in range(3):
        try:
            res = session.get(url, timeout=CONFIG["TIMEOUT"], stream=True)
            if res.status_code == 200 and res.headers.get("Content-Type", "").startswith("image"):
                filename = guess_filename(url, res.headers.get("Content-Type", ""))
                path = os.path.join(dest_dir, filename)
                with open(path, "wb") as f:
                    for chunk in res.iter_content(8192):
                        f.write(chunk)
                log["downloaded"][url] = filename
                save_log(os.path.join(dest_dir, CONFIG["LOG_FILENAME"]), log)
                return
            logger.warning(
                "Invalid response for %s (status %s, content-type %s) [attempt %s]",
                url,
                res.status_code,
                res.headers.get("Content-Type"),
                attempt + 1,
            )
        except requests.RequestException as e:
            logger.error("Error downloading %s: %s", url, e)
        time.sleep(CONFIG["DL_DELAY"])
    log["errors"][url] = log["errors"].get(url, 0) + 1
    save_log(os.path.join(dest_dir, CONFIG["LOG_FILENAME"]), log)
    logger.error("Failed to download %s after 3 attempts", url)


def main() -> None:
    session = requests.Session()
    user_dir = os.path.join(CONFIG["OUT_DIR"], CONFIG["USERNAME"])
    os.makedirs(user_dir, exist_ok=True)
    setup_logger(user_dir)
    log_path = os.path.join(user_dir, CONFIG["LOG_FILENAME"])
    log = init_log(log_path)

    for page in range(1, CONFIG["MAX_PAGES"] + 1):
        html = fetch_page(session, CONFIG["USERNAME"], page)
        if not html:
            logger.error("No HTML fetched for page %s; stopping.", page)
            break
        urls = extract_image_urls(html)
        for url in tqdm(urls, desc=f"page {page}"):
            download_image(session, url, user_dir, log)
        time.sleep(CONFIG["PAGE_DELAY"])


if __name__ == "__main__":
    try:
        main()
    except Exception:  # pragma: no cover - エラー原因記録のため
        logger.exception("Unhandled exception occurred")
        raise
