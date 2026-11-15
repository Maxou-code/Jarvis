import json
from datetime import datetime

from config import KNOWLEDGE_DB
from Tools.web import _search_terms

def _knowledge_connection():
    import sqlite3
    db=sqlite3.connect(str(KNOWLEDGE_DB),timeout=10)
    db.execute("CREATE TABLE IF NOT EXISTS knowledge(id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL UNIQUE,content TEXT NOT NULL,tags TEXT DEFAULT '',created_at TEXT NOT NULL,updated_at TEXT NOT NULL)"); db.commit(); return db
def knowledge_save(title,content,tags=""):
    if not title.strip() or not content.strip(): raise ValueError("Titre et contenu obligatoires.")
    if len(title)>200 or len(content)>10000 or len(tags)>500: raise ValueError("Connaissance trop volumineuse.")
    now=datetime.now().astimezone().isoformat(timespec="seconds")
    with _knowledge_connection() as db: db.execute("INSERT INTO knowledge(title,content,tags,created_at,updated_at) VALUES(?,?,?,?,?) ON CONFLICT(title) DO UPDATE SET content=excluded.content,tags=excluded.tags,updated_at=excluded.updated_at",(title.strip(),content.strip(),tags.strip(),now,now))
    return f"Connaissance enregistrée : {title.strip()}"
def knowledge_search(query,limit=8):
    if not query.strip(): raise ValueError("Indique les termes à rechercher.")
    if not 1<=int(limit)<=20: raise ValueError("limit doit être compris entre 1 et 20.")
    terms=_search_terms(query)
    with _knowledge_connection() as db: rows=db.execute("SELECT title,content,tags,updated_at FROM knowledge ORDER BY updated_at DESC").fetchall()
    found=[]
    for title,content,tags,updated in rows:
        score=len(terms&_search_terms(title+" "+tags+" "+content))
        if score: found.append((score,{"title":title,"content":content,"tags":tags,"updated_at":updated}))
    found.sort(key=lambda x:(x[0],x[1]["updated_at"]),reverse=True)
    return json.dumps({"query":query,"results":[x[1] for x in found[:int(limit)]]},ensure_ascii=False,indent=2)
def knowledge_list(limit=20):
    if not 1<=int(limit)<=100: raise ValueError("limit doit être compris entre 1 et 100.")
    with _knowledge_connection() as db: rows=db.execute("SELECT title,tags,updated_at FROM knowledge ORDER BY updated_at DESC LIMIT ?",(int(limit),)).fetchall()
    return json.dumps([{"title":a,"tags":b,"updated_at":c} for a,b,c in rows],ensure_ascii=False,indent=2)
