import os
import requests
import json
from datetime import datetime

TOKEN = os.environ["GITHUB_TOKEN"]
USERNAME = os.environ.get("GITHUB_USERNAME", "mgiorgi13")

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json",
}

# --- GraphQL query: stars, commits, PRs, issues, repos ---
QUERY = """
query($login: String!) {
  user(login: $login) {
    name
    repositories(ownerAffiliations: OWNER, isFork: false, first: 100) {
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      totalRepositoryContributions
    }
    followers { totalCount }
  }
}
"""

resp = requests.post(
    "https://api.github.com/graphql",
    headers=HEADERS,
    json={"query": QUERY, "variables": {"login": USERNAME}},
)
resp.raise_for_status()
data = resp.json()["data"]["user"]

repos = data["repositories"]["nodes"]
stars = sum(r["stargazerCount"] for r in repos)
contribs = data["contributionsCollection"]
commits = contribs["totalCommitContributions"]
prs = contribs["totalPullRequestContributions"]
issues = contribs["totalIssueContributions"]
followers = data["followers"]["totalCount"]

# Top languages by bytes
lang_sizes: dict[str, int] = {}
lang_colors: dict[str, str] = {}
for repo in repos:
    for edge in repo["languages"]["edges"]:
        name = edge["node"]["name"]
        color = edge["node"]["color"] or "#858585"
        lang_sizes[name] = lang_sizes.get(name, 0) + edge["size"]
        lang_colors[name] = color

top_langs = sorted(lang_sizes.items(), key=lambda x: x[1], reverse=True)[:6]
total_bytes = sum(v for _, v in top_langs) or 1

updated = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

# --- Build SVG ---
W, H = 780, 220
CARD_W = 370
GAP = 20
LEFT_X = GAP
RIGHT_X = CARD_W + GAP * 2

def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def stat_row(x, y, label, value):
    return (
        f'<text x="{x}" y="{y}" font-size="13" fill="#57606a">{esc(label)}</text>'
        f'<text x="{x+180}" y="{y}" font-size="13" font-weight="600" fill="#24292f" text-anchor="end">{esc(value)}</text>'
    )

# Language bars
bar_rows = ""
bar_y = 60
BAR_W = CARD_W - 40
for lang, size in top_langs:
    pct = size / total_bytes * 100
    bar_w = int(BAR_W * pct / 100)
    color = lang_colors[lang]
    bar_rows += (
        f'<text x="{RIGHT_X + 20}" y="{bar_y}" font-size="12" fill="#57606a">{esc(lang)}</text>'
        f'<text x="{RIGHT_X + CARD_W - 20}" y="{bar_y}" font-size="12" fill="#57606a" text-anchor="end">{pct:.1f}%</text>'
        f'<rect x="{RIGHT_X + 20}" y="{bar_y + 4}" width="{BAR_W}" height="6" rx="3" fill="#e8eaed"/>'
        f'<rect x="{RIGHT_X + 20}" y="{bar_y + 4}" width="{bar_w}" height="6" rx="3" fill="{color}"/>'
    )
    bar_y += 26

svg = f"""<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif">
  <style>
    .card {{ fill: #ffffff; stroke: #d0d7de; stroke-width: 1; rx: 6; }}
  </style>

  <!-- Left card: Stats -->
  <rect x="{LEFT_X}" y="10" width="{CARD_W}" height="{H - 20}" rx="6" fill="#ffffff" stroke="#d0d7de" stroke-width="1"/>
  <text x="{LEFT_X + 20}" y="38" font-size="14" font-weight="600" fill="#24292f">📊 GitHub Stats</text>
  {stat_row(LEFT_X + 20, 68,  "⭐ Total Stars",    f"{stars:,}")}
  {stat_row(LEFT_X + 20, 94,  "📦 Commits (year)", f"{commits:,}")}
  {stat_row(LEFT_X + 20, 120, "🔀 Pull Requests",  f"{prs:,}")}
  {stat_row(LEFT_X + 20, 146, "🐛 Issues opened",  f"{issues:,}")}
  {stat_row(LEFT_X + 20, 172, "👥 Followers",       f"{followers:,}")}
  <text x="{LEFT_X + 20}" y="{H - 16}" font-size="10" fill="#8c959f">Updated: {updated}</text>

  <!-- Right card: Languages -->
  <rect x="{RIGHT_X}" y="10" width="{CARD_W}" height="{H - 20}" rx="6" fill="#ffffff" stroke="#d0d7de" stroke-width="1"/>
  <text x="{RIGHT_X + 20}" y="38" font-size="14" font-weight="600" fill="#24292f">💻 Top Languages</text>
  {bar_rows}
</svg>"""

os.makedirs("assets", exist_ok=True)
with open("assets/github-stats.svg", "w", encoding="utf-8") as f:
    f.write(svg)

print(f"✅ SVG generated — stars:{stars} commits:{commits} prs:{prs} issues:{issues}")
