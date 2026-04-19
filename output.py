# formats and writes results to JSON and HTML dashboard

import json
import os
from collections import Counter
from datetime import datetime

FLAG_META = {
    "deployment_signals":      "Deployment",
    "recent_commit_velocity":  "Velocity",
    "external_engagement":     "Engagement",
    "readme_product_voice":    "Product Voice",
    "stack_sophistication":    "Sophistication",
    "domain_focus_clustering": "Domain Focus",
    "complexity_progression":  "Complexity↑",
    "bio_signals":             "Indie Bio",
}

# (bg, text, border)
TYPE_COLORS = {
    "Active Product Builder": ("#1a4731", "#3fb950", "#238636"),
    "Early Trajectory":       ("#2d1f0c", "#e3b341", "#9e6a03"),
    "Hobbyist":               ("#21262d", "#8b949e", "#30363d"),
    "Already Known":          ("#0c2137", "#58a6ff", "#1f6feb"),
}

# ─────────────────────────────────────────────────────────────────────────────
# CSS (plain string — no f-string escaping needed)
# ─────────────────────────────────────────────────────────────────────────────

_CSS = """
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
               "Helvetica Neue", sans-serif;
  background: #0d1117;
  color: #e6edf3;
  min-height: 100vh;
  padding: 2rem 2.5rem 4rem;
}

/* ── Header ── */
header { margin-bottom: 2rem; }
header h1 {
  font-size: 1.6rem;
  font-weight: 700;
  letter-spacing: -.5px;
  color: #e6edf3;
}
header h1 span { color: #3fb950; }
.subtitle {
  margin-top: .35rem;
  font-size: .85rem;
  color: #8b949e;
}

/* ── Stat cards ── */
.stat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: 1rem;
  margin-top: 1.5rem;
}
.stat-card {
  background: #161b22;
  border: 1px solid #30363d;
  border-radius: 8px;
  padding: 1.1rem 1.25rem;
}
.stat-card .count {
  font-size: 2rem;
  font-weight: 700;
  line-height: 1;
}
.stat-card .label {
  margin-top: .4rem;
  font-size: .78rem;
  color: #8b949e;
  text-transform: uppercase;
  letter-spacing: .5px;
}
.stat-apb .count { color: #3fb950; }
.stat-et  .count { color: #e3b341; }
.stat-hob .count { color: #8b949e; }
.stat-ak  .count { color: #58a6ff; }

/* ── Filter bar ── */
.filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: .5rem;
  margin: 1.75rem 0 1.25rem;
}
.filter-btn {
  padding: .35rem .9rem;
  border-radius: 999px;
  border: 1px solid #30363d;
  background: #21262d;
  color: #8b949e;
  font-size: .8rem;
  cursor: pointer;
  transition: all .15s;
}
.filter-btn:hover { border-color: #8b949e; color: #e6edf3; }
.filter-btn.active-all  { background: #e6edf3; color: #0d1117; border-color: #e6edf3; }
.filter-btn.active-apb  { background: #238636; color: #e6edf3; border-color: #238636; }
.filter-btn.active-et   { background: #9e6a03; color: #e6edf3; border-color: #9e6a03; }
.filter-btn.active-hob  { background: #30363d; color: #e6edf3; border-color: #30363d; }
.filter-btn.active-ak   { background: #1f6feb; color: #e6edf3; border-color: #1f6feb; }

.result-count { font-size: .82rem; color: #8b949e; margin-bottom: .75rem; }

/* ── Table ── */
.table-wrap {
  overflow-x: auto;
  border: 1px solid #30363d;
  border-radius: 8px;
}
table { width: 100%; border-collapse: collapse; }
thead tr { background: #161b22; border-bottom: 1px solid #30363d; }
th {
  padding: .65rem 1rem;
  font-size: .75rem;
  font-weight: 600;
  color: #8b949e;
  text-transform: uppercase;
  letter-spacing: .5px;
  white-space: nowrap;
  text-align: left;
}
th.center { text-align: center; }

/* data rows */
.data-row {
  border-bottom: 1px solid #21262d;
  cursor: pointer;
  transition: background .12s;
}
.data-row:last-of-type { border-bottom: none; }
.data-row:hover { background: #161b22; }
td {
  padding: .7rem 1rem;
  font-size: .85rem;
  vertical-align: middle;
}
td.center { text-align: center; }
.hidden { display: none !important; }

/* avatar */
.avatar {
  width: 36px; height: 36px;
  border-radius: 50%;
  object-fit: cover;
  border: 1px solid #30363d;
  display: block;
}

/* username */
.username-link {
  color: #58a6ff;
  text-decoration: none;
  font-weight: 500;
}
.username-link:hover { text-decoration: underline; }

/* profile type badge */
.type-badge {
  display: inline-block;
  padding: .22rem .65rem;
  border-radius: 999px;
  font-size: .75rem;
  font-weight: 600;
  white-space: nowrap;
  border: 1px solid;
}

/* flag pills */
.pills { display: flex; flex-wrap: wrap; gap: .3rem; }
.pill {
  display: inline-block;
  padding: .18rem .5rem;
  border-radius: 4px;
  font-size: .7rem;
  font-weight: 500;
  white-space: nowrap;
}
.pill-on  { background: #238636; color: #e6edf3; }
.pill-off { background: transparent; color: #484f58; border: 1px solid #30363d; }

/* checkbox */
.shortlist-cb { width: 16px; height: 16px; cursor: pointer; accent-color: #3fb950; }

/* detail panel row */
.detail-row td {
  padding: 0;
  background: #0d1117;
  border-bottom: 2px solid #238636;
}
.detail-inner {
  padding: 1rem 1.25rem;
  font-size: .82rem;
  color: #8b949e;
  line-height: 1.7;
}
.detail-inner strong { color: #e6edf3; }
.detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: .5rem .75rem;
  margin-top: .65rem;
}
.detail-flag { display: flex; align-items: center; gap: .4rem; }
.flag-dot {
  width: 8px; height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.flag-dot.on  { background: #3fb950; }
.flag-dot.off { background: #30363d; }

/* footer */
footer {
  margin-top: 1.75rem;
  display: flex;
  align-items: center;
  gap: 1rem;
}
.export-btn {
  padding: .45rem 1rem;
  background: #238636;
  color: #e6edf3;
  border: 1px solid #2ea043;
  border-radius: 6px;
  font-size: .85rem;
  font-weight: 500;
  cursor: pointer;
  transition: background .15s;
}
.export-btn:hover { background: #2ea043; }
.export-btn:disabled { background: #21262d; color: #484f58; border-color: #30363d; cursor: default; }
.shortlist-tally { font-size: .82rem; color: #8b949e; }
"""

# ─────────────────────────────────────────────────────────────────────────────
# JS (plain string — no f-string escaping needed)
# RESULTS_DATA is injected separately before this block.
# ─────────────────────────────────────────────────────────────────────────────

_JS = """
// ── Filtering ──────────────────────────────────────────────────────────────
const filterBtns = document.querySelectorAll('.filter-btn');
const resultCount = document.getElementById('result-count');

function applyFilter(type) {
  const rows = document.querySelectorAll('.data-row');
  let visible = 0;
  rows.forEach(row => {
    const match = type === 'all' || row.dataset.type === type;
    row.classList.toggle('hidden', !match);
    const detail = document.getElementById('detail-' + row.dataset.idx);
    if (detail && !match) detail.classList.add('hidden');
    if (match) visible++;
  });
  resultCount.textContent = visible + ' profile' + (visible !== 1 ? 's' : '');
}

filterBtns.forEach(btn => {
  btn.addEventListener('click', () => {
    filterBtns.forEach(b => b.className = 'filter-btn');
    btn.classList.add('filter-btn', btn.dataset.active);
    applyFilter(btn.dataset.filter);
  });
});

// ── Row expand/collapse ────────────────────────────────────────────────────
document.querySelectorAll('.data-row').forEach(row => {
  row.addEventListener('click', e => {
    if (e.target.closest('.shortlist-cell')) return;
    const detail = document.getElementById('detail-' + row.dataset.idx);
    if (!detail) return;
    const isHidden = detail.classList.contains('hidden');
    // collapse all others
    document.querySelectorAll('.detail-row').forEach(d => d.classList.add('hidden'));
    if (isHidden) detail.classList.remove('hidden');
  });
});

// ── Shortlist counter ──────────────────────────────────────────────────────
const tally = document.getElementById('shortlist-tally');
const exportBtn = document.getElementById('export-btn');

function updateTally() {
  const n = document.querySelectorAll('.shortlist-cb:checked').length;
  tally.textContent = n + ' shortlisted';
  exportBtn.disabled = n === 0;
}

document.querySelectorAll('.shortlist-cb').forEach(cb => {
  cb.addEventListener('change', updateTally);
});
updateTally();

// ── CSV Export ─────────────────────────────────────────────────────────────
exportBtn.addEventListener('click', () => {
  const checked = Array.from(document.querySelectorAll('.shortlist-cb:checked'));
  if (!checked.length) return;

  const header = ['username','profile_type','fired_flags','follower_count','account_age_days','github_url'];
  const rows = checked.map(cb => {
    const idx = cb.dataset.idx;
    const r = RESULTS_DATA[idx];
    const fired = Object.entries(r.flags || {})
                        .filter(([,v]) => v)
                        .map(([k]) => k)
                        .join('|');
    return [
      r.username,
      r.profile_type,
      fired,
      r.follower_count,
      r.account_age_days,
      r.github_url
    ].map(v => '"' + String(v ?? '').replace(/"/g, '""') + '"').join(',');
  });

  const csv = [header.join(','), ...rows].join('\\n');
  const blob = new Blob([csv], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'shortlist.csv';
  a.click();
  URL.revokeObjectURL(url);
});
"""

# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def save_results(results: list, output_dir: str = "results") -> None:
    os.makedirs(output_dir, exist_ok=True)
    _write_json(results, os.path.join(output_dir, "results.json"))
    html = generate_dashboard_html(results)
    with open(os.path.join(output_dir, "dashboard.html"), "w", encoding="utf-8") as f:
        f.write(html)


def generate_dashboard_html(results: list) -> str:
    run_date = datetime.now().strftime("%B %d, %Y at %H:%M")
    counts = Counter(r.get("profile_type", "Hobbyist") for r in results)

    stat_cards = _stat_cards(counts)
    filter_bar = _filter_bar()
    table_body = "\n".join(_render_row(r, i) for i, r in enumerate(results))
    results_json = json.dumps(results, default=str)

    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="UTF-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        "<title>GitHub Founder Scout</title>\n"
        f"<style>{_CSS}</style>\n"
        "</head>\n"
        "<body>\n"
        "<header>\n"
        '  <h1>GitHub <span>Founder</span> Scout</h1>\n'
        f'  <p class="subtitle">Run {_esc(run_date)} &nbsp;·&nbsp; {len(results)} profile{"s" if len(results) != 1 else ""} evaluated</p>\n'
        f'  <div class="stat-grid">{stat_cards}</div>\n'
        "</header>\n"
        f'<div class="filter-bar">{filter_bar}</div>\n'
        f'<p class="result-count" id="result-count">{len(results)} profile{"s" if len(results) != 1 else ""}</p>\n'
        '<div class="table-wrap">\n'
        "<table>\n"
        "<thead><tr>\n"
        '  <th style="width:44px"></th>\n'
        "  <th>Username</th>\n"
        "  <th>Profile Type</th>\n"
        "  <th>Flags</th>\n"
        '  <th class="center">Followers</th>\n'
        '  <th class="center">Age (days)</th>\n'
        '  <th class="center">Shortlist</th>\n'
        "</tr></thead>\n"
        f"<tbody>\n{table_body}\n</tbody>\n"
        "</table>\n"
        "</div>\n"
        "<footer>\n"
        '  <button class="export-btn" id="export-btn" disabled>Export Shortlist as CSV</button>\n'
        '  <span class="shortlist-tally" id="shortlist-tally">0 shortlisted</span>\n'
        "</footer>\n"
        f"<script>const RESULTS_DATA = {results_json};</script>\n"
        f"<script>{_JS}</script>\n"
        "</body>\n"
        "</html>\n"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _write_json(results: list, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)


def _stat_cards(counts: Counter) -> str:
    cards = [
        ("Active Product Builder", "stat-apb", "Active Product Builder"),
        ("Early Trajectory",       "stat-et",  "Early Trajectory"),
        ("Hobbyist",               "stat-hob", "Hobbyist"),
        ("Already Known",          "stat-ak",  "Already Known"),
    ]
    html = ""
    for key, css, label in cards:
        html += (
            f'<div class="stat-card {css}">'
            f'<div class="count">{counts.get(key, 0)}</div>'
            f'<div class="label">{label}</div>'
            f"</div>"
        )
    return html


def _filter_bar() -> str:
    buttons = [
        ("All",                    "all",  "active-all"),
        ("Active Product Builder", "Active Product Builder", "active-apb"),
        ("Early Trajectory",       "Early Trajectory",       "active-et"),
        ("Hobbyist",               "Hobbyist",               "active-hob"),
        ("Already Known",          "Already Known",          "active-ak"),
    ]
    parts = []
    for i, (label, filt, active_cls) in enumerate(buttons):
        cls = "filter-btn" + (" active-all" if i == 0 else "")
        parts.append(
            f'<button class="{cls}" data-filter="{_esc(filt)}" data-active="{active_cls}">'
            f"{_esc(label)}</button>"
        )
    return "".join(parts)


def _render_row(result: dict, idx: int) -> str:
    username     = result.get("username", "")
    profile_type = result.get("profile_type", "Hobbyist")
    flags        = result.get("flags", {})
    followers    = result.get("follower_count", 0)
    age          = result.get("account_age_days", 0)
    github_url   = result.get("github_url", f"https://github.com/{username}")
    reason       = result.get("classification_reason", "")

    bg, fg, border = TYPE_COLORS.get(profile_type, TYPE_COLORS["Hobbyist"])
    badge = (
        f'<span class="type-badge" '
        f'style="background:{bg};color:{fg};border-color:{border}">'
        f"{_esc(profile_type)}</span>"
    )

    pills = "".join(
        f'<span class="pill {"pill-on" if flags.get(k) else "pill-off"}">'
        f"{_esc(label)}</span>"
        for k, label in FLAG_META.items()
    )

    avatar_url = f"https://github.com/{_esc(username)}.png?size=40"
    profile_link = f"https://github.com/{_esc(username)}"

    main_row = (
        f'<tr class="data-row" data-type="{_esc(profile_type)}" data-idx="{idx}">\n'
        f'  <td><img class="avatar" src="{avatar_url}" alt="" loading="lazy"></td>\n'
        f'  <td><a class="username-link" href="{profile_link}" target="_blank" '
        f'rel="noopener noreferrer">@{_esc(username)}</a></td>\n'
        f"  <td>{badge}</td>\n"
        f'  <td><div class="pills">{pills}</div></td>\n'
        f'  <td class="center">{followers:,}</td>\n'
        f'  <td class="center">{age:,}</td>\n'
        f'  <td class="center shortlist-cell">'
        f'<input class="shortlist-cb" type="checkbox" data-idx="{idx}" '
        f'aria-label="Shortlist {_esc(username)}"></td>\n'
        f"</tr>"
    )

    flag_details = "".join(
        f'<div class="detail-flag">'
        f'<span class="flag-dot {"on" if flags.get(k) else "off"}"></span>'
        f'<span style="color:{"#e6edf3" if flags.get(k) else "#484f58"}">{_esc(label)}</span>'
        f"</div>"
        for k, label in FLAG_META.items()
    )

    detail_row = (
        f'<tr class="detail-row hidden" id="detail-{idx}">\n'
        f'  <td colspan="7">\n'
        f'    <div class="detail-inner">\n'
        f"      <strong>Classification reason:</strong> {_esc(reason)}<br>\n"
        f'      <div class="detail-grid" style="margin-top:.65rem">{flag_details}</div>\n'
        f"    </div>\n"
        f"  </td>\n"
        f"</tr>"
    )

    return main_row + "\n" + detail_row


def _esc(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
