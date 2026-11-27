"""Verify candidate references against arXiv and Crossref and emit BibTeX ONLY from verified metadata.

A candidate is accepted when a source returns a record whose normalized title equals the requested title.
Nothing is written from memory: every field in references.bib comes from the API response. Unverified candidates
are listed in the report and excluded from the bibliography.
Usage: verify_references.py CANDIDATES_JSON OUT_BIB OUT_REPORT_JSON
"""
import json, re, sys, time, urllib.parse, urllib.request, xml.etree.ElementTree as ET

UA = {"User-Agent": "sqltoviz-research/0.1 (reference verification)"}
norm = lambda s: re.sub(r"[^a-z0-9]", "", re.sub(r"<[^>]+>", "", s or "").lower())


def get(url, tries=3):
    for k in range(tries):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40).read()
        except Exception:
            time.sleep(3 * (k + 1))
    return None


def arxiv_lookup(title, author=None, **_):
    q = urllib.parse.quote(f'ti:"{title}"')
    raw = get(f"http://export.arxiv.org/api/query?search_query={q}&max_results=5")
    time.sleep(3.2)
    if not raw:
        return None
    ns = {"a": "http://www.w3.org/2005/Atom"}
    for e in ET.fromstring(raw).findall("a:entry", ns):
        t = " ".join((e.findtext("a:title", "", ns) or "").split())
        auths = [a.findtext("a:name", "", ns) for a in e.findall("a:author", ns)]
        if norm(t) == norm(title) and (not author or norm(author) in norm(auths[0])):
            aid = e.findtext("a:id", "", ns).rsplit("/abs/", 1)[1]
            return {"source": "arxiv", "title": t, "authors": [a.findtext("a:name", "", ns) for a in e.findall("a:author", ns)],
                    "year": int(e.findtext("a:published", "", ns)[:4]), "arxiv_id": re.sub(r"v\d+$", "", aid),
                    "abstract": " ".join((e.findtext("a:summary", "", ns) or "").split())}
    return None


def crossref_doi(title, doi, author=None):
    """Direct DOI fetch; accepted only if Crossref's own title (and first author) match the requested ones."""
    raw = get("https://api.crossref.org/works/" + urllib.parse.quote(doi))
    if not raw:
        return None
    it = json.loads(raw)["message"]
    t = (it.get("title") or [""])[0]
    if norm(t) == norm(title) and it.get("author") and (not author or norm(author) in norm(it["author"][0].get("family", ""))):
        return {"source": "crossref", "title": re.sub(r"<[^>]+>", "", t), "doi": it["DOI"], "type": it.get("type"),
                "authors": [f"{a.get('family','')}, {a.get('given','')}".strip(", ") for a in it["author"]],
                "year": (it.get("issued") or it.get("published") or {"date-parts": [[None]]})["date-parts"][0][0],
                "venue": (it.get("container-title") or [""])[0], "volume": it.get("volume"), "issue": it.get("issue"), "pages": it.get("page")}
    return None


def crossref_lookup(title, author=None, avoid_doi_prefix=None):
    raw = get("https://api.crossref.org/works?rows=5&select=DOI,title,author,issued,container-title,type,volume,issue,page,publisher&query.bibliographic=" + urllib.parse.quote(title))
    if not raw:
        return None
    for it in json.loads(raw)["message"]["items"]:
        t = (it.get("title") or [""])[0]
        if avoid_doi_prefix and it["DOI"].startswith(avoid_doi_prefix):
            continue
        if norm(t) == norm(title) and it.get("author") and (not author or norm(author) in norm(it["author"][0].get("family", ""))):
            return {"source": "crossref", "title": re.sub(r"<[^>]+>", "", t), "doi": it["DOI"], "type": it.get("type"),
                    "authors": [f"{a.get('family','')}, {a.get('given','')}".strip(", ") for a in it["author"]],
                    "year": it["issued"]["date-parts"][0][0], "venue": (it.get("container-title") or [""])[0],
                    "volume": it.get("volume"), "issue": it.get("issue"), "pages": it.get("page")}
    return None


_ACC = {"\u0306": "u", "\u0327": "c", "\u0301": "'", "\u0300": "`", "\u0302": "^", "\u0308": '"', "\u0303": "~", "\u030c": "v", "\u0304": "=", "\u030a": "r"}


def latex_accents(text):
    """Non-ASCII letters -> LaTeX accent commands (plain-TeX bibliographies cannot print them reliably)."""
    import unicodedata
    out, chars = [], list(unicodedata.normalize("NFD", text))
    i = 0
    while i < len(chars):
        c = chars[i]
        if i + 1 < len(chars) and chars[i + 1] in _ACC:
            cmd = _ACC[chars[i + 1]]
            out.append("{\\%s{%s}}" % (cmd, c) if cmd.isalpha() else "{\\%s%s}" % (cmd, c))
            i += 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


def bibtex(key, r):
    esc = lambda s: latex_accents(s).replace("&", r"\&").replace("%", r"\%").replace("_", r"\_")
    au = " and ".join(r["authors"])
    if r["source"] == "arxiv":
        return (f"@misc{{{key},\n  title = {{{esc(r['title'])}}},\n  author = {{{esc(au)}}},\n  year = {{{r['year']}}},\n"
                f"  eprint = {{{r['arxiv_id']}}},\n  archivePrefix = {{arXiv}}\n}}\n")
    kind = "inproceedings" if r.get("type") == "proceedings-article" else "article"
    venue = "booktitle" if kind == "inproceedings" else "journal"
    extra = "".join(f"  {k} = {{{esc(str(v))}}},\n" for k, v in (("volume", r.get("volume")), ("number", r.get("issue")), ("pages", r.get("pages"))) if v)
    return (f"@{kind}{{{key},\n  title = {{{esc(r['title'])}}},\n  author = {{{esc(au)}}},\n  year = {{{r['year']}}},\n"
            f"  {venue} = {{{esc(r['venue'])}}},\n{extra}  doi = {{{r['doi']}}}\n}}\n")


if __name__ == "__main__":
    cands = json.load(open(sys.argv[1]))
    bib, report = [], []
    for c in cands:
        order = ("arxiv", "crossref") if c.get("prefer") == "arxiv" else ("crossref", "arxiv")
        rec = crossref_doi(c["title"], c["doi"], c.get("author")) if c.get("doi") else None
        for s in (order if not rec else ()):
            rec = (arxiv_lookup if s == "arxiv" else crossref_lookup)(c["title"], author=c.get("author"), avoid_doi_prefix=c.get("avoid_doi_prefix"))
            if rec:
                break
        if rec:
            bib.append(bibtex(c["key"], rec))
            report.append({"key": c["key"], "verified": True, "source": rec["source"], "id": rec.get("arxiv_id") or rec.get("doi"),
                           "year": rec["year"], "title": rec["title"], "first_author": rec["authors"][0], "abstract": rec.get("abstract")})
        else:
            report.append({"key": c["key"], "verified": False, "requested_title": c["title"]})
    open(sys.argv[2], "w").write("% Generated by tools/verify_references.py from arXiv/Crossref responses only.\n\n" + "\n".join(bib))
    json.dump({"retrieved": time.strftime("%Y-%m-%d"), "entries": report}, open(sys.argv[3], "w"), indent=1)
    print(json.dumps([{k: r[k] for k in ("key", "verified", "source", "id", "year") if k in r} for r in report], indent=0))
