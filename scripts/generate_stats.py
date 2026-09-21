#!/usr/bin/env python3
"""Generate n8n-style GitHub stats cards (assets/stats.svg, assets/langs.svg).

Runs in GitHub Actions with GITHUB_TOKEN, so it never depends on a third-party
stats server. Use `--placeholder` to write the initial "waiting" cards.
"""
import json, os, sys, urllib.request, urllib.error
from xml.sax.saxutils import escape as esc

USER = os.environ.get("GH_USER", "mokal2002")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")

BG="#12111A"; PANEL="#1E1D2B"; STROKE="#3A3950"; LINE="#4A4960"
TXT="#F5F5F7"; SOFT="#C9C7D9"; MUTED="#8F8DA6"
CORAL="#FF6D5A"; PINK="#EA4B71"; PURPLE="#9B6BFF"; TEAL="#29C6A8"; AMBER="#F5A524"; BLUE="#4C9BFF"
PALETTE = [CORAL, PURPLE, TEAL, PINK, AMBER, BLUE]

STYLE = """<style>
.sans{font-family:Inter,'Segoe UI','Helvetica Neue',Arial,sans-serif}
.mono{font-family:'JetBrains Mono','SFMono-Regular',Consolas,'Liberation Mono',Menlo,monospace}
</style>"""

def api(path):
    req = urllib.request.Request("https://api.github.com" + path)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "profile-stats")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

def card(w, h, label, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{esc(label)}">'
            f'<defs>{STYLE}<pattern id="dots" width="24" height="24" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1.3" fill="#2C2B3B"/></pattern></defs>'
            f'<rect width="{w}" height="{h}" rx="16" fill="{BG}"/><rect width="{w}" height="{h}" rx="16" fill="url(#dots)"/>'
            f'<rect x="0.75" y="0.75" width="{w-1.5}" height="{h-1.5}" rx="16" fill="none" stroke="{STROKE}" stroke-width="1.5"/>'
            f'{body}</svg>')

def header(title, num):
    return (f'<rect x="20" y="18" width="30" height="30" rx="8" fill="{CORAL}" fill-opacity="0.16" stroke="{CORAL}" stroke-opacity="0.6"/>'
            f'<text class="mono" x="35" y="38" text-anchor="middle" font-size="12" font-weight="700" fill="{CORAL}">{num}</text>'
            f'<text class="sans" x="62" y="39" font-size="17" font-weight="700" fill="{TXT}">{esc(title)}</text>'
            f'<line x1="20" y1="62" x2="{{W}}" y2="62" stroke="#2C2B3B"/>')

def stats_svg(rows, note=None):
    W, H = 495, 200
    b = header("GitHub Stats", "01").replace("{W}", str(W - 20))
    for i, (label, value, col) in enumerate(rows):
        cx = 24 + (i % 2) * 235
        cy = 92 + (i // 2) * 34
        b += f'<circle cx="{cx+4}" cy="{cy-4}" r="4" fill="{col}"/>'
        b += f'<text class="sans" x="{cx+18}" y="{cy}" font-size="13" fill="{SOFT}">{esc(label)}</text>'
        b += f'<text class="mono" x="{cx+205}" y="{cy}" text-anchor="end" font-size="14" font-weight="700" fill="{TXT}">{esc(str(value))}</text>'
    if note:
        b += f'<text class="mono" x="{W/2}" y="{H-14}" text-anchor="middle" font-size="11" fill="{MUTED}">{esc(note)}</text>'
    return card(W, H, "GitHub stats", b)

def langs_svg(langs, note=None):
    W, H = 495, 200
    b = header("Top Languages", "02").replace("{W}", str(W - 20))
    if not langs:
        b += f'<text class="mono" x="{W/2}" y="120" text-anchor="middle" font-size="13" fill="{MUTED}">{esc(note or "No data yet")}</text>'
        return card(W, H, "Top languages", b)
    total = sum(v for _, v in langs) or 1
    # stacked bar
    x, bx, bw = 24, 24, W - 48
    b += f'<clipPath id="bar"><rect x="{bx}" y="76" width="{bw}" height="10" rx="5"/></clipPath><g clip-path="url(#bar)">'
    for i, (name, v) in enumerate(langs):
        w = bw * v / total
        b += f'<rect x="{x:.1f}" y="76" width="{w:.1f}" height="10" fill="{PALETTE[i % len(PALETTE)]}"/>'
        x += w
    b += '</g>'
    for i, (name, v) in enumerate(langs):
        cx = 24 + (i % 2) * 235
        cy = 116 + (i // 2) * 28
        col = PALETTE[i % len(PALETTE)]
        b += f'<circle cx="{cx+4}" cy="{cy-4}" r="4" fill="{col}"/>'
        b += f'<text class="sans" x="{cx+18}" y="{cy}" font-size="13" fill="{SOFT}">{esc(name)}</text>'
        b += f'<text class="mono" x="{cx+205}" y="{cy}" text-anchor="end" font-size="13" font-weight="700" fill="{TXT}">{100*v/total:.1f}%</text>'
    return card(W, H, "Top languages", b)

def save(name, content):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
        f.write(content)

def placeholder():
    msg = "Waiting for first workflow run"
    save("stats.svg", stats_svg([("Public repos", "–", CORAL), ("Stars earned", "–", PURPLE), ("Followers", "–", TEAL),
                                  ("Forks", "–", PINK), ("Pull requests", "–", AMBER), ("Issues", "–", BLUE)], msg))
    save("langs.svg", langs_svg([], msg))

def main():
    if "--placeholder" in sys.argv:
        placeholder(); return
    try:
        user = api(f"/users/{USER}")
        repos, page = [], 1
        while True:
            chunk = api(f"/users/{USER}/repos?per_page=100&type=owner&page={page}")
            repos += chunk
            if len(chunk) < 100: break
            page += 1
        own = [r for r in repos if not r.get("fork")]
        stars = sum(r["stargazers_count"] for r in own)
        forks = sum(r["forks_count"] for r in own)
        langs = {}
        for r in own:
            try:
                for k, v in api(f"/repos/{USER}/{r['name']}/languages").items():
                    langs[k] = langs.get(k, 0) + v
            except urllib.error.HTTPError:
                pass
        prs = api(f"/search/issues?q=author:{USER}+type:pr&per_page=1")["total_count"]
        issues = api(f"/search/issues?q=author:{USER}+type:issue&per_page=1")["total_count"]
    except Exception as e:  # keep the previous cards if the API is unavailable
        print("GitHub API unavailable, keeping existing cards:", e)
        return
    rows = [("Public repos", user["public_repos"], CORAL), ("Stars earned", stars, PURPLE),
            ("Followers", user["followers"], TEAL), ("Forks", forks, PINK),
            ("Pull requests", prs, AMBER), ("Issues", issues, BLUE)]
    save("stats.svg", stats_svg(rows))
    top = sorted(langs.items(), key=lambda kv: -kv[1])[:6]
    save("langs.svg", langs_svg(top))
    print("Updated stats.svg and langs.svg")

if __name__ == "__main__":
    main()
