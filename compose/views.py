
from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction, models
from django.db.models import Max
from .models import Session, Draft, Move, RubricSnapshot
from .forms import SessionForm, DraftForm
try:
    from haiku_shared import analyze_draft
except Exception:
    analyze_draft = None

# ===== 日本語表示用の共通定義（グローバル定数） =====
LABELS = {
    "seasonality": "季節感",
    "imagery": "像",
    "rhythm": "律動",
    "originality": "独創",
    "clarity": "透明度",
}
HELPS = {
    "seasonality": "季語・季の手掛かりの明確さ（季の風合いが伝わるか）",
    "imagery":     "視覚・聴覚など具体的な像が立つか（描写の密度）",
    "rhythm":      "音数・切れ・語の調子が整っているか",
    "originality": "ありきたりでない視点や言い回し",
    "clarity":     "余計な説明がなく読みやすいか（透明感）",
}
ORDER_KEYS = ["seasonality", "imagery", "rhythm", "originality", "clarity"]

# ---- お題→季語の簡易抽出 ----
def extract_season_hint(odai: str):
    if not odai:
        return None
    seasons = {
        "春": ["春","花見","桜","若葉","霞"],
        "夏": ["夏","蝉","夕立","向日葵","涼"],
        "秋": ["秋","月","雁","紅葉","秋風","彼岸"],
        "冬": ["冬","雪","霜","氷","寒","冴ゆ"],
        "新年": ["新年","初日の出","初売り","初詣"],
    }
    for _, words in seasons.items():
        for w in words:
            if w in odai:
                return w
    return None

def home(request):
    sessions = Session.objects.order_by("-id")[:50]
    return render(request, "compose/home.html", {"sessions": sessions})

def session_new(request):
    # お題（odai）1項目版を想定。既存フォーム互換のため theme/season_hint も拾う。
    if request.method == "POST":
        form = SessionForm(request.POST)
        if form.is_valid():
            odai = form.cleaned_data.get("odai") or form.cleaned_data.get("theme") or ""
            hint = extract_season_hint(odai) or form.cleaned_data.get("season_hint") or ""
            s = Session.objects.create(theme=odai, season_hint=hint)
            return redirect("compose:session_detail", session_id=s.id)
    else:
        form = SessionForm()
    return render(request, "compose/session_new.html", {"form":form})

def session_detail(request, session_id:int):
    s = get_object_or_404(Session, id=session_id)
    drafts = s.drafts.order_by("version").all()
    moves = s.moves.order_by("id").all()
    return render(request, "compose/session_detail.html", {"session":s,"drafts":drafts,"moves":moves})

def draft_new(request, session_id:int):
    s = get_object_or_404(Session, id=session_id)
    if request.method == "POST":
        form = DraftForm(request.POST)
        if form.is_valid():
            text = form.cleaned_data["text"].strip()
            ver = (s.drafts.aggregate(vmax=models.Max("version"))["vmax"] or 0) + 1
            with transaction.atomic():
                d = Draft.objects.create(session=s, version=ver, text=text)
                Move.objects.create(session=s, draft=d, kind="note", payload={"text":"初稿作成"})
                if analyze_draft:
                    res = analyze_draft(text, season_hint=s.season_hint or None)
                    trip = res.get("triplet",(0,0,0))
                    RubricSnapshot.objects.create(draft=d, total=res["total"], breakdown=res["breakdown"], triplet=f"{trip[0]}-{trip[1]}-{trip[2]}")
            return redirect("compose:draft_detail", draft_id=d.id)
    else:
        form = DraftForm()
    return render(request, "compose/draft_new.html", {"form":form, "session":s})

def draft_detail(request, draft_id:int):
    d = get_object_or_404(Draft, id=draft_id)
    prev = d.session.drafts.filter(version=d.version-1).first()

    # ---- 観点別の表 ----
    breakdown_list = None
    if getattr(d, "rubric", None):
        bd = d.rubric.breakdown or {}
        breakdown_list = [{
            "key": k,
            "label": LABELS.get(k, k),
            "help": HELPS.get(k, ""),
            "score": (bd.get(k) or {}).get("score"),
            "why": (bd.get(k) or {}).get("why"),
        } for k in ORDER_KEYS if k in bd]

    # ---- Δスコア ----
    delta = None
    if prev and getattr(d, "rubric", None) and getattr(prev, "rubric", None):
        def get_score(bd, k):
            try:
                return (bd.get(k) or {}).get("score") or 0
            except Exception:
                return 0
        parts = {k: get_score(d.rubric.breakdown, k) - get_score(prev.rubric.breakdown, k) for k in ORDER_KEYS}
        delta = {
            "total": round((d.rubric.total or 0) - (prev.rubric.total or 0), 2),
            "parts": [{"label": LABELS.get(k, k), "value": parts[k]} for k in ORDER_KEYS],
        }

    return render(request, "compose/draft_detail.html",
                  {"draft": d, "prev": prev, "breakdown_list": breakdown_list, "delta": delta})

def _next_candidates(d: Draft):
    s = d.session
    base = d.text
    cands = []
    cands.append(base.replace("や","").replace("かな","").replace("けり","").strip())
    if "遠く" not in base and "山" not in base:
        cands.append(f"{base}　遠く山影")
    if s.season_hint and s.season_hint not in base:
        cands.append(f"{base}　{s.season_hint}")
    cands.append(base.replace("/", " / "))
    return [t for t in cands if t and t != base][:5]

def draft_next(request, draft_id:int):
    d = get_object_or_404(Draft, id=draft_id)
    s = d.session
    if request.method == "POST":
        text = request.POST.get("text","").strip()
        ver = (s.drafts.aggregate(vmax=Max("version"))["vmax"] or 0) + 1
        with transaction.atomic():
            nd = Draft.objects.create(session=s, version=ver, text=text)
            Move.objects.create(session=s, draft=nd, kind="note", payload={"from": d.id, "text":"改稿（v+1）"})
            if analyze_draft:
                res = analyze_draft(text, season_hint=s.season_hint or None)
                trip = res.get("triplet",(0,0,0))
                RubricSnapshot.objects.create(draft=nd, total=res["total"], breakdown=res["breakdown"], triplet=f"{trip[0]}-{trip[1]}-{trip[2]}")
        return redirect("compose:draft_detail", draft_id=nd.id)
    cands = _next_candidates(d)
    return render(request, "compose/draft_next.html", {"draft":d, "cands":cands})

def move_add(request, session_id:int):
    s = get_object_or_404(Session, id=session_id)
    if request.method == "POST":
        kind = request.POST.get("kind","note")
        text = request.POST.get("text","").strip()
        Move.objects.create(session=s, kind=kind, payload={"text": text})
    return redirect("compose:session_detail", session_id=s.id)
