#!/usr/bin/env python3
"""
split_ssss_blocklist.py

Downloads the Super-SEO-Spam-Suppressor domain blocklist and splits it
into chunks small enough for AdGuard DNS's 5 MB per-list import limit.

Usage:
    python3 split_ssss_blocklist.py
    python3 split_ssss_blocklist.py --format dnsmasq --max-mb 4.5 --out ./blocklist_parts

Then host each part_N.txt somewhere with a raw URL (a GitHub Gist, a
"raw" file in your own repo, GitHub Pages, etc.) and add each URL as a
separate custom blocklist in AdGuard DNS (Settings > DNS protection >
Blocklists > Add blocklist). AdGuard DNS is fine with multiple lists.

Re-run this script whenever you want an updated split (the source repo
updates its lists roughly daily).
"""

import argparse
import os
import urllib.request

SOURCES = {
    # plain "one domain per line" list - smallest, works with AdGuard DNS
    "domains": "https://raw.githubusercontent.com/NotaInutilis/Super-SEO-Spam-Suppressor/main/domains.txt",
    # dnsmasq-formatted list (larger, includes "address=/x/#" syntax)
    "dnsmasq": "https://raw.githubusercontent.com/NotaInutilis/Super-SEO-Spam-Suppressor/main/dnsmasq.txt",
    # hosts-file formatted list
    "hosts": "https://raw.githubusercontent.com/NotaInutilis/Super-SEO-Spam-Suppressor/main/hosts.txt",
}


def download(url: str) -> str:
    print(f"Downloading {url} ...")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp:
        data = resp.read().decode("utf-8", errors="replace")
    print(f"Downloaded {len(data):,} characters")
    return data


def split_by_size(text: str, max_bytes: int):
    """Split text into chunks <= max_bytes, breaking only on full lines,
    and re-adding a header comment to each part."""
    lines = text.splitlines(keepends=True)

    header_lines = []
    body_start = 0
    for i, line in enumerate(lines):
        if line.strip().startswith("!") or line.strip().startswith("#"):
            header_lines.append(line)
            body_start = i + 1
        else:
            break

    body_lines = lines[body_start:]

    chunks = []
    current = []
    current_size = 0
    for line in body_lines:
        line_size = len(line.encode("utf-8"))
        if current_size + line_size > max_bytes and current:
            chunks.append(current)
            current = []
            current_size = 0
        current.append(line)
        current_size += line_size
    if current:
        chunks.append(current)

    return header_lines, chunks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=SOURCES.keys(), default="domains",
                         help="Which upstream list format to use (default: domains)")
    parser.add_argument("--max-mb", type=float, default=4.5,
                         help="Max size per chunk in MB (default: 4.5, safely under the 5MB cap)")
    parser.add_argument("--out", default="./blocklist_parts",
                         help="Output directory for the split files")
    args = parser.parse_args()

    url = SOURCES[args.format]
    text = download(url)

    max_bytes = int(args.max_mb * 1024 * 1024)
    header_lines, chunks = split_by_size(text, max_bytes)

    os.makedirs(args.out, exist_ok=True)

    total_lines = sum(len(c) for c in chunks)
    print(f"Total rule lines: {total_lines:,}")
    print(f"Splitting into {len(chunks)} part(s), each <= {args.max_mb} MB")

    for i, chunk in enumerate(chunks, start=1):
        part_path = os.path.join(args.out, f"part_{i}.txt")
        with open(part_path, "w", encoding="utf-8") as f:
            f.write(f"! Super-SEO-Spam-Suppressor - part {i} of {len(chunks)}\n")
            f.writelines(header_lines)
            f.writelines(chunk)
        size_mb = os.path.getsize(part_path) / (1024 * 1024)
        print(f"  wrote {part_path} ({size_mb:.2f} MB, {len(chunk):,} lines)")

    print("\nDone. Host each part_N.txt at a public raw URL, then in AdGuard DNS:")
    print("  Settings > DNS protection > Blocklists > Add blocklist")
    print("  ...and paste each part's URL as its own custom blocklist entry.")


if __name__ == "__main__":
    main()
