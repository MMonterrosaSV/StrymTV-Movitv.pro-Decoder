#!/usr/bin/env python3
"""
Fetch the M3U playlist from https://movitv.pro/,
decode the Base85 (RFC 1924) encoded stream URLs,
append the website name in parentheses to the channel name,
and write a clean readable M3U file.
"""

import ssl
import base64
import urllib.request
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime, timezone

SOURCE_URL = "https://movitv.pro/"
OUTPUT_FILE = "movitv_decoded.m3u"


def decode_b85(encoded: str) -> str:
    encoded = encoded.strip()
    try:
        raw = base64.b85decode(encoded.encode("ascii"))
        return raw.decode("utf-8", errors="replace").strip()
    except Exception as e:
        print(f"  [!] Failed to decode: {encoded[:50]}... → {e}")
        return encoded


def get_site_tag(url_or_payload: str) -> str:
    try:
        url = url_or_payload.split()[0]
        host = urlparse(url).netloc.lower()
        if host.startswith("www."):
            host = host[4:]
        return host.split(".")[0].upper()
    except Exception:
        return "UNKNOWN"


def fetch_playlist(url: str) -> str:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; M3U-Decoder/1.0)"},
    )
    with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def process_m3u(content: str) -> str:
    lines = content.splitlines()
    output_lines = []
    i = 0

    while i < len(lines):
        line = lines[i].rstrip()

        if line.startswith("#EXTINF"):
            extinf_line = line
            i += 1

            encoded_parts = []
            while i < len(lines):
                next_line = lines[i].rstrip()
                if not next_line or next_line.startswith("#"):
                    break
                encoded_parts.append(next_line)
                i += 1

            if encoded_parts:
                encoded = "".join(encoded_parts)
                decoded = decode_b85(encoded)

                site = get_site_tag(decoded)
                tag = f"({site})"

                if "," in extinf_line:
                    left, right = extinf_line.rsplit(",", 1)
                    new_extinf = f"{left},{right.strip()} {tag}"
                else:
                    new_extinf = f"{extinf_line} {tag}"

                output_lines.append(new_extinf)
                output_lines.append(decoded)
            else:
                output_lines.append(extinf_line)
            continue

        output_lines.append(line)
        i += 1

    return "\n".join(output_lines) + "\n"


def main():
    print(f"[{datetime.now(timezone.utc):%Y-%m-%d %H:%M:%S} UTC] Fetching playlist…")
    raw = fetch_playlist(SOURCE_URL)

    print("Decoding Base85 links and adding site tags…")
    decoded = process_m3u(raw)

    Path(OUTPUT_FILE).write_text(decoded, encoding="utf-8")
    print(f"Written → {OUTPUT_FILE}")

    url_count = sum(1 for line in decoded.splitlines() if "http" in line)
    print(f"Decoded {url_count} stream entries.")


if __name__ == "__main__":
    main()
