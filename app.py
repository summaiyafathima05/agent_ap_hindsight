"""
AP Agent — Web Dashboard (Flask) powered by Hindsight.

This is a real website (not a mockup) whose backend calls Hindsight for
every recall/retain, so what you see in the browser is driven by actual
memory operations.

No Docker needed: with GROQ_API_KEY set, this starts an embedded Hindsight
inside Python. (Docker / Hindsight Cloud also supported, see README.)

Run:
pip install -r requirements.txt
python app.py
Then open in your browser:
http://localhost:5000
"""

import os
import atexit
from flask import Flask, jsonify, request, render_template_string
from hindsight_client import Hindsight

app = Flask(__name__)
BANK_ID = os.environ.get("BANK_ID", "ap-agent-demo")


def make_client():
	"""Pick how to reach Hindsight (all real Hindsight, all free options):
	1. HINDSIGHT_API_KEY set -> Hindsight Cloud
	2. HINDSIGHT_URL set -> your own Hindsight server (e.g. Docker)
	3. otherwise -> EMBEDDED Hindsight started right here in
	Python (no Docker), using your Groq key.
	"""
	api_key = os.environ.get("HINDSIGHT_API_KEY")
	if api_key:
		print("Using Hindsight Cloud")
		return Hindsight(base_url="https://api.hindsight.vectorize.io", api_key=api_key)

	url = os.environ.get("HINDSIGHT_URL")
	if url:
		print(f"Using Hindsight server at {url}")
		return Hindsight(base_url=url)

	groq_key = os.environ.get("GROQ_API_KEY")
	if not groq_key:
		raise SystemExit("Set GROQ_API_KEY first (see README). Get a free key at console.groq.com")
	print("Starting embedded Hindsight (no Docker). First start can take a few minutes...")
	from hindsight import HindsightServer
	server = HindsightServer(
		llm_provider="groq",
		llm_model=os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b"),
		llm_api_key=groq_key,
	)
	server.__enter__()
	atexit.register(lambda: server.__exit__(None, None, None))
	print(f"Embedded Hindsight running at {server.url}")
	return Hindsight(base_url=server.url)


client = make_client()

INVOICES = [
{"id": "INV-001", "vendor": "Acme Supplies", "po_amount": 49500, "invoice_amount": 50000},
{"id": "INV-002", "vendor": "Bright Traders", "po_amount": 20000, "invoice_amount": 19800},
{"id": "INV-003", "vendor": "Zenith Co", "po_amount": 15000, "invoice_amount": 15000},
]


@app.route("/")
def index():
	return render_template_string(INDEX_HTML)


@app.route("/api/invoices")
def get_invoices():
	return jsonify(INVOICES)


@app.route("/api/recall", methods=["POST"])
def recall():
		data = request.get_json()
		vendor = data["vendor"]
		diff = data["diff"]
		query = f"{vendor} invoice discrepancy of {diff} rupees - how was it resolved?"
		try:
				result = client.recall(bank_id=BANK_ID, query=query)
				matches = getattr(result, "results", result) or []
				if matches:
						top = matches[0]
						text = getattr(top, "text", str(top))
						return jsonify({"found": True, "resolution": text})
				return jsonify({"found": False})
		except Exception as e:
				return jsonify({"found": False, "error": str(e)}), 200


@app.route("/api/retain", methods=["POST"])
def retain():
	data = request.get_json()
	vendor = data["vendor"]
	diff = data["diff"]
	resolution = data["resolution"]
	try:
		client.retain(
			bank_id=BANK_ID,
			content=f"Vendor {vendor} had an invoice discrepancy of {diff} rupees. Resolution: {resolution}",
		)
		return jsonify({"ok": True})
	except Exception as e:
		return jsonify({"ok": False, "error": str(e)}), 200


@app.route("/api/reflect", methods=["POST"])
def reflect():
	try:
		result = client.reflect(
			bank_id=BANK_ID,
			query="Summarize the vendor invoice discrepancy patterns learned so far and how each is resolved.",
		)
		text = getattr(result, "text", str(result))
		return jsonify({"ok": True, "text": text})
	except Exception as e:
		return jsonify({"ok": False, "error": str(e)}), 200


INDEX_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AP Agent — Powered by Hindsight</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root{--paper:#F6F3EA;--ink:#1E2A24;--line:#D9D2BF;--green:#3E6B52;--green-bg:#E4EEE6;
--amber:#B4791F;--amber-bg:#F5E9D6;--muted:#7A7566;}
*{box-sizing:border-box;}
body{margin:0;background:var(--paper);color:var(--ink);font-family:'IBM Plex Mono',monospace;}
h1{font-family:'Source Serif 4',serif;font-size:26px;margin:0;}
.wrap{max-width:760px;margin:0 auto;padding:32px 20px 60px;}
p.sub{color:var(--muted);font-size:14px;max-width:56ch;line-height:1.5;margin:8px 0 0;}
.badge{display:inline-block;font-size:11px;padding:2px 8px;border:1px solid var(--line);border-radius:3px;margin-left:8px;color:var(--muted);}
.ledger{border-top:2px solid var(--ink);border-bottom:2px solid var(--ink);margin:20px 0;}
.row{display:grid;grid-template-columns:1fr 90px 90px 90px 120px;gap:8px;padding:10px 4px;
border-bottom:1px solid var(--line);font-size:13px;align-items:center;}
.row.head{font-weight:600;color:var(--muted);font-size:11px;}
.row:last-child{border-bottom:none;}
.num{text-align:right;font-variant-numeric:tabular-nums;}
.status{padding:3px 8px;border-radius:3px;font-size:11px;justify-self:start;white-space:nowrap;}
.status.pending{background:var(--line);color:var(--muted);}
.status.escalated{background:var(--amber-bg);color:var(--amber);}
.status.resolved,.status.exact{background:var(--green-bg);color:var(--green);}
button{font-family:'IBM Plex Mono',monospace;font-size:13px;padding:10px 16px;border:1.5px solid var(--ink);
background:transparent;color:var(--ink);border-radius:3px;cursor:pointer;}
button:hover{background:var(--ink);color:var(--paper);}
button:disabled{opacity:.35;cursor:default;}
.controls{display:flex;gap:10px;margin:20px 0;flex-wrap:wrap;}
.prompt{display:none;background:var(--amber-bg);border:1px solid var(--amber);border-radius:4px;padding:14px;margin:16px 0;font-size:13px;}
.prompt.show{display:block;}
.prompt input{width:100%;font-family:'IBM Plex Mono',monospace;font-size:13px;padding:8px;
border:1px solid var(--line);border-radius:3px;background:var(--paper);color:var(--ink);margin-top:8px;}
section{margin-top:30px;}
section h2{font-family:'Source Serif 4',serif;font-size:16px;margin-bottom:10px;}
.log{background:#1B2A3A;color:var(--paper);border-radius:4px;padding:14px 16px;font-size:12.5px;
line-height:1.7;height:170px;overflow-y:auto;}
.log .tag{color:#8FCBA8;}
.reflection{background:var(--green-bg);border:1px solid var(--green);border-radius:4px;padding:14px;
font-size:13px;line-height:1.6;display:none;}
.reflection.show{display:block;}
</style>
</head>
<body>
<div class="wrap">
<header>
<h1>AP Agent <span class="badge" id="statusBadge">connecting to Hindsight...</span></h1>
<p class="sub">Invoices with a discrepancy escalate once. Hindsight retains the resolution — the next time the same pattern appears, the agent resolves it on its own.</p>
</header>

<div class="ledger" id="ledger"></div>

<div class="prompt" id="prompt">
<label id="promptLabel"></label>
<input id="promptInput" type="text" placeholder="How should this be resolved?">
<div style="margin-top:10px;"><button id="promptGo">Save resolution to Hindsight</button></div>
</div>

<div class="controls">
<button id="stepBtn">Process next invoice</button>
<button id="reflectBtn">Ask Hindsight to reflect</button>
</div>

<section>
<h2>Agent log</h2>
<div class="log" id="log"></div>
</section>

<section>
<h2>Hindsight reflection</h2>
<div class="reflection" id="reflection"></div>
</section>
</div>

<script>
let invoices = [];
let idx = 0;
let round = 1;
let pending = null;

const ledgerEl = document.getElementById('ledger');
const logEl = document.getElementById('log');
const promptEl = document.getElementById('prompt');
const promptLabel = document.getElementById('promptLabel');
const promptInput = document.getElementById('promptInput');
const statusBadge = document.getElementById('statusBadge');
const reflectionEl = document.getElementById('reflection');

function log(text, tag){
const div = document.createElement('div');
div.innerHTML = tag ? `<span class="tag">[${tag}]</span> ${text}` : text;
logEl.appendChild(div);
logEl.scrollTop = logEl.scrollHeight;
}

function renderLedger(){
let html = `<div class="row head"><div>VENDOR / INVOICE</div><div class="num">PO</div><div class="num">INVOICE</div><div class="num">DIFF</div><div>STATUS</div></div>`;
invoices.forEach(inv => {
const diff = inv.invoice_amount - inv.po_amount;
const label = {pending:'—', exact:'auto-approved', escalated:'escalated', resolved:'auto-resolved'}[inv.status || 'pending'];
html += `<div class="row">
<div>${inv.vendor}<br><span style="color:var(--muted);font-size:11px">${inv.id}</span></div>
<div class="num">₹${inv.po_amount.toLocaleString()}</div>
<div class="num">₹${inv.invoice_amount.toLocaleString()}</div>
<div class="num">${diff===0?'—':(diff>0?'+':'')+'₹'+diff}</div>
<div class="status ${inv.status || 'pending'}">${label}</div>
</div>`;
});
ledgerEl.innerHTML = html;
}

async function loadInvoices(){
const res = await fetch('/api/invoices');
invoices = await res.json();
invoices.forEach(i => i.status = 'pending');
statusBadge.textContent = 'connected';
renderLedger();
}

async function processCurrent(){
if(idx >= invoices.length){
if(round === 1){
round = 2;
idx = 0;
invoices.forEach(i => i.status = 'pending');
log('Round 2: the same invoices arrive again.', 'round 2');
renderLedger();
} else {
document.getElementById('stepBtn').disabled = true;
log('Demo complete.', 'done');
}
return;
}

const inv = invoices[idx];
const diff = inv.invoice_amount - inv.po_amount;

if(diff === 0){
inv.status = 'exact';
log(`${inv.vendor}: matches PO exactly. Auto-approved.`, inv.id);
idx++; renderLedger();
processCurrent();
return;
}

log(`${inv.vendor}: checking Hindsight for a past resolution...`, inv.id);
const res = await fetch('/api/recall', {method:'POST', headers:{'Content-Type':'application/json'},
body: JSON.stringify({vendor: inv.vendor, diff})});
const data = await res.json();

if(data.found){
inv.status = 'resolved';
log(`${inv.vendor}: recalled — "${data.resolution}". Auto-resolved.`, inv.id);
idx++; renderLedger();
} else {
pending = inv;
promptLabel.textContent = `${inv.vendor}: new ₹${diff} discrepancy. How should this be resolved?`;
promptEl.classList.add('show');
promptInput.value = '';
promptInput.focus();
log(`${inv.vendor}: new pattern. Escalating to a human...`, inv.id);
}
}

document.getElementById('stepBtn').addEventListener('click', processCurrent);

document.getElementById('promptGo').addEventListener('click', async () => {
const text = promptInput.value.trim();
if(!text || !pending) return;
const diff = pending.invoice_amount - pending.po_amount;
await fetch('/api/retain', {method:'POST', headers:{'Content-Type':'application/json'},
body: JSON.stringify({vendor: pending.vendor, diff, resolution: text})});
pending.status = 'escalated';
log('Resolution saved to Hindsight.', pending.id);
promptEl.classList.remove('show');
pending = null;
idx++;
renderLedger();
});

document.getElementById('reflectBtn').addEventListener('click', async () => {
log('Asking Hindsight to reflect on everything learned so far...', 'reflect');
const res = await fetch('/api/reflect', {method:'POST'});
const data = await res.json();
reflectionEl.textContent = data.ok ? data.text : ('Error: ' + data.error);
reflectionEl.classList.add('show');
});

loadInvoices();
log('Click "Process next invoice" to begin.', 'ready');
</script>
</body>
</html>
"""

if __name__ == "__main__":
	app.run(debug=False, use_reloader=False, port=5000)

