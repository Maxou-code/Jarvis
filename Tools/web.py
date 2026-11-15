import json
import os
import re

import requests

def _check_internet_connection():
    """Teste plusieurs destinations HTTPS ; une seule réponse suffit à confirmer Internet."""
    endpoints = (
        "https://www.google.com/generate_204",
        "https://duckduckgo.com/",
        "https://www.cloudflare.com/",
    )
    for url in endpoints:
        try:
            response = requests.get(
                url, timeout=(3, 4), allow_redirects=True,
                headers={"User-Agent": "JARVIS-3.5/1.0"}
            )
            if response.status_code < 500:
                return True
        except requests.RequestException:
            continue
    return False
def _search_terms(text):
    stop = {"avec","pour","dans","sans","sur","les","des","une","un","est","que","qui","the","and","for","with","from","this","that","are","was","how","what"}
    return {t for t in re.findall(r"[a-zA-ZÀ-ÿ0-9]{3,}", (text or "").casefold()) if t not in stop}
def _rank_search_result(query, item):
    terms = _search_terms(query)
    if not terms: return 0.0
    title, body = _search_terms(item.get("titre", "")), _search_terms(item.get("extrait", ""))
    return round(0.7 * len(terms & title) / len(terms) + 0.3 * len(terms & body) / len(terms), 4)
def web_search(query, max_results=5):
    """Recherche DuckDuckGo, complétée par Bing/Google si les clés API existent."""
    if not isinstance(query, str) or not query.strip() or len(query) > 500: raise ValueError("Indique une recherche non vide de 500 caractères maximum.")
    if isinstance(max_results, bool) or not isinstance(max_results, int) or not 1 <= max_results <= 10: raise ValueError("max_results doit être compris entre 1 et 10.")
    if not _check_internet_connection(): raise ConnectionError("Recherche impossible : ce PC ne semble pas connecté à Internet.")
    query = query.strip(); gathered = []; errors = []
    try:
        from ddgs import DDGS
        for item in (DDGS().text(query, max_results=max_results * 2, safesearch="moderate") or []):
            gathered.append({"titre":item.get("title",""),"url":item.get("href",""),"extrait":item.get("body",""),"moteur":"DuckDuckGo"})
    except Exception as exc: errors.append(f"DuckDuckGo : {type(exc).__name__}: {exc}")
    bing_key = os.environ.get("BING_SEARCH_API_KEY")
    if bing_key:
        try:
            r=requests.get("https://api.bing.microsoft.com/v7.0/search",headers={"Ocp-Apim-Subscription-Key":bing_key},params={"q":query,"count":max_results*2,"mkt":"fr-FR","safeSearch":"Moderate"},timeout=(5,12)); r.raise_for_status()
            for x in r.json().get("webPages",{}).get("value",[]): gathered.append({"titre":x.get("name",""),"url":x.get("url",""),"extrait":x.get("snippet",""),"moteur":"Bing"})
        except Exception as exc: errors.append(f"Bing : {type(exc).__name__}: {exc}")
    google_key=os.environ.get("GOOGLE_SEARCH_API_KEY"); google_cx=os.environ.get("GOOGLE_SEARCH_ENGINE_ID")
    if google_key and google_cx:
        try:
            r=requests.get("https://www.googleapis.com/customsearch/v1",params={"key":google_key,"cx":google_cx,"q":query,"num":min(10,max_results*2),"safe":"active"},timeout=(5,12)); r.raise_for_status()
            for x in r.json().get("items",[]): gathered.append({"titre":x.get("title",""),"url":x.get("link",""),"extrait":x.get("snippet",""),"moteur":"Google"})
        except Exception as exc: errors.append(f"Google : {type(exc).__name__}: {exc}")
    unique={}
    for item in gathered:
        url=(item.get("url") or "").strip()
        if not url: continue
        item["pertinence"]=_rank_search_result(query,item); key=url.rstrip("/").casefold()
        if key not in unique or item["pertinence"]>unique[key]["pertinence"]: unique[key]=item
    results=sorted(unique.values(),key=lambda x:(x["pertinence"],bool(x["titre"])),reverse=True)[:max_results]
    return json.dumps({"query":query,"nombre_resultats":len(results),"moteurs_utilises":sorted({x["moteur"] for x in results}),"resultats":results,"avertissements":errors,"configuration_api":{"bing":bool(bing_key),"google":bool(google_key and google_cx)}},ensure_ascii=False,indent=2)
