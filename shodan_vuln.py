import os
import sys
import json

import requests

SHODAN_API = "https://api.shodan.io/shodan/host/search"


def fetch_hosts(key, ashn):
    """Return all hosts exposed under the ASN, paginating through 100/page."""
    hosts = []
    page = 1
    while True:
        resp = requests.get(SHODAN_API, params={
            "key": key,
            "query": f"asn:{ashn}",
            "page": page,
        }, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        # Shodan reports errors (rate limit, quota, invalid query) in a 'message'
        # field with a 200 — surface them instead of crashing on a missing key.
        if "results" not in data:
            print(f"  ERROR from Shodan: {data.get('message', data)}")
            break

        hosts.extend(data.get("results", []))
        print(f"  page {page}: +{len(data['results'])} hosts (running total: {len(hosts)})")

        if len(data.get("results", [])) < 100:
            break
        page += 1
        if page > 1000:  # safety valve
            print("  hit page safety limit, stopping")
            break

        time.sleep(65)   # free tier allows 1 query/minute — be polite
    return hosts

from datetime import datetime, timezone


def write_report(hosts, ashn, output_file="shodan_{ashn}.txt"):
    """Write a human-readable summary plus an embedded JSON block for machines.

    The file has two parts:
      1. A summary + per-host listing that a person can read without parsing JSON.
      2. The full raw payload inside ===JSON_START=== / ===JSON_END=== markers so
         a script can extract the machine-readable portion cleanly.
    """
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # ---- summary statistics ----
    unique_ports = {p for h in hosts for p in h.get("ports", [])}
    countries = {h.get("country_name", "unknown") for h in hosts}
    orgs = {h.get("org", "unknown") for h in hosts if h.get("org")}
    unique_asns = {h.get("asn") for h in hosts if h.get("asn")}

    lines = []
    lines.append("=== ATTACK SURFACE SCAN REPORT (Shodan) ===")
    lines.append(f"Generated: {generated_at}")
    lines.append(f"ASN:       {ashn}")
    lines.append(f"Hosts exposed: {len(hosts)}")
    lines.append(f"Distinct ports: {len(unique_ports)}")
    lines.append(f"Distinct countries: {len(countries)} -> {sorted(countries)}")
    lines.append(f"Organizations: {len(orgs)} -> {sorted(orgs)}")
    lines.append(f"Distinct ASN(s): {sorted(unique_asns)}")
    lines.append("")

    # ---- human-readable per-host listing ----
    lines.append("=== HOSTS ===")
    for i, h in enumerate(hosts, 1):
        ip = h.get("ip_str", "unknown")
        lines.append(f"[{i}] {ip}")
        lines.append(f"    Country:   {h.get('country_name', 'unknown')}")
        if h.get("org"):
            lines.append(f"    Org:       {h['org']}")
        if h.get("domain"):
            lines.append(f"    Domain:    {h['domain']}")
        lines.append(f"    ASN:       {h.get('asn', 'unknown')}")
        ports = h.get("ports", [])
        lines.append(f"    Ports:     {', '.join(str(p) for p in ports) if ports else '(none)'}")
        for port in ports:
            detail = []
            if port.get("product"):
                detail.append(port["product"])
            if port.get("version"):
                detail.append(port["version"])
            service = port.get("service") or port.get("proto", "")
            lines.append(f"        - {port.get('ports', '?')} ({service}): {'; '.join(detail)}")
        lines.append("")

    # ---- machine-readable JSON block ----
    payload = {
        "generated_at": generated_at,
        "asn": ashn,
        "host_count": len(hosts),
        "hosts": hosts,
    }
    json_block = json.dumps(payload, indent=2, default=str)
    lines.append("=== RAW DATA ===")
    lines.append("===JSON_START===")
    lines.append(json_block)
    lines.append("===JSON_END===")

    final_path = output_file.format(ashn=ashn)
    with open(final_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Done: {len(hosts)} hosts -> {final_path}")
    return final_path


def main():
    ashn = sys.argv[1]
    key_file = sys.argv[2]

    with open(key_file, encoding="utf-8") as f:
        key = f.read().strip()

    print(f"Searching ASN {ashn}...")
    hosts = fetch_hosts(key, ashn)

    write_report(hosts, ashn)



if __name__ == "__main__":
    main()