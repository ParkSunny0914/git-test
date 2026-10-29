"""Monitor official MW4 notes and X posts; never claim that rumor is confirmed."""
import os, json, hashlib, re, pathlib, datetime
import requests
from bs4 import BeautifulSoup

ROOT=pathlib.Path(__file__).parent
C=json.loads((ROOT/"config.json").read_text())
STATE=ROOT/"state/seen.json"
S=requests.Session(); S.headers.update({"User-Agent":"MW4-Discord-Alert/1.0"})
TIMEOUT=20

def clean(s): return re.sub(r"\\s+"," ",s or "").strip()
def relevant(s): return any(w in s.casefold() for w in [x.casefold() for x in C["keywords"]])
def entry(source,kind,title,body,url,date=""):
    body=clean(body)
    key=hashlib.sha256((source+"|"+url+"|"+body).encode()).hexdigest()[:24]
    return {"id":key,"source":source,"kind":kind,"title":clean(title)[:220],"body":body[:1400],"url":url,"date":date}

def official(url):
    r=S.get(url,timeout=TIMEOUT); r.raise_for_status()
    soup=BeautifulSoup(r.text,"html.parser")
    for t in soup(["script","style","nav","footer","aside"]): t.decompose()
    root=soup.find("main") or soup.find("article") or soup
    parts=[clean(t.get_text(" ",strip=True)) for t in root.find_all(["h1","h2","h3","p","li"])]
    text="\n".join(dict.fromkeys(p for p in parts if len(p)>35))[:50000]
    if not text or not relevant(text): return []
    x=entry("Call of Duty","official","공식 패치노트 변경",text[:1350],url)
    x["id"]=hashlib.sha256((url+"|"+text).encode()).hexdigest()[:24]
    return [x]

def xposts(users,kind,token):
    if not token: return []
    q="("+" OR ".join("from:"+u for u in users)+") -is:retweet -is:reply"
    r=S.get("https://api.x.com/2/tweets/search/recent",params={"query":q,"max_results":100,"tweet.fields":"created_at,author_id","expansions":"author_id","user.fields":"username"},headers={"Authorization":"Bearer "+token},timeout=TIMEOUT)
    r.raise_for_status()
    j=r.json(); names={u["id"]:u["username"] for u in j.get("includes",{}).get("users",[])}
    out=[]
    for t in j.get("data",[]):
        author=names.get(t.get("author_id"),"unknown"); body=clean(t.get("text",""))
        if relevant(body): out.append(entry(author,kind,body[:120],body,"https://x.com/"+author+"/status/"+t["id"],t.get("created_at","")))
    return out

def tokens(t): return set(w for w in re.findall(r"[a-z0-9][a-z0-9-]{3,}",t.casefold()) if w not in {"modern","warfare","call","duty","update","leak","rumor","official","season","with","from"})
def corroborated(x,others):
    a=tokens(x["body"])
    for y in others:
        if x["source"].lower()==y["source"].lower(): continue
        b=tokens(y["body"])
        if len(a&b)>=4 and len(a&b)/max(1,min(len(a),len(b)))>=0.5: return True
    return False

def discord(url,x):
    label="공식" if x["kind"]=="official" else "유출·미확정"
    text=x["body"][:1000].replace("@everyone","@ everyone").replace("@here","@ here")
    if label!="공식": text="⚠️ 서로 다른 정보 계정의 내용이 비슷하다는 뜻이며, 독립된 원본 증거로 검증된 사실은 아닙니다.\n"+text
    payload={"username":"MW4 뉴스 알림","allowed_mentions":{"parse":[]},"embeds":[{"title":"["+label+"] "+x["title"][:200],"description":text,"url":x["url"],"color":3066993 if label=="공식" else 15844367,"fields":[{"name":"출처 · 게시일","value":(x["source"]+" · "+(x["date"] or "미표기"))[:1024]},{"name":"한눈에 보는 요약","value":x["title"][:1024]}]}]}
    r=S.post(url,json=payload,timeout=TIMEOUT);r.raise_for_status()

def main():
    seen=json.loads(STATE.read_text()); gathered=[]; sources_ok=0
    for url in C["official_urls"]:
        try: gathered+=official(url); sources_ok+=1
        except Exception as e: print("WARN official",type(e).__name__,str(e)[:120])
    token=os.getenv("X_BEARER_TOKEN","")
    news=[]; verified=[]
    if token:
        try: verified=xposts(C["official_x_accounts"],"official",token); sources_ok+=1
        except Exception as e: print("WARN official X",type(e).__name__,str(e)[:120])
        try: news=xposts(C["news_x_accounts"],"unofficial",token); sources_ok+=1
        except Exception as e: print("WARN news X",type(e).__name__,str(e)[:120])
    gathered+=verified
    # Unofficial claims require corroboration by a second named account.
    # This establishes repeated reporting, NOT verified authenticity.
    gathered += [x for x in news if corroborated(x,news)]
    if not gathered:
        print("No usable material; keeping state unchanged");return
    old=set(seen.get("seen",[]))
    if not seen.get("initialized"):
        STATE.write_text(json.dumps({"initialized":True,"seen":sorted(old|{x["id"] for x in gathered})},indent=2)+"\n")
        print("Initial baseline saved; no old news sent"); return
    fresh=[x for x in gathered if x["id"] not in old]
    if not fresh: print("No new content");return
    webhook=os.getenv("DISCORD_WEBHOOK_URL","")
    if not webhook: raise RuntimeError("Add DISCORD_WEBHOOK_URL as an Actions repository secret")
    # Persist only delivered notifications to avoid suppressing a failed retry.
    for x in fresh[:8]:
        discord(webhook,x)
        old.add(x["id"])
        STATE.write_text(json.dumps({"initialized":True,"seen":sorted(old)[-2500:]},indent=2)+"\n")
    print("Notifications sent:",min(len(fresh),8))
if __name__=="__main__": main()
