import logging
from django.http import HttpResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rag.retrieval import search_events, get_stats, exact_events
from rag.pipeline import answer_question

logger = logging.getLogger(__name__)

HOME = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Cricket Log Semantic Search</title><style>
:root{font-family:system-ui,-apple-system,sans-serif;color:#172033;background:#f4f7fb}body{max-width:1100px;margin:0 auto;padding:24px}h1{margin-bottom:4px}.muted{color:#65718a}.panel{background:white;border:1px solid #dce3ed;border-radius:14px;padding:18px;margin:16px 0;box-shadow:0 2px 10px #1720330a}input,select,button{font:inherit;padding:10px;border:1px solid #ccd5e2;border-radius:8px}input{width:min(100%,560px)}button{background:#153e75;color:white;border:0;cursor:pointer}pre{white-space:pre-wrap;overflow-wrap:anywhere}.row{display:flex;gap:10px;flex-wrap:wrap;align-items:center}.event{border-top:1px solid #e7ebf1;padding:12px 0}.pill{font-size:.8rem;background:#edf3fc;padding:3px 8px;border-radius:20px}.error{color:#a11}.stats{display:flex;gap:12px;flex-wrap:wrap}.stat{background:#f2f6fb;border-radius:10px;padding:12px 16px}</style></head><body>
<h1>🏏 Cricket Log Semantic Search</h1><p class="muted">Search match commentary by meaning, filter event metadata, and ask grounded questions.</p>
<div class="panel"><h2>Dataset status</h2><div id="stats">Loading stats…</div></div>
<div class="panel"><h2>Semantic search</h2><form id="searchForm"><div class="row"><input id="query" placeholder="e.g. disputed decisions involving a wicket" required><button>Search events</button></div><p class="row"><label>Match <select id="match"><option value="">Any</option></select></label><label>Event <select id="event"><option value="">Any</option></select></label><label>Top results <select id="topk"><option>5</option><option>10</option><option>20</option></select></label></p></form><div id="results"></div></div>
<div class="panel"><h2>Ask the cricket logs</h2><form id="chatForm"><div class="row"><input id="question" placeholder="e.g. What types of events appear in the logs?" required><button>Ask</button></div></form><p id="answer"></p><div id="sources"></div></div>
<div class="panel"><h2>REST API</h2><p><code>GET /api/health/</code> · <code>GET /api/stats/</code> · <code>POST /api/search/</code> · <code>POST /api/chat/</code> · <code>GET /api/events/</code></p><p class="muted">Ingestion is a manual/offline command; no public ingestion endpoint is exposed.</p></div>
<script>
const el=id=>document.getElementById(id);const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function api(url,opts){const r=await fetch(url,opts);const j=await r.json();if(!r.ok)throw Error(j.error||r.statusText);return j}
function eventCard(e){return `<div class="event"><div class="row"><b>${esc(e.event_type)}</b><span class="pill">${esc(e.match_id)}</span><span class="pill">${esc(e.status)}</span><span class="muted">score ${Number(e.score||0).toFixed(3)}</span></div><p>${esc(e.commentary)}</p><small>Player: ${esc(e.player)} · Team: ${esc(e.team)} · Runs: ${esc(e.runs)} · Over: ${esc(e.over)} · ${esc(e.timestamp)}</small>${e.quality_flags?.length?`<p class="error">Quality flags: ${esc(e.quality_flags.join(', '))}</p>`:''}</div>`}
async function loadStats(){try{const s=await api('/api/stats/');el('stats').innerHTML=`<div class="stats"><div class="stat"><b>${s.total_events}</b><br>events</div><div class="stat"><b>${s.matches.length}</b><br>matches</div><div class="stat"><b>${s.event_types.length}</b><br>event types</div><div class="stat"><b>${s.quality_flagged_events}</b><br>flagged records</div></div>`;s.matches.forEach(v=>el('match').insertAdjacentHTML('beforeend',`<option>${esc(v)}</option>`));s.event_types.forEach(v=>el('event').insertAdjacentHTML('beforeend',`<option>${esc(v._id)}</option>`))}catch(e){el('stats').innerHTML=`<span class="error">${esc(e.message)}. Have you ingested the dataset?</span>`}}
el('searchForm').addEventListener('submit',async ev=>{ev.preventDefault();el('results').textContent='Searching…';try{const r=await api('/api/search/',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query:el('query').value,top_k:Number(el('topk').value),filters:{match_id:el('match').value,event_type:el('event').value}})});el('results').innerHTML=r.results.map(eventCard).join('')||'No matching events.'}catch(e){el('results').innerHTML=`<p class="error">${esc(e.message)}</p>`}});
el('chatForm').addEventListener('submit',async ev=>{ev.preventDefault();el('answer').textContent='Thinking…';el('sources').innerHTML='';try{const r=await api('/api/chat/',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:el('question').value,top_k:5})});el('answer').textContent=r.answer;el('sources').innerHTML='<h3>Retrieved evidence</h3>'+r.sources.map(eventCard).join('')}catch(e){el('answer').innerHTML=`<span class="error">${esc(e.message)}</span>`}});
loadStats();
</script></body></html>"""

class HomeView(APIView):
    authentication_classes = []
    permission_classes = []
    def get(self, request):
        return HttpResponse(HOME, content_type="text/html")

class HealthView(APIView):
    authentication_classes = []
    permission_classes = []
    def get(self, request):
        checks = {}
        try:
            from pymongo import MongoClient
            import os
            c=MongoClient(os.getenv("MONGODB_URI","mongodb://mongodb:27017"),serverSelectionTimeoutMS=1500); c.admin.command("ping"); c.close(); checks["mongodb"]="ok"
        except Exception as exc:
            checks["mongodb"]="error"; logger.warning("Mongo health failed: %s", exc)
        try:
            from rag.vector_store import get_qdrant_client
            get_qdrant_client().get_collections(); checks["qdrant"]="ok"
        except Exception as exc:
            checks["qdrant"]="error"; logger.warning("Qdrant health failed: %s", exc)
        ok=all(v=="ok" for v in checks.values())
        return Response({"status":"ok" if ok else "degraded","checks":checks},status=200 if ok else 503)

class SearchView(APIView):
    authentication_classes=[]; permission_classes=[]
    def post(self, request):
        query=request.data.get("query","")
        top_k=request.data.get("top_k",5)
        filters=request.data.get("filters",{}) or {}
        if not isinstance(query,str) or not query.strip():
            return Response({"error":"query is required"},status=400)
        try:
            return Response({"results":search_events(query,int(top_k),filters)})
        except Exception as exc:
            logger.exception("Search failed")
            return Response({"error":"Search failed.","detail":str(exc)},status=503)

class ChatView(APIView):
    authentication_classes=[]; permission_classes=[]
    def post(self, request):
        question=request.data.get("question","")
        try:
            if not isinstance(question,str) or not question.strip(): return Response({"error":"question is required"},status=400)
            return Response(answer_question(question,int(request.data.get("top_k",5))))
        except Exception as exc:
            logger.exception("Chat failed")
            return Response({"error":"Chat failed","detail":str(exc)},status=502)

class StatsView(APIView):
    authentication_classes=[]; permission_classes=[]
    def get(self, request):
        try: return Response(get_stats())
        except Exception as exc:
            logger.exception("Stats failed")
            return Response({"error":"Could not read event statistics. Run ingestion first.","detail":str(exc)},status=503)

class EventsView(APIView):
    authentication_classes=[]; permission_classes=[]
    def get(self, request):
        from rag.retrieval import exact_events
        params={k:request.query_params.get(k) for k in ("match_id","player","team","event_type","status")}
        try: return Response({"events":exact_events(params)})
        except Exception as exc:
            logger.exception("Event query failed")
            return Response({"error":"Could not query events","detail":str(exc)},status=503)
