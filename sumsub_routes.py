import os, time, json, hmac, hashlib, secrets
import httpx
from fastapi import Header, HTTPException, Request
from pydantic import BaseModel, Field

SUMSUB_APP_TOKEN = os.environ.get("SUMSUB_APP_TOKEN", "")
SUMSUB_SECRET_KEY = os.environ.get("SUMSUB_SECRET_KEY", "")
SUMSUB_LEVEL_NAME = os.environ.get("SUMSUB_LEVEL_NAME", "masters-kyc")
SUMSUB_WEBHOOK_SECRET = os.environ.get("SUMSUB_WEBHOOK_SECRET", "")
SUMSUB_BASE = "https://api.sumsub.com"

def _sumsub_sign(ts: str, method: str, path_qs: str, body: bytes) -> str:
    msg = (ts + method.upper() + path_qs).encode("utf-8") + body
    return hmac.new(SUMSUB_SECRET_KEY.encode("utf-8"), msg, hashlib.sha256).hexdigest()

async def _sumsub_request(method: str, path: str, json_body: dict | None = None, params: dict | None = None):
    ts = str(int(time.time()))
    body = b"" if json_body is None else json.dumps(json_body, separators=(",", ":")).encode("utf-8")

    if params:
        from urllib.parse import urlencode
        path_qs = path + "?" + urlencode(params)
    else:
        path_qs = path

    sig = _sumsub_sign(ts, method, path_qs, body)
    headers = {
        "X-App-Token": SUMSUB_APP_TOKEN,
        "X-App-Access-Ts": ts,
        "X-App-Access-Sig": sig,
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(base_url=SUMSUB_BASE, timeout=30) as client:
        r = await client.request(method, path, params=params, content=body, headers=headers)
        if r.status_code >= 400:
            raise HTTPException(status_code=502, detail={"sumsub": r.text})
        return r.json()

class MasterSignup(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    service: str = Field(pattern="^(plumber|electrician|furniture|handyman)$")
    phone: str = Field(min_length=6, max_length=30)
    email: str | None = None
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)

class KycTokenReq(BaseModel):
    masterId: int
    authToken: str

def register_sumsub(app, connect):
    # простая миграция для SQLite
    conn = connect()
    cur = conn.cursor()
    try: cur.execute("ALTER TABLE masters ADD COLUMN email TEXT;")
    except: pass
    try: cur.execute("ALTER TABLE masters ADD COLUMN auth_token TEXT;")
    except: pass
    conn.commit()
    conn.close()

    @app.post("/api/masters/signup")
    def masters_signup(m: MasterSignup):
        auth_token = secrets.token_urlsafe(24)
        conn = connect()
        cur = conn.cursor()
        cur.execute("""
          INSERT INTO masters (name, service, phone, rating, jobs, price_from, tagline, lat, lng, is_verified, email, auth_token)
          VALUES (?, ?, ?, 4.5, 0, 0, "", ?, ?, 0, ?, ?)
        """, (m.name, m.service, m.phone, float(m.lat), float(m.lng), m.email, auth_token))
        master_id = cur.lastrowid
        conn.commit()
        conn.close()
        return {"ok": True, "masterId": master_id, "authToken": auth_token}

    @app.post("/api/kyc/sumsub-token")
    async def get_sumsub_token(req: KycTokenReq):
        conn = connect()
        cur = conn.cursor()
        cur.execute("SELECT id, email, phone, auth_token FROM masters WHERE id = ?", (req.masterId,))
        row = cur.fetchone()
        conn.close()
        if not row or row["auth_token"] != req.authToken:
            raise HTTPException(status_code=401, detail="Invalid auth token")

        user_id = f"master:{req.masterId}"
        payload = {
            "ttlInSecs": 600,
            "userId": user_id,
            "levelName": SUMSUB_LEVEL_NAME,
            "applicantIdentifiers": {}
        }
        if row["email"]:
            payload["applicantIdentifiers"]["email"] = row["email"]
        if row["phone"]:
            payload["applicantIdentifiers"]["phone"] = row["phone"]

        return await _sumsub_request("POST", "/resources/accessTokens/sdk", json_body=payload)

    def _verify_webhook(raw: bytes, digest_hex: str, alg: str):
        a = (alg or "HMAC_SHA256").lower()
        h = hashlib.sha512 if "sha512" in a else hashlib.sha256
        calc = hmac.new(SUMSUB_WEBHOOK_SECRET.encode("utf-8"), raw, h).hexdigest()
        return hmac.compare_digest(calc, digest_hex)

    @app.post("/api/sumsub/webhook")
    async def sumsub_webhook(
        request: Request,
        x_payload_digest: str | None = Header(default=None, alias="x-payload-digest"),
        x_payload_digest_alg: str | None = Header(default="HMAC_SHA256", alias="x-payload-digest-alg"),
    ):
        raw = await request.body()
        if not x_payload_digest or not SUMSUB_WEBHOOK_SECRET:
            raise HTTPException(status_code=400, detail="Webhook signature missing/config error")
        if not _verify_webhook(raw, x_payload_digest, x_payload_digest_alg or "HMAC_SHA256"):
            raise HTTPException(status_code=401, detail="Bad webhook signature")

        event = json.loads(raw.decode("utf-8"))
        if event.get("type") == "applicantReviewed":
            review = event.get("reviewResult") or {}
            if review.get("reviewAnswer") == "GREEN":
                user_id = event.get("externalUserId") or event.get("userId")
                if user_id and str(user_id).startswith("master:"):
                    master_id = int(str(user_id).split(":", 1)[1])
                    conn = connect()
                    cur = conn.cursor()
                    cur.execute("UPDATE masters SET is_verified = 1 WHERE id = ?", (master_id,))
                    conn.commit()
                    conn.close()

        return {"ok": True}
