"""Bounded public HTTPS, existing curl transport, explicit certificate checks.

No proxies, challenge retries, browser processes or credentialed endpoints.
DNS addresses are validated and pinned so a re-resolution cannot reach private IPs.
"""
import ipaddress
import socket
import time
from urllib.parse import urlsplit,urljoin
from .identity import canonical


class Transport:
    def __init__(self,host):
        self.host=host;self.deadline=time.monotonic()+75
        self.requests=[];self.stop_state=None;self.last_request=0;self.protection_events=[]
    def __enter__(self): return self
    def __exit__(self,*args): pass
    def pace(self,*args): pass  # actual per-request pacing below; no Redis

    def get(self,client,url,timeout=12):
        from app.services.store_index import _protection_result
        from app.services.fetch import IMPERSONATE,_headers
        from curl_cffi import CurlOpt
        from curl_cffi.requests import Session
        while True:
            if self.stop_state: raise RuntimeError('Previous protection/budget response stopped this pass')
            parsed=urlsplit(url)
            if parsed.scheme!='https' or parsed.username or parsed.password or parsed.port not in (None,443) or canonical(parsed.hostname)!=canonical(self.host):
                self.stop_state='ambiguous';raise ValueError('Unapproved redirect destination')
            if len(self.requests)>=8 or time.monotonic()>=self.deadline:
                self.stop_state='temporarily_unreachable';raise TimeoutError('Request budget reached')
            time.sleep(max(0,1-(time.monotonic()-self.last_request)))
            addresses={a[4][0] for a in socket.getaddrinfo(parsed.hostname,443,type=socket.SOCK_STREAM)}
            if not addresses or any(not ipaddress.ip_address(a).is_global for a in addresses):
                self.stop_state='ambiguous';raise ValueError('Nonpublic address rejected')
            ip=sorted(addresses,key=lambda a:(':' in a,a))[0]
            if ':' in ip: ip='['+ip+']'
            event={'host':parsed.hostname,'path':parsed.path,'status':None};self.requests.append(event)
            started=time.monotonic();self.last_request=started
            remaining=self.deadline-started
            if remaining<=0: self.stop_state='temporarily_unreachable';raise TimeoutError('Deadline')
            body=bytearray()
            def receive(chunk):
                if len(body)+len(chunk)>8*1024*1024: raise ValueError('Response body limit')
                body.extend(chunk)
            try:
                with Session(impersonate=IMPERSONATE,headers=_headers(),verify=True,trust_env=False,
                    curl_options={CurlOpt.RESOLVE:[f'{parsed.hostname}:443:{ip}']}) as session:
                    response=session.get(url,allow_redirects=False,timeout=min(timeout,remaining),
                        verify=True,content_callback=receive,discard_cookies=True)
                response.content=bytes(body)
                event.update(status=response.status_code,bytes=len(body),seconds=time.monotonic()-started)
            except Exception:
                event['error']='transport_failure';self.stop_state='temporarily_unreachable';raise
            protection=_protection_result(response,{})
            if protection:
                self.stop_state=protection['access_state']
                from .protection import observed,journal
                evidence=observed(parsed.path,response.status_code,event['seconds'],len(body),protection)
                if evidence:
                    self.protection_events.append(evidence)
                    journal(self.protection_events)
            if 300<=response.status_code<400:
                location=response.headers.get('location')
                if not location: self.stop_state='ambiguous';raise ValueError('Redirect missing location')
                url=urljoin(url,location)
                continue
            return response
