import re
import pandas as pd
from publicsuffix2 import PublicSuffixList

INPUT_FILE = "domains.csv"
OUTPUT_FILE = "analysis_by_tld.csv"

psl = PublicSuffixList()
DOMAIN_RE = re.compile(r'^\s*"([A-Za-z0-9.\-]+)"\s*:\s*\{')

COUNTRY = {
    "ir": "Iran", "kr": "South Korea", "us": "United States",
    "gb": "United Kingdom", "uk": "United Kingdom", "ca": "Canada",
    "au": "Australia", "nl": "Netherlands", "ru": "Russia",
    "cn": "China", "tr": "Turkey", "sa": "Saudi Arabia",
    "ae": "UAE", "il": "Israel", "sg": "Singapore", "tw": "Taiwan",
    "de": "Germany", "fr": "France", "br": "Brazil", "mx": "Mexico",
    "tv": "Tuvalu", "io": "British Indian Ocean Terr.", "ai": "Anguilla",
    "me": "Montenegro", "to": "Tonga", "gg": "Guernsey", "eu": "European Union",
}

# ccTLDs frequently repurposed as "generic" despite technically being country codes
GENERIC_CC = {"io", "tv", "ai", "me", "to", "gg", "co"}


def classify(tld):
    """Return (category, country)."""
    if tld is None:
        return "unknown", "N/A"
    if tld in GENERIC_CC:
        return "gTLD", "generic"
    if re.match(r"^[a-z]{2}$", tld):
        return "ccTLD", COUNTRY.get(tld, "unknown")
    return "gTLD", "generic"


domains = []
with open(INPUT_FILE, encoding="utf-8") as f:
    for line in f:
        m = DOMAIN_RE.match(line)
        if m:
            domains.append(m.group(1))

df = pd.DataFrame({
    "domain": domains,
    "tld": [psl.public_suffix(d) for d in domains],
})

by_tld = (df["tld"].value_counts().reset_index()
          .rename(columns={"index": "tld", "0": "domain_count"})
          .sort_values("domain_count", ascending=False))

tld_cat, country = [], []
for tld in by_tld["tld"]:
    cat, c = classify(tld)
    tld_cat.append(cat)
    country.append(c)

by_tld["category"] = tld_cat
by_tld["country"] = country
by_tld = by_tld[["tld", "category", "country", "domain_count"]]

by_tld.to_csv(OUTPUT_FILE, index=False)
print("Total domains extracted:", len(domains))
print(by_tld.to_string(index=False))
