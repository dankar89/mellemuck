"""Write BUILD_DIR/review.html: a local page for reviewing the HD art against the original.

  review_page.py BUILD_DIR

Open it through tools/review_server.py to save flags into the project
(BUILD_DIR/review-flags.json), or as a plain file (flags stay in the browser,
with an export button). One toggle (button or T) flips every image between
original and HD; originals get the same transparency the game gives them
(matte = flood fill from the border, bgtrans = all pure white), so halos and
holes can be compared fairly on any background. Those originals are written
as files to BUILD_DIR/orig_ink/ because browsers refuse to read pixels of
local images from script on a page opened from disk.
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from alpha_upscale import ink_mask  # noqa: E402

PAGE = r"""<!doctype html>
<html lang="sv"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>HD Art Review</title>
<style>
:root { --bg:#16181c; --panel:#20242a; --fg:#e8e6e1; --muted:#9aa0a8; --accent:#f0a33a; --line:#333a42; }
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--fg); font:14px/1.4 system-ui, sans-serif; }
header { position:sticky; top:0; z-index:5; background:var(--panel); border-bottom:1px solid var(--line);
  padding:10px 16px; display:flex; flex-wrap:wrap; gap:8px 16px; align-items:center; }
header h1 { font-size:16px; margin:0 8px 0 0; }
label { color:var(--muted); display:flex; gap:6px; align-items:center; }
select, input, button { background:#2b3038; color:var(--fg); border:1px solid var(--line); border-radius:6px; padding:5px 8px; font:inherit; }
button.toggle { background:var(--accent); color:#1a1a1a; border:none; font-weight:600; min-width:150px; }
#count { color:var(--muted); margin-left:auto; }
main { display:grid; grid-template-columns:repeat(auto-fill, minmax(240px, 1fr)); gap:12px; padding:16px; }
.card { background:var(--panel); border:1px solid var(--line); border-radius:8px; overflow:hidden; cursor:zoom-in; }
.stage { height:200px; display:flex; align-items:center; justify-content:center; background:var(--stage); background-size:cover; background-position:center; }
.stage canvas, .stage img { max-width:100%; max-height:100%; object-fit:contain; }
.stage canvas { image-rendering:pixelated; }
.meta { padding:6px 8px; font-size:12px; color:var(--muted); display:flex; justify-content:space-between; gap:6px; }
.meta b { color:var(--fg); font-weight:600; }
.tag { border:1px solid var(--line); border-radius:4px; padding:0 4px; }
#zoom { position:fixed; inset:0; background:rgba(0,0,0,.85); display:none; z-index:10; overflow:auto; cursor:zoom-out; }
#zoom .stage { height:auto; min-height:100vh; padding:24px; }
#zoom .stage img, #zoom .stage canvas { max-width:none; max-height:none; }
.bg-dark { --stage:#2a2e33; } .bg-light { --stage:#e9e4d8; }
.bg-checker { --stage: repeating-conic-gradient(#555 0 25%, #888 0 50%) 0 0/24px 24px; }
.flagbtn { background:none; border:none; color:var(--muted); cursor:pointer; padding:0 2px; font-size:15px; line-height:1; }
.flagbtn:hover { color:var(--fg); }
.card.flagged { border-color:#e5484d; box-shadow:inset 0 0 0 1px #e5484d; }
.card.flagged .flagbtn { color:#e5484d; }
.note { padding:0 8px 6px; font-size:12px; color:#ff9a9e; overflow-wrap:anywhere; }
.note:empty { display:none; }
#flaginfo { color:var(--muted); }
#zoombar { position:sticky; top:0; padding:8px 16px; background:rgba(0,0,0,.6); color:var(--fg); font-size:13px; }
@media (max-width:600px) { main { grid-template-columns:repeat(auto-fill, minmax(150px, 1fr)); padding:8px; } .stage { height:140px; } }
</style></head>
<body class="bg-dark">
<header>
  <h1>HD Art Review</h1>
  <button class="toggle" id="toggle">Showing: HD (T)</button>
  <label>Background <select id="bg"><option value="dark">Dark</option><option value="light">Light</option>
    <option value="checker">Checker</option><option value="garage">Garage</option></select></label>
  <label>Category <select id="cat"><option value="">All</option><option>background</option><option>painted</option><option>lineart</option></select></label>
  <label>Cast <select id="cast"><option value="">All</option></select></label>
  <label>Variant <select id="variant"><option value="">All</option><option>copy</option><option>matte</option><option>bgtrans</option></select></label>
  <label><input type="checkbox" id="enclosed"> Enclosed white only</label>
  <label>Name <input id="q" size="10" placeholder="20b199"></label>
  <label><input type="checkbox" id="flaggedOnly"> Flagged only</label>
  <span id="flaginfo"></span>
  <button id="export" hidden>Export flags</button>
  <span id="count"></span>
</header>
<main id="grid"></main>
<div id="zoom"></div>
<script>
const DATA = __DATA__;
const GARAGE = __GARAGE__;
let showHD = true;
// Flags: saved to the server (review_server.py -> review-flags.json) when served
// over http, otherwise kept in this browser with an export button.
const SERVER = location.protocol.startsWith('http');
let FLAGS = {};
const flagKey = (e, v) => `${e.cast}/${e.member}/${v}`;
async function loadFlags() {
  if (SERVER) { try { FLAGS = await (await fetch('api/flags')).json(); } catch { FLAGS = {}; } return; }
  try { FLAGS = JSON.parse(localStorage.getItem('mulle-review-flags') || '{}'); } catch { FLAGS = {}; }
  document.getElementById('export').hidden = false;
}
function saveFlags() {
  updateFlagInfo();
  if (SERVER) {
    fetch('api/flags', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(FLAGS) })
      .then(r => { if (!r.ok) throw new Error(r.status); })
      .catch(() => alert('Could not save the flags. Is review_server.py still running?'));
  } else { try { localStorage.setItem('mulle-review-flags', JSON.stringify(FLAGS)); } catch {} }
}
function updateFlagInfo() {
  const n = Object.keys(FLAGS).length;
  document.getElementById('flaginfo').textContent = `${n} flagged` + (SERVER ? ' · saved to review-flags.json' : ' · stored in this browser');
}
function toggleFlag(e, v) {
  const k = flagKey(e, v), cur = FLAGS[k];
  const note = prompt(cur ? 'Edit the note. Clear it and press OK to remove the flag.'
                          : `Flag ${e.name || '#' + e.member} (${e.cast}, ${v}). What's wrong? (optional)`, cur ? cur.note : '');
  if (note === null) return false;
  if (cur && note.trim() === '') delete FLAGS[k];
  else FLAGS[k] = { cast: e.cast, member: e.member, name: e.name, variant: v, hd: e.hd[v], note: note.trim(), time: new Date().toISOString() };
  saveFlags(); return true;
}
function decorate(card, e, v) {
  const f = FLAGS[flagKey(e, v)];
  card.classList.toggle('flagged', !!f);
  card.querySelector('.note').textContent = f ? (f.note || 'Flagged') : '';
}
document.getElementById('export').onclick = () => {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([JSON.stringify(FLAGS, null, 1)], { type: 'application/json' }));
  a.download = 'review-flags.json'; a.click();
};
const grid = document.getElementById('grid'), zoom = document.getElementById('zoom');

function visual(e, variant, hd) {
  const im = new Image(); im.loading = 'lazy';
  im.src = hd ? e.hd[variant] : e.orig[variant];
  if (!hd) im.style.imageRendering = 'pixelated';
  im.style.width = (e.width*3) + 'px'; im.style.height = (e.height*3) + 'px'; return im;
}

function render() {
  const cat = document.getElementById('cat').value, cast = document.getElementById('cast').value;
  const variant = document.getElementById('variant').value, enc = document.getElementById('enclosed').checked;
  const q = document.getElementById('q').value.trim().toLowerCase();
  const flaggedOnly = document.getElementById('flaggedOnly').checked;
  grid.innerHTML = ''; let n = 0;
  const io = new IntersectionObserver(entries => entries.forEach(en => {
    if (!en.isIntersecting) return; io.unobserve(en.target);
    const { e, v } = en.target._item; en.target.querySelector('.stage').append(visual(e, v, showHD));
  }), { rootMargin: '600px' });
  for (const e of DATA) {
    if (cat && e.category !== cat) continue; if (cast && e.cast !== cast) continue;
    if (enc && !e.enclosed_white) continue; if (q && !e.name.toLowerCase().includes(q)) continue;
    for (const v of Object.keys(e.hd || {})) {
      if (variant && v !== variant) continue;
      if (flaggedOnly && !FLAGS[flagKey(e, v)]) continue;
      const card = document.createElement('div'); card.className = 'card'; card._item = { e, v };
      card.innerHTML = `<div class="stage"></div><div class="meta"><span><b>${e.name || '#' + e.member}</b> ${e.cast}/${e.member}</span>
        <span><span class="tag">${v}</span> ${e.width}×${e.height}
        <button class="flagbtn" title="Flag as wrong (F when zoomed)">⚑</button></span></div><div class="note"></div>`;
      card.onclick = () => openZoom(e, v);
      card.querySelector('.flagbtn').onclick = ev => { ev.stopPropagation(); if (toggleFlag(e, v)) decorate(card, e, v); };
      decorate(card, e, v);
      grid.append(card); io.observe(card); n++;
    }
  }
  document.getElementById('count').textContent = `${n} images`;
}

function openZoom(e, v) {
  const f = FLAGS[flagKey(e, v)];
  zoom.innerHTML = `<div id="zoombar"><b>${e.name || '#' + e.member}</b> ${e.cast}/${e.member} · ${v} · ${showHD ? 'HD' : 'Original'}
    · T toggle · F ${f ? 'edit flag (' + (f.note || 'flagged') + ')' : 'flag as wrong'} · Esc close</div><div class="stage"></div>`;
  zoom.querySelector('.stage').append(visual(e, v, showHD));
  zoom.style.display = 'block'; zoom._item = { e, v };
}
zoom.onclick = () => { zoom.style.display = 'none'; zoom._item = null; };

function setToggle() {
  showHD = !showHD;
  document.getElementById('toggle').textContent = `Showing: ${showHD ? 'HD' : 'Original'} (T)`;
  if (zoom._item) openZoom(zoom._item.e, zoom._item.v);
  render();
}
document.getElementById('toggle').onclick = setToggle;
document.addEventListener('keydown', ev => {
  if (ev.target.tagName === 'INPUT') return;
  if (ev.key === 't' || ev.key === 'T') setToggle();
  if ((ev.key === 'f' || ev.key === 'F') && zoom._item) { const { e, v } = zoom._item; if (toggleFlag(e, v)) { openZoom(e, v); render(); } }
  if (ev.key === 'Escape') zoom.onclick();
});

document.getElementById('bg').onchange = ev => {
  const v = ev.target.value; document.body.className = 'bg-' + (v === 'garage' ? 'dark' : v);
  document.body.style.setProperty('--stage', v === 'garage' ? `url("${GARAGE}")` : '');
};
for (const id of ['cat', 'cast', 'variant', 'enclosed', 'flaggedOnly']) document.getElementById(id).onchange = render;
document.getElementById('q').oninput = render;
if (location.hash === '#original') { showHD = false; document.getElementById('toggle').textContent = 'Showing: Original (T)'; }
const castSel = document.getElementById('cast');
[...new Set(DATA.map(e => e.cast))].sort().forEach(c => castSel.append(new Option(c, c)));
loadFlags().then(() => { updateFlagInfo(); render(); });
</script></body></html>
"""


def main():
	build = Path(sys.argv[1])
	manifest = json.loads((build / "manifest.json").read_text())
	data = []
	for e in manifest:
		if not e.get("hd"):
			continue
		item = {k: e[k] for k in ("cast", "member", "name", "file", "width", "height", "category", "inks",
			"enclosed_white", "tiny", "hd")}
		item["orig"] = {}
		for variant in e["hd"]:
			rel = Path("orig_ink") / e["cast"] / f"{Path(e['file']).stem}.{variant}.png"
			if not (build / rel).exists():
				rgb = np.asarray(Image.open(build / e["file"]).convert("RGB"))
				(build / rel).parent.mkdir(parents=True, exist_ok=True)
				alpha = (ink_mask(rgb, variant) * 255).astype(np.uint8)
				Image.fromarray(np.dstack([rgb, alpha]), "RGBA").save(build / rel)
			item["orig"][variant] = rel.as_posix()
		data.append(item)
	garage = next((e["hd"]["copy"] for e in manifest if e["name"] == "03b001v0" and e.get("hd")), "")
	html = PAGE.replace("__DATA__", json.dumps(data)).replace("__GARAGE__", json.dumps(garage))
	(build / "review.html").write_text(html, encoding="utf-8")
	print(f"{build / 'review.html'}: {sum(len(e['hd']) for e in data)} images")


if __name__ == "__main__":
	main()
