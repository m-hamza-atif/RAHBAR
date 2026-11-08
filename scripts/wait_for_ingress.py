"""Wait for the Ingress controller to route /readyz to the API service and return JSON."""
import argparse
import sys
import time

import httpx


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:18080', help='Ingress base URL')
    parser.add_argument('--host', default='rahbar.local', help='Host header for routing')
    parser.add_argument('--timeout', type=int, default=120, help='Maximum seconds to wait')
    args = parser.parse_args()

    deadline = time.time() + args.timeout
    client = httpx.Client(base_url=args.url, headers={'Host': args.host}, timeout=10)
    print(f"Waiting for Ingress at {args.url} (Host: {args.host}) to serve API readiness JSON...")

    last_status = "no attempts made yet"
    attempt = 0
    while time.time() < deadline:
        attempt += 1
        try:
            r = client.get('/readyz')
            ct = r.headers.get('content-type', '')
            if r.status_code == 200 and 'application/json' in ct:
                data = r.json()
                if data.get('status') == 'ready':
                    rev = data.get('index_revision')
                    print(f"  Attempt {attempt}: Ingress /readyz is READY (revision={rev})")
                    # Also confirm /api/ask accepts POST through Ingress
                    ask_r = client.post('/api/ask', json={'question': 'When is a student placed on academic warning?'})
                    ask_ct = ask_r.headers.get('content-type', '')
                    if ask_r.status_code == 200 and 'application/json' in ask_ct:
                        print(f"  Attempt {attempt}: Ingress /api/ask confirmed accepting POST requests.")
                        client.close()
                        return 0
                    last_status = f"/api/ask returned HTTP {ask_r.status_code} ({ask_ct})"
                else:
                    last_status = f"/readyz returned status={data.get('status')}"
            else:
                last_status = f"/readyz returned HTTP {r.status_code} ({ct})"
        except Exception as exc:
            last_status = f"connection error: {exc}"

        print(f"  Attempt {attempt}: {last_status}; waiting 2s...")
        time.sleep(2)

    client.close()
    sys.exit(f"Timed out after {args.timeout}s waiting for API Ingress route: {last_status}")


if __name__ == '__main__':
    sys.exit(main())
