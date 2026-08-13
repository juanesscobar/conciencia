"""Test E2E rápido de LeadHunterJob (PR-0.2)."""
import json
import sys
import time
import urllib.request

BASE = "http://localhost:8000"
PASSWORD = "MC-Admin#2026!"


def req(method, path, token=None, body=None, timeout=30):
    url = BASE + path
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        print(f"  HTTP {e.code} {path}: {raw[:300]}")
        return e.code, None


def main():
    st, login = req("POST", "/api/v1/auth/login", body={"username": "admin", "password": PASSWORD})
    if st != 200 or not login:
        print("FALLO login")
        sys.exit(1)
    token = login["access_token"]
    print("1. LOGIN OK")

    body = {"name": "Test E2E jobs", "criteria": {"source": "overpass", "limit": 3}}
    st, job = req("POST", "/api/v1/leads/jobs", token=token, body=body)
    if st != 201 or not job:
        print("FALLO crear job")
        sys.exit(1)
    print(f"2. JOB CREADO id={job['id']} status={job['status']}")

    # poll hasta completar
    for i in range(10):
        time.sleep(4)
        st, job2 = req("GET", f"/api/v1/leads/jobs/{job['id']}", token=token)
        print(f"   poll {i}: status={job2['status']} progress={job2['progress']} results={job2['results_count']} dupes={job2['duplicates_count']}")
        if job2["status"] in ("completed", "failed", "cancelled"):
            break

    if job2["status"] != "completed":
        print("FALLO: job no completó", job2.get("error"))
        sys.exit(1)

    st, leads = req("GET", f"/api/v1/leads/jobs/{job['id']}/leads?page_size=5", token=token)
    print(f"3. LEADS DEL JOB: {leads['total']}")
    for l in leads["items"][:3]:
        print(f"   - {l['company']} | {l['region']} | score={l['score']}")

    # retry test: crear job con fuente inválida debería fallar limpio
    st, bad = req("POST", "/api/v1/leads/jobs", token=token, body={"name": "bad", "criteria": {"source": "nonexistent"}})
    print(f"4. JOB FUENTE INVÁLIDA: status={bad['status'] if bad else '?'} (esperado fail eventual)")

    print("\nE2E JOB TEST: OK")


if __name__ == "__main__":
    main()
