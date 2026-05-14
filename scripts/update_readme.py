"""
Auto-update script for ToyBitZ00's GitHub profile README.
Fetches live data from the GitHub API and updates placeholder sections.
"""

import os
import re
import requests
from datetime import datetime, timezone

# ── Config ────────────────────────────────────────────────────────────────────
USERNAME = os.environ.get("GITHUB_USERNAME", "ToyBitZ00")
TOKEN    = os.environ.get("GITHUB_TOKEN", "")

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

README_PATH = "README.md"

# ── Helpers ───────────────────────────────────────────────────────────────────

def gh_get(url, params=None):
    """Make a GitHub API GET request and return JSON."""
    r = requests.get(url, headers=HEADERS, params=params, timeout=15)
    r.raise_for_status()
    return r.json()


def fetch_stats():
    """Return a dict of computed stats from the GitHub API."""
    # Basic user info
    user = gh_get(f"https://api.github.com/users/{USERNAME}")
    public_repos   = user.get("public_repos", 0)
    followers      = user.get("followers", 0)

    # All repos
    repos = []
    page  = 1
    while True:
        page_data = gh_get(
            f"https://api.github.com/users/{USERNAME}/repos",
            params={"per_page": 100, "page": page, "type": "owner"},
        )
        if not page_data:
            break
        repos.extend(page_data)
        page += 1

    total_stars  = sum(r.get("stargazers_count", 0) for r in repos)
    languages    = set(r.get("language") for r in repos if r.get("language"))
    lang_count   = len(languages)

    # Recent activity (last 5 public events)
    events = gh_get(
        f"https://api.github.com/users/{USERNAME}/events/public",
        params={"per_page": 10},
    )

    activity_lines = []
    seen = 0
    for ev in events:
        if seen >= 5:
            break
        etype   = ev.get("type", "")
        repo    = ev.get("repo", {}).get("name", "")
        created = ev.get("created_at", "")
        date_str = created[:10] if created else "?"

        if etype == "PushEvent":
            commits = ev.get("payload", {}).get("commits", [])
            msg     = commits[0].get("message", "").splitlines()[0] if commits else "pushed"
            activity_lines.append(f"| 📝 Push | `{repo}` | {msg[:55]} | `{date_str}` |")
            seen += 1
        elif etype == "CreateEvent":
            ref_type = ev.get("payload", {}).get("ref_type", "branch")
            ref      = ev.get("payload", {}).get("ref", "")
            activity_lines.append(f"| ✨ Created {ref_type} | `{repo}` | `{ref}` | `{date_str}` |")
            seen += 1
        elif etype == "WatchEvent":
            activity_lines.append(f"| ⭐ Starred | `{repo}` | — | `{date_str}` |")
            seen += 1
        elif etype == "ForkEvent":
            activity_lines.append(f"| 🍴 Forked | `{repo}` | — | `{date_str}` |")
            seen += 1
        elif etype == "IssuesEvent":
            action = ev.get("payload", {}).get("action", "")
            title  = ev.get("payload", {}).get("issue", {}).get("title", "")[:50]
            activity_lines.append(f"| 🐛 Issue {action} | `{repo}` | {title} | `{date_str}` |")
            seen += 1

    if not activity_lines:
        activity_lines = ["| — | No recent public activity found | — | — |"]

    updated_at = datetime.now(timezone.utc).strftime("%B %d, %Y at %H:%M UTC")

    return {
        "public_repos": public_repos,
        "followers":    followers,
        "total_stars":  total_stars,
        "lang_count":   lang_count,
        "activity":     activity_lines,
        "updated_at":   updated_at,
    }


def build_stats_table(stats):
    return f"""| 📊 Stat | 🔢 Count |
|--------|---------|
| 🗂️ Public Repositories | **{stats['public_repos']}** |
| 👥 Followers | **{stats['followers']}** |
| ⭐ Total Stars | **{stats['total_stars']}** |
| 💬 Languages Used | **{stats['lang_count']}** |
| 🤝 Collaborations | **Multiple team projects** |"""


def build_activity_table(stats):
    header = """| 🔔 Event | 📁 Repository | 📝 Details | 📅 Date |
|---------|-------------|---------|------|"""
    rows   = "\n".join(stats["activity"])
    return f"{header}\n{rows}"


def replace_section(content, marker, new_block):
    """
    Replace everything between <!-- START:marker --> and <!-- END:marker -->
    with new_block.
    """
    pattern = rf"(<!-- START:{marker} -->).*?(<!-- END:{marker} -->)"
    replacement = rf"\1\n{new_block}\n\2"
    new_content, count = re.subn(pattern, replacement, content, flags=re.DOTALL)
    if count == 0:
        print(f"  ⚠️  Marker '{marker}' not found in README — skipping.")
    return new_content


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(f"🔍 Fetching GitHub stats for @{USERNAME}...")
    stats = fetch_stats()

    print(f"   ✅ Repos: {stats['public_repos']}  |  Stars: {stats['total_stars']}  |  Followers: {stats['followers']}")
    print(f"   ✅ Languages: {stats['lang_count']}  |  Activity events: {len(stats['activity'])}")

    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # Replace stats table
    content = replace_section(content, "STATS", build_stats_table(stats))

    # Replace activity feed
    content = replace_section(content, "ACTIVITY", build_activity_table(stats))

    # Replace last-updated timestamp
    content = replace_section(
        content, "UPDATED",
        f"*🤖 Last auto-updated: **{stats['updated_at']}***"
    )

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"✅ README.md updated successfully at {stats['updated_at']}")


if __name__ == "__main__":
    main()
