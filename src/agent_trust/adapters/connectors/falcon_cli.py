"""Explicit operator interface; never run live collection from ordinary CI."""
import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

from agent_trust.config import Settings
from agent_trust.storage.database import create_schema, make_engine
from .falcon_client import FalconConfig, FalconError, REGIONS
from .falcon_collect import check_connection, sync_once


def main():
    parser = argparse.ArgumentParser(description='Read-only Falcon host/alert source; credentials from private environment only')
    parser.add_argument('command', choices=['check','sync-once','live-smoke'])
    parser.add_argument('--connection',required=True)
    parser.add_argument('--account-cid',required=True)
    parser.add_argument('--region',choices=REGIONS,default='us-1')
    parser.add_argument('--since',default=(datetime.now(timezone.utc)-timedelta(days=1)).isoformat())
    parser.add_argument('--agent-map',type=Path)
    parser.add_argument('--page-size',type=int,default=100)
    parser.add_argument('--max-pages',type=int,default=5)
    parser.add_argument('--seconds',type=int,default=120)
    parser.add_argument('--replay',action='store_true',help='Replay explicit backfill, preserving all existing records')
    parser.add_argument('--authorize-live-read',action='store_true',help='Required for the optional bounded live smoke')
    args = parser.parse_args()
    engine = None
    try:
        config = FalconConfig.from_env(args.connection,args.account_cid,args.region)
        if args.command=='live-smoke' and not args.authorize_live_read:
            raise FalconError('explicit_live_read_authorization_required')
        config.validate()  # Fail missing vendor credentials before any DB access.
        if args.command in ('check','live-smoke'):
            result = check_connection(config)
        else:
            settings = Settings.from_env()
            settings.validate()
            engine = make_engine(settings.database_url)
            if engine.dialect.name!='postgresql':
                raise FalconError('postgresql_required')
            mapping = {}
            if args.agent_map:
                if args.agent_map.stat().st_size>1_000_000:
                    raise FalconError('agent_mapping_too_large')
                mapping = json.loads(args.agent_map.read_text())
            create_schema(engine)
            result = sync_once(engine,config,settings.workspace_id,since=args.since,
                agent_mapping=mapping,page_size=args.page_size,max_pages=args.max_pages,
                seconds=args.seconds,replay=args.replay)
        print(json.dumps(result))
        return 0 if result['status']=='complete' else 2
    except FalconError as error:
        print(json.dumps({'status':'unavailable','error':str(error)}))
        return 2
    except Exception:
        # No DB URLs, request/response text, tokens, traceback or environment dump.
        print(json.dumps({'status':'unavailable','error':'configuration_or_storage_failure'}))
        return 2
    finally:
        if engine:
            engine.dispose()


if __name__=='__main__':
    raise SystemExit(main())
