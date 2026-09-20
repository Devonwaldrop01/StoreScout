"""Explicit local init/import/export; no automatic production schema changes."""
import argparse
from datetime import datetime,timezone,timedelta
import hashlib
import json
import os
from pathlib import Path
import signal
import sys
import time
from .identity import prepare,digest
from .store import Store


def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['prepare','init','seed','status','metrics','export','backup','run'])
    parser.add_argument('--db',default='/var/data/store-index-v2.sqlite')
    parser.add_argument('--input');parser.add_argument('--output');parser.add_argument('--batch-size',type=int,default=100)
    parser.add_argument('--target',type=int,default=1000);parser.add_argument('--expires-at')
    args=parser.parse_args(argv)
    if args.action=='prepare':
        raw=Path(args.input).read_bytes()
        if not args.expires_at: raise ValueError('Explicit reviewed expiry required')
        manifest=prepare(json.loads(raw),batch_size=args.batch_size,expires_at=args.expires_at,
                         source_sha256=hashlib.sha256(raw).hexdigest(),target_eligible=args.target)
        with Path(args.output).open('x',encoding='utf8') as f: json.dump(manifest,f,indent=2)
        print(digest(manifest));return
    if args.action=='init': Store.initialize(args.db);return
    if args.action=='run':
        from .worker import assert_isolated_env,run
        assert_isolated_env()
        stopped=False
        def stop(*args):
            nonlocal stopped
            stopped=True
        signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
        if os.environ.get('INDEX_V2_ENABLED')!='true':
            print('STORE_INDEX_V2 disabled; no jobs or application initialized',flush=True)
            while not stopped: time.sleep(.5)
            return
        if sys.platform!='linux' or not os.path.ismount('/var/data') or Path(args.db).resolve().parent!=Path('/var/data'):
            raise ValueError('Production execution requires the dedicated /var/data persistent Linux mount')
        store=Store(args.db)
        try: run(store,os.environ.get('INDEX_V2_MANIFEST_SHA256',''),lambda:stopped)
        finally: store.close()
        return
    store=Store(args.db)
    try:
        if args.action=='seed': print(store.seed(json.loads(Path(args.input).read_text(encoding='utf8'))))
        elif args.action=='status': print(json.dumps(store.summary(),indent=2))
        elif args.action=='metrics': print(json.dumps(store.metrics(),indent=2))
        elif args.action=='backup': store.backup(args.output)
        elif args.action=='export':
            from .experiment import export
            export(store,Path(args.output),Path(args.input) if args.input else None)
    finally: store.close()


if __name__=='__main__': main()
