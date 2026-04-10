import sys, requests
BASE_URL='http://localhost:5000'
def check(method,path,expected=200,json_body=None):
    url=BASE_URL+path
    if method=='GET': r=requests.get(url,timeout=10)
    else: r=requests.post(url,json=json_body or {},timeout=20)
    return r.status_code == expected, f'{method} {path} -> {r.status_code}'
def main():
    checks=[('GET','/health/live',200,None),('GET','/health/ready',200,None),('GET','/api/test',200,None),('GET','/api/engine-status',200,None),('GET','/api/stats',200,None),('GET','/metrics',200,None),('POST','/api/analyze',200,{'sport':'football','competition':'epl','home_team':'Arsenal','away_team':'Chelsea','use_cache':True,'force_refresh':False})]
    failed=0
    for m,p,e,b in checks:
        ok,msg=check(m,p,e,b); print(('[PASS] ' if ok else '[FAIL] ')+msg); failed += 0 if ok else 1
    sys.exit(1 if failed else 0)
if __name__=='__main__': main()
