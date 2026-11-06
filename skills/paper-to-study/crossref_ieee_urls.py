"""由參考文獻標題查 IEEE Xplore 文件網址（Crossref → doi.org 轉址）。

用法：
    python crossref_ieee_urls.py <refs.json> <ieee_papers.json>

refs.json：[{"ref": "1", "title": "..."}, ...]（Phase 0c 的 to_download）
輸出 ieee_papers.json：只含「標題完全吻合且解出 /document/NNN」者，格式同 ieee_downloader.py 的輸入。
每篇印一行：HIT / MISS / NOURL，最後印 written N。
"""
import json, re, sys, urllib.request, urllib.parse, urllib.error
from pathlib import Path

UA = {"User-Agent": "paper-to-study/1.0 (mailto:noreply@example.com)"}


def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def resolve(doi):
    url = "https://doi.org/" + doi
    opener = urllib.request.build_opener(_NoRedirect)
    for _ in range(5):
        try:
            opener.open(urllib.request.Request(url, headers=UA), timeout=20)
            return url
        except urllib.error.HTTPError as e:
            loc = e.headers.get("Location")
            if not loc:
                return url
            url = urllib.parse.urljoin(url, loc)
            m = re.search(r"ieeexplore\.ieee\.org/document/(\d+)", url)
            if m:
                return f"https://ieeexplore.ieee.org/document/{m.group(1)}/"
    return url


def main(src, dst):
    refs = json.loads(Path(src).read_text(encoding="utf-8"))
    out = []
    for r in refs:
        title = r["title"]
        q = urllib.parse.urlencode({"query.bibliographic": title, "rows": 5, "filter": "prefix:10.1109"})
        try:
            data = json.load(urllib.request.urlopen(
                urllib.request.Request("https://api.crossref.org/works?" + q, headers=UA), timeout=30))
        except Exception as e:
            print(r["ref"], "ERROR", e)
            continue
        hit = next((it for it in data["message"]["items"]
                    if norm((it.get("title") or [""])[0]) == norm(title)), None)
        if not hit:
            print(r["ref"], "MISS")
            continue
        url = resolve(hit["DOI"])
        if "/document/" in url:
            print(r["ref"], "HIT", hit["DOI"], url)
            out.append({"ref": r["ref"], "title": title, "url": url})
        else:
            print(r["ref"], "NOURL", hit["DOI"], url)
    Path(dst).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print("written", len(out))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
