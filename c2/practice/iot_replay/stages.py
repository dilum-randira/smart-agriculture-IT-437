"""Practice crop-stage history with leakage-safe as-of lookup.

An event must BOTH have been observed and documented by the forecast issue
instant. Backfilled entries are not visible to forecasts issued earlier.
"""
from schema import parse_aware_datetime, STAGES


def validate_stage_event(event):
    if not isinstance(event, dict):
        raise ValueError('stage event must be a dictionary')
    plot_id=event.get('plot_id')
    if not isinstance(plot_id,str) or not plot_id.strip():
        raise ValueError('plot_id required')
    stage=event.get('growth_stage')
    if stage not in STAGES:
        raise ValueError('invalid growth stage')
    observed=parse_aware_datetime(event.get('observed_at'))
    recorded=parse_aware_datetime(event.get('recorded_at'))
    if recorded < observed:
        raise ValueError('recorded_at cannot precede observed_at')
    return {'plot_id':plot_id, 'growth_stage':stage,
            'observed_at':observed, 'recorded_at':recorded}


def stage_as_of(events,plot_id,issued_at):
    issue=parse_aware_datetime(issued_at)
    eligible=[]
    for item in events:
        event=validate_stage_event(item)
        if (event['plot_id']==plot_id and event['observed_at']<=issue
                and event['recorded_at']<=issue):
            eligible.append(event)
    if not eligible:
        return None
    selected=max(eligible,key=lambda e:(e['observed_at'],e['recorded_at']))
    return {'growth_stage':selected['growth_stage'],
            'stage_observed_at':selected['observed_at'].isoformat(),
            'stage_recorded_at':selected['recorded_at'].isoformat(),
            'status':'observed'}
