import os, csv, io, time
import requests
from flask import Flask, jsonify, render_template

app = Flask(__name__)

# =========================================================
#  시트 설정 — Railway 환경변수로 덮어쓸 수 있음.
#  (환경변수 없으면 아래 기본값 사용)
#  ※ 어느 쪽이 K-Stock이고 어느 쪽이 CG인지 한 번 확인하세요.
#    바뀌어 있으면 두 SHEET_ID/GID만 서로 바꿔주면 됩니다.
# =========================================================
KSTOCK_SHEET_ID = os.environ.get("KSTOCK_SHEET_ID", "1vCncbTh3FA4fxuOlrwq9nmSB_bVvS7-7gBxs07xV1XM")
KSTOCK_GID      = os.environ.get("KSTOCK_GID", "0")
CGDB_SHEET_ID   = os.environ.get("CGDB_SHEET_ID", "1XbuQwCEg43OR1yAlp2YTGIo0PVx1FFzFewXftMkGd_4")
CGDB_GID        = os.environ.get("CGDB_GID", "1179664728")
SOURCE_LABEL    = os.environ.get("SOURCE_LABEL", "자료: 머니플러스 자체 집계")

CACHE_TTL = 60  # 초. 시트 수정 후 최대 1분이면 반영됨.
_cache = {}

DEMO_KSTOCK = [
    {"종목명":"한화에어로스페이스","테마":"방산","특징":"방산 대장주, 지상장비·엔진","종목코드":"012450"},
    {"종목명":"LIG넥스원","테마":"방산","특징":"유도무기 중심 방산주","종목코드":"079550"},
    {"종목명":"현대로템","테마":"방산","특징":"K2전차·철도","종목코드":"064350"},
    {"종목명":"한국항공우주","테마":"방산","특징":"항공기·KF-21","종목코드":"047810"},
    {"종목명":"두산에너빌리티","테마":"원전","특징":"원전 주기기 대장","종목코드":"034020"},
    {"종목명":"한전기술","테마":"원전","특징":"원전 설계 전문","종목코드":"052690"},
    {"종목명":"비에이치아이","테마":"원전","특징":"원전 보조기기","종목코드":"083650"},
    {"종목명":"에코프로비엠","테마":"2차전지","특징":"양극재 대표주","종목코드":"247540"},
    {"종목명":"포스코퓨처엠","테마":"2차전지","특징":"양극재·음극재","종목코드":"003670"},
    {"종목명":"한미반도체","테마":"AI반도체","특징":"HBM 본더 TC본더","종목코드":"042700"},
    {"종목명":"이수페타시스","테마":"AI반도체","특징":"고다층 MLB 기판","종목코드":"007660"},
    {"종목명":"리노공업","테마":"AI반도체","특징":"테스트 핀·소켓","종목코드":"058470"},
]
DEMO_CGDB = [
    {"날짜":"02/14","CG제목":"방산 수출 사상 최대","키워드":"방산·실적","유형":"실적"},
    {"날짜":"02/14","CG제목":"원전 일감 본격화","키워드":"원전·정책","유형":"정책"},
    {"날짜":"02/13","CG제목":"HBM 수요 폭발","키워드":"AI반도체·전망","유형":"전망"},
    {"날짜":"02/13","CG제목":"2차전지 바닥 신호?","키워드":"2차전지·등락","유형":"등락"},
]


def gviz_url(sid, gid):
    return f"https://docs.google.com/spreadsheets/d/{sid}/gviz/tq?tqx=out:csv&gid={gid}"


def fetch_sheet(sid, gid):
    """구글시트를 CSV로 서버에서 직접 읽어 list[dict] 반환. 실패 시 None."""
    key = f"{sid}:{gid}"
    now = time.time()
    if key in _cache and now - _cache[key][0] < CACHE_TTL:
        return _cache[key][1]
    try:
        r = requests.get(gviz_url(sid, gid), timeout=10)
        r.raise_for_status()
        text = r.content.decode("utf-8-sig", errors="replace")
        # 시트가 비공개면 구글 로그인 HTML이 돌아옴 → 방어
        head_peek = text[:300].lower()
        if "<html" in head_peek or "<!doctype" in head_peek:
            raise ValueError("sheet is not public (login page returned)")
        reader = csv.reader(io.StringIO(text))
        rows = [row for row in reader if any(c.strip() for c in row)]
        if not rows:
            _cache[key] = (now, [])
            return []
        header = [h.strip() for h in rows[0]]
        objs = []
        for raw in rows[1:]:
            obj = {header[i]: (raw[i].strip() if i < len(raw) else "")
                   for i in range(len(header))}
            objs.append(obj)
        _cache[key] = (now, objs)
        return objs
    except Exception as e:
        print("[fetch_sheet] error:", e)
        return None


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/kstock")
def api_kstock():
    data = fetch_sheet(KSTOCK_SHEET_ID, KSTOCK_GID)
    if data is None:
        return jsonify(rows=DEMO_KSTOCK, source="demo", label=SOURCE_LABEL)
    return jsonify(rows=data, source="live", label=SOURCE_LABEL)


@app.route("/api/cgdb")
def api_cgdb():
    data = fetch_sheet(CGDB_SHEET_ID, CGDB_GID)
    if data is None:
        return jsonify(rows=DEMO_CGDB, source="demo", label=SOURCE_LABEL)
    return jsonify(rows=data, source="live", label=SOURCE_LABEL)


@app.route("/healthz")
def healthz():
    return "ok"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
