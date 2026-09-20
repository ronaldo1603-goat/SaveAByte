import streamlit as st

FONT_URL = ("https://fonts.googleapis.com/css2?"
            "family=Be+Vietnam+Pro:wght@400;500;600;700&display=swap")

TRAY_MARK = (
    '<svg width="38" height="30" viewBox="0 0 38 30" fill="none" aria-hidden="true">'
    '<g stroke="currentColor" stroke-width="1.8" stroke-linecap="square">'
    '<path d="M2 2 H36 V28 H2 Z"/>'
    '<path d="M15 2 V28"/>'
    '<path d="M15 15 H36"/>'
    '<path d="M25.5 2 V15"/>'
    '<path d="M25.5 15 V28"/>'
    '</g></svg>'
)

_CSS = """
:root{
  --leaf:#2F6B4F;
  --leaf-dark:#24523D;
  --edge:#C9D1CB;
  --well:#FFFFFF;
  --ink:#1B2320;
  --muted:#5E6A66;
  --track:#E4E8E5;
  --fill-low:#9CB3A6;
  --fill-mid:#D9A441;
  --fill-high:#A8422E;
}

html, body, [class*="st-"], button, input, textarea, select,
h1, h2, h3, h4, p, div, span, label{
  font-family:"Be Vietnam Pro", system-ui, -apple-system, sans-serif !important;
}

[data-testid="stIconMaterial"],
.material-icons, .material-icons-outlined,
.material-symbols-rounded, .material-symbols-outlined,
span[class*="material"], i[class*="material"]{
  font-family:"Material Symbols Rounded","Material Symbols Outlined",
              "Material Icons" !important;
}

h1{ font-size:1.55rem !important; font-weight:700 !important;
    letter-spacing:-0.015em; color:var(--ink); }
h2, h3{ font-size:1.12rem !important; font-weight:600 !important;
        letter-spacing:-0.01em; color:var(--ink); margin-top:2rem !important; }

[data-testid="stMetricValue"], [data-testid="stDataFrame"],
[data-testid="stTable"], .vd-val{ font-variant-numeric:tabular-nums; }

.block-container,
[data-testid="stMainBlockContainer"],
[data-testid="stAppViewBlockContainer"]{
  max-width:1040px; padding-top:4.5rem !important; padding-bottom:3rem !important;
}

[data-testid="stSidebarNav"] a span{ font-size:.92rem; }
[data-testid="stSidebarNav"] a[aria-current="page"] span{
  color:var(--leaf) !important; font-weight:600 !important;
}

[data-testid="stMetric"]{
  background:var(--well);
  border:1px solid var(--edge);
  border-top:3px solid var(--leaf);
  padding:.85rem .95rem 1rem;
}
[data-testid="stMetricLabel"] p{
  font-size:.86rem !important; font-weight:500 !important; color:var(--muted) !important;
}
[data-testid="stMetricValue"]{
  font-size:1.65rem !important; font-weight:700 !important; color:var(--ink) !important;
}

.stButton > button{
  min-height:3.1rem;
  font-size:1rem !important; font-weight:600 !important;
  border:1px solid var(--leaf) !important; border-radius:2px !important;
  background:var(--leaf) !important; color:#FFFFFF !important;
}
.stButton > button:hover{
  background:var(--leaf-dark) !important; border-color:var(--leaf-dark) !important;
  color:#FFFFFF !important;
}
.stButton > button:active{ background:var(--ink) !important; }

[data-testid="stDataFrame"]{ border:1px solid var(--edge); }
[data-testid="stFileUploaderDropzone"]{
  background:var(--well) !important; border:1px dashed var(--edge) !important;
}

hr, [data-testid="stDivider"] hr{ border-color:var(--edge) !important; }

.vd-band{
  display:flex; align-items:center; gap:.8rem; color:var(--leaf);
  border-bottom:3px solid var(--leaf); padding-bottom:.8rem; margin-bottom:1.4rem;
}
.vd-band svg{ flex:none; }
.vd-title{ font-weight:700; font-size:1.2rem; color:var(--ink); line-height:1.15; }
.vd-sub{ font-size:.85rem; color:var(--muted); margin-top:.12rem; }

.vd-call{
  background:var(--well); border:1px solid var(--edge);
  border-left:4px solid var(--leaf);
  padding:1rem 1.2rem; margin:0 0 1.5rem;
  font-size:1.06rem; line-height:1.5; color:var(--ink);
}
.vd-call b{ font-weight:600; }
.vd-when{ display:block; font-size:.82rem; color:var(--muted); margin-top:.45rem; }

.vd-tray{
  display:grid; grid-template-columns:repeat(auto-fit,minmax(158px,1fr));
  gap:1px; background:var(--edge); border:1px solid var(--edge);
}
.vd-well{ background:var(--well); padding:.9rem .95rem 1rem; }
.vd-dish{ font-weight:600; font-size:.94rem; color:var(--ink); }
.vd-val{ font-size:1.6rem; font-weight:700; color:var(--ink); line-height:1.25; margin-top:.15rem; }
.vd-pm{ font-size:.8rem; font-weight:400; color:var(--muted); }
.vd-bar{ height:6px; background:var(--track); margin-top:.6rem; }
.vd-bar span{ display:block; height:100%; }
.vd-note{ font-size:.78rem; color:var(--muted); margin-top:.45rem; line-height:1.35; }

.vd-empty{
  background:var(--well); border:1px dashed var(--edge);
  padding:2rem 1.4rem; text-align:center; color:var(--muted);
}
.vd-empty b{ display:block; color:var(--ink); font-weight:600;
             font-size:1rem; margin-bottom:.35rem; }

button:focus-visible, a:focus-visible, [role="button"]:focus-visible{
  outline:2px solid var(--leaf) !important; outline-offset:2px;
}

@media (max-width:640px){
  .vd-val{ font-size:1.35rem; }
  .vd-call{ font-size:1rem; }
  [data-testid="stMetricValue"]{ font-size:1.35rem !important; }
}
@media (prefers-reduced-motion:reduce){
  *{ animation:none !important; transition:none !important; }
}
"""


def inject() -> None:
    st.markdown(f'<style>@import url("{FONT_URL}");{_CSS}</style>',
                unsafe_allow_html=True)


def band(subtitle: str) -> None:
    st.markdown(
        f'<div class="vd-band">{TRAY_MARK}'
        f'<div><div class="vd-title">Vừa Đủ</div>'
        f'<div class="vd-sub">{subtitle}</div></div></div>',
        unsafe_allow_html=True,
    )


def call(text: str, when: str = "") -> None:
    extra = f'<span class="vd-when">{when}</span>' if when else ""
    st.markdown(f'<div class="vd-call">{text}{extra}</div>', unsafe_allow_html=True)


def _fill_color(v: float) -> str:
    if v < 0.25:
        return "var(--fill-low)"
    if v < 0.50:
        return "var(--fill-mid)"
    return "var(--fill-high)"


def wells(items: list[dict]) -> None:
    parts = ['<div class="vd-tray">']
    for it in items:
        v = it.get("value")
        if v is None:
            val, bar = '<div class="vd-val">—</div>', '<div class="vd-bar"></div>'
        else:
            v = float(v)
            pm = (f'<span class="vd-pm"> ± {it["mae"]:.0%}</span>'
                  if it.get("mae") is not None else "")
            val = f'<div class="vd-val">{v:.0%}{pm}</div>'
            bar = (f'<div class="vd-bar"><span style="width:'
                   f'{min(max(v, 0.0), 1.0) * 100:.0f}%;'
                   f'background:{_fill_color(v)}"></span></div>')
        note = f'<div class="vd-note">{it["note"]}</div>' if it.get("note") else ""
        parts.append(f'<div class="vd-well"><div class="vd-dish">{it["label"]}</div>'
                     f'{val}{bar}{note}</div>')
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)


def empty(title: str, hint: str) -> None:
    st.markdown(f'<div class="vd-empty"><b>{title}</b>{hint}</div>',
                unsafe_allow_html=True)
