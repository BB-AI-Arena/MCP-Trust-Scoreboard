"""Bounded explainable correlations. Observations are not causality/prevention."""
from datetime import datetime
import hashlib
from pathlib import PureWindowsPath


def correlate(event, state, policy):
    state = dict(state)
    history = state.get('events',[])
    history.append({k:event[k] for k in ('id','event_type','observed_at','data')})
    history = sorted(history,key=lambda e:e['observed_at'])[-512:]
    latest = max(datetime.fromisoformat(e['observed_at'].replace('Z','+00:00')).timestamp() for e in history)
    recent = [e for e in history if latest-datetime.fromisoformat(e['observed_at'].replace('Z','+00:00')).timestamp()<=120]
    emitted = state.get('emitted',[])
    findings = []

    def finding(rule,title,signals,context,relationship,severity='medium'):
        signature = hashlib.sha256((rule+str(context)+str(int(latest//600))).encode()).hexdigest()
        if signature in emitted:
            return
        emitted.append(signature)
        findings.append({'id':'endpoint-finding-'+hashlib.sha256((event['endpoint_id']+signature).encode()).hexdigest(),
            'workspace_id':event['workspace_id'],'subject_id':event['endpoint_id'],
            'endpoint_id':event['endpoint_id'],'source':'windows-endpoint','origin':'platform_rule',
            'rule_id':rule,'rule_version':'endpoint-rules-1','schema_version':'2026-01',
            'title':title,'severity':severity,'status':'open','context':context,
            'evidence_ids':sorted({e['id'] for e in signals})[:32],
            'observed_from':min(e['observed_at'] for e in signals),
            'observed_until':max(e['observed_at'] for e in signals),
            'relationship_type':relationship,'confidence':'limited_uncalibrated',
            'limitations':'Polling/collector reports are incomplete and unverified; no proof of AI causation, exfiltration or malware. Review required.',
            'response':{'requested_action':None,'target':event['endpoint_id'],'policy':policy['version'],'approval_required':True,'executed':False}})

    repositories = {r['id']:r for r in policy['repositories']}
    tools = [e for e in recent if e['event_type']=='ai_tool_running' and e['data']['tool_id'] not in policy['approved_tools']]
    files = [e for e in recent if e['event_type'] in ('file_created','file_modified','file_renamed','file_deleted','repository_interaction')]
    for f in files:
        repo = repositories.get(f['data']['repository_id'])
        if repo and repo['classification'] in ('Confidential','Restricted','Regulated'):
            for tool in tools[:10]:
                finding('shadow-ai-sensitive-repository','Shadow AI near sensitive repository',[tool,f],
                    {'tool':tool['data']['tool_id'],'repository_id':repo['id'],'sensitivity':repo['classification']},
                    'temporal_endpoint_copresence_file_process_unknown')

    processes = {e['data']['process_key']:e for e in recent if e['event_type']=='process_started'}
    networks = [e for e in recent if e['event_type']=='process_network_connection' and e['data']['direction']=='outbound_candidate']
    groups = {}
    for e in networks:
        groups.setdefault((e['data']['process_key'],e['data']['destination_ip']),[]).append(e)
    for (key,ip), observations in groups.items():
        process = processes.get(key)
        times = sorted({datetime.fromisoformat(e['observed_at'].replace('Z','+00:00')).timestamp() for e in observations})
        if process and process['data'].get('parent_key') and len(times)>=5 and times[-1]-times[0]>=4 and ip not in policy['known_destinations']:
            intervals = [b-a for a,b in zip(times,times[1:])]
            if max(intervals)-min(intervals)<=2:
                finding('periodic-unlisted-destination','Suspected command-and-control behavior',observations+[process],
                    {'destination_ip':ip,'process_key':key,'destination_context':'not_in_operator_known_destinations'},'experimental_periodic_connections_with_ancestry')

    for repo_id in repositories:
        activity = [e for e in files if e['data']['repository_id']==repo_id and e['event_type'] in ('file_modified','file_renamed')]
        renames = [e for e in activity if e['event_type']=='file_renamed']
        directories = {str(PureWindowsPath(e['data']['relative_path']).parent) for e in activity}
        if len(activity)>=20 and len(renames)>=10 and len(directories)>=3:
            finding('destructive-file-pattern','Suspected destructive file behavior',activity,
                {'repository_id':repo_id,'changes':len(activity),'renames':len(renames),'directories':len(directories)},'experimental_metadata_burst_process_unknown','high')
    if event['event_type']=='process_started' and event['data'].get('sha256') in policy['indicator_sha256']:
        finding('configured-hash-indicator','Known-indicator match',[event],{'sha256':event['data']['sha256']},'operator_configured_hash_indicator')
    state.update(events=history,emitted=emitted[-128:])
    return state, findings
