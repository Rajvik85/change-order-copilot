"""Shared visual system for the Streamlit product."""

APP_CSS = """
<style>
:root {
  --navy: #10243e;
  --navy-2: #183b5b;
  --amber: #d89414;
  --paper: #f7f9fc;
  --blue: #0072b2;
  --green: #007a5e;
  --red: #b4472d;
}
.stApp { background: var(--paper); }
.block-container { max-width: 1180px; padding-top: 2rem; padding-bottom: 3rem; }
.hero {
  background: linear-gradient(130deg, #10243e 0%, #183b5b 72%, #2b5877 100%);
  color: white; border-radius: 18px; padding: 2.2rem 2.4rem; margin-bottom: 1.25rem;
  box-shadow: 0 12px 28px rgba(16,36,62,.16);
}
.hero h1 { color: white; font-size: 2.45rem; line-height: 1.08; margin-bottom: .65rem; }
.hero p { color: #dbe8f3; font-size: 1.08rem; max-width: 760px; }
.eyebrow { color: #f3bd55; font-weight: 750; letter-spacing: .09em; text-transform: uppercase; }
.feature-card, .finding-card, .status-card {
  background: white; border: 1px solid #dbe4ed; border-radius: 14px;
  padding: 1rem 1.15rem; min-height: 128px; box-shadow: 0 3px 12px rgba(16,36,62,.05);
}
.feature-card h3 { margin-top: .15rem; color: var(--navy); }
.status-card { min-height: auto; border-left: 5px solid var(--blue); }
.finding-critical { border-left: 6px solid #b4472d; }
.finding-high { border-left: 6px solid #d89414; }
.finding-medium { border-left: 6px solid #0072b2; }
.metric-note { color: #526579; font-size: .82rem; }
.provisional {
  background: #fff4d6; border: 1px solid #d89414; border-radius: 10px;
  padding: .85rem 1rem; color: #563e0b; font-weight: 650;
}
.app-footer { color: #66788a; text-align: center; font-size: .78rem; margin-top: 2rem; }
div[data-testid="stMetric"] {
  background: white; border: 1px solid #dbe4ed; padding: .85rem;
  border-radius: 12px; box-shadow: 0 2px 9px rgba(16,36,62,.05);
}
button[kind="primary"] { font-weight: 700; }
@media (max-width: 780px) {
  .hero { padding: 1.45rem; }
  .hero h1 { font-size: 1.9rem; }
}
</style>
"""
