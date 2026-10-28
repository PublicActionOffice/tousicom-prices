"""朝(前場終値)・夕方(大引け)の株価を取得して history.csv に追記する。
使い方: python fetch_prices.py morning|evening
出典: Yahoo Finance chart API (非公式)。教育目的・非商用。取得時点の価格であり公式終値ではない。
"""
import sys,csv,json,time,random,urllib.request,datetime,os
from concurrent.futures import ThreadPoolExecutor
HERE=os.path.dirname(os.path.abspath(__file__))
CODES=json.load(open(os.path.join(HERE,'codes.json'),encoding='utf-8'))
H=os.path.join(HERE,'history.csv')
JST=datetime.timezone(datetime.timedelta(hours=9))
def get(code):
    u=f'https://query1.finance.yahoo.com/v8/finance/chart/{code}.T?range=1d&interval=5m'
    r=urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0 (educational non-commercial; tousi.com)'})
    for i in range(3):
        try: return json.load(urllib.request.urlopen(r,timeout=20))['chart']['result'][0]
        except Exception:
            if i==2: raise
            time.sleep(3+i*5)
def morning_close(res):
    ts=res.get('timestamp') or [];cl=res['indicators']['quote'][0]['close']
    best=None
    for t,c in zip(ts,cl):
        d=datetime.datetime.fromtimestamp(t,JST)
        if c is not None and (d.hour,d.minute)<=(11,30): best=(d,c)
    return best
def main(ed):
    now=datetime.datetime.now(JST)
    if now.weekday()>=5: print('weekend: skip');return
    new=not os.path.exists(H)
    def one(item):
        code,name=item
        try:
            res=get(code);m=res['meta']
            if datetime.datetime.fromtimestamp(m['regularMarketTime'],JST).date()!=now.date():
                price,at,note='','','休場または未更新'
            elif ed=='morning':
                b=morning_close(res)
                price,at,note=(round(b[1],1),b[0].strftime('%H:%M'),'') if b else ('','','取得できず')
            else:
                price,at,note=round(m['regularMarketPrice'],1),datetime.datetime.fromtimestamp(m['regularMarketTime'],JST).strftime('%H:%M'),''
            prev=m.get('chartPreviousClose') or m.get('previousClose') or ''
        except Exception as e:
            price,at,prev,note='','','',f'取得できず:{type(e).__name__}'
        time.sleep(random.uniform(0.2,0.6))
        return [now.strftime('%Y-%m-%d %H:%M:%S'),ed,name,code,price,at,prev,note]
    with ThreadPoolExecutor(5) as ex: rows=list(ex.map(one,CODES.items()))
    with open(H,'a',newline='',encoding='utf-8-sig' if new else 'utf-8') as f:
        w=csv.writer(f)
        if new: w.writerow(['取得日時','版','会社名','証券コード','価格','価格の時刻','前営業日終値','備考'])
        w.writerows(rows)
    J=os.path.join(HERE,'prices.json')
    try: data=json.load(open(J,encoding='utf-8'))
    except Exception: data={'stocks':{}}
    today=now.strftime('%Y-%m-%d')
    for r in rows:
        code=r[3];e=data['stocks'].get(code)
        if not e or e.get('day')!=today: e={'name':r[2],'day':today}
        if r[4]!='':
            e[ed]={'price':r[4],'time':r[5]}
            e['prev']=r[6]
        data['stocks'][code]=e
    data['updated']=now.strftime('%Y-%m-%d %H:%M')
    json.dump(data,open(J,'w',encoding='utf-8'),ensure_ascii=False,indent=1)
    print(len(rows),'rows;',sum(1 for r in rows if r[4]!=''),'with price')
if __name__=='__main__': main(sys.argv[1] if len(sys.argv)>1 else 'evening')
