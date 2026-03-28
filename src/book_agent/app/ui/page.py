from __future__ import annotations

from html import escape


def build_homepage_html(*, app_name: str, app_version: str, api_prefix: str) -> str:
    docs_href = f"{api_prefix}/docs"
    openapi_href = f"{api_prefix}/openapi.json"
    health_href = f"{api_prefix}/health"
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta
      name="description"
      content="book-agent backend service entry. The production workspace now runs as a standalone React and Vite frontend."
    />
    <title>{escape(app_name)} service entry</title>
    <style>
      :root {{
        color-scheme: light;
        --bg: #eef1f4;
        --surface: rgba(250, 252, 253, 0.96);
        --surface-strong: #ffffff;
        --ink: #14212b;
        --ink-soft: #566472;
        --line: rgba(20, 33, 43, 0.12);
        --accent: #17384b;
        --accent-soft: rgba(23, 56, 75, 0.08);
        --shadow: 0 24px 60px rgba(17, 31, 42, 0.08);
        --radius: 28px;
        --card-radius: 18px;
        --sans: "Manrope", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
      }}

      * {{
        box-sizing: border-box;
      }}

      body {{
        margin: 0;
        min-height: 100vh;
        display: grid;
        place-items: center;
        padding: 24px;
        background:
          radial-gradient(circle at top left, rgba(23, 56, 75, 0.1), transparent 22%),
          linear-gradient(180deg, #f8fafb 0%, #ecf1f4 100%);
        color: var(--ink);
        font-family: var(--sans);
      }}

      main {{
        width: min(860px, 100%);
        padding: 36px;
        border: 1px solid rgba(255, 255, 255, 0.88);
        border-radius: var(--radius);
        background: linear-gradient(180deg, var(--surface-strong), var(--surface));
        box-shadow: var(--shadow);
      }}

      .eyebrow {{
        color: var(--accent);
        font-size: 12px;
        font-weight: 800;
        letter-spacing: 0.16em;
        text-transform: uppercase;
      }}

      h1 {{
        margin: 10px 0 12px;
        font-size: clamp(2rem, 4vw, 3rem);
        line-height: 0.98;
        letter-spacing: -0.05em;
      }}

      p {{
        margin: 0;
        color: var(--ink-soft);
        font-size: 16px;
        line-height: 1.7;
      }}

      .meta {{
        display: inline-flex;
        align-items: center;
        gap: 10px;
        margin-top: 18px;
        padding: 10px 14px;
        border-radius: 999px;
        background: var(--accent-soft);
        color: var(--accent);
        font-size: 13px;
        font-weight: 700;
      }}

      .link-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 14px;
        margin-top: 28px;
      }}

      .link-card {{
        display: grid;
        gap: 10px;
        min-height: 144px;
        padding: 18px;
        border: 1px solid var(--line);
        border-radius: var(--card-radius);
        background: rgba(255, 255, 255, 0.78);
        color: inherit;
        text-decoration: none;
      }}

      .link-card:hover,
      .link-card:focus-visible {{
        border-color: rgba(23, 56, 75, 0.28);
      }}

      .link-label {{
        color: var(--accent);
        font-size: 12px;
        font-weight: 800;
        letter-spacing: 0.14em;
        text-transform: uppercase;
      }}

      .link-title {{
        font-size: 20px;
        font-weight: 750;
      }}

      .mono {{
        font-family: "JetBrains Mono", "SFMono-Regular", monospace;
        font-size: 13px;
      }}
    </style>
  </head>
  <body>
    <main>
      <div class="eyebrow">Book Agent Service</div>
      <h1>{escape(app_name)}</h1>
      <p>
        This backend now serves the translation APIs and runtime only. The user-facing workspace
        is expected to run as a standalone React/Vite frontend.
      </p>
      <div class="meta">Version {escape(app_version)} · API prefix {escape(api_prefix)}</div>
      <div class="link-grid">
        <a class="link-card" href="{escape(docs_href)}">
          <div class="link-label">API Docs</div>
          <div class="link-title">Swagger UI</div>
          <div class="mono">{escape(docs_href)}</div>
        </a>
        <a class="link-card" href="{escape(openapi_href)}">
          <div class="link-label">OpenAPI</div>
          <div class="link-title">Schema JSON</div>
          <div class="mono">{escape(openapi_href)}</div>
        </a>
        <a class="link-card" href="{escape(health_href)}">
          <div class="link-label">Health</div>
          <div class="link-title">Service Status</div>
          <div class="mono">{escape(health_href)}</div>
        </a>
      </div>
    </main>
  </body>
</html>
"""
