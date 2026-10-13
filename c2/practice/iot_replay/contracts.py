"""Versioned, JSON-serializable forecast messages for interface PRACTICE ONLY.

There are no invented prediction intervals: None means 'not estimated'.
A persistence output is explicitly labelled as untrained reference.
"""
from datetime import timedelta
from hashlib import sha256
from schema import parse_aware_datetime
from stages import stage_as_of


def publishable_payload(practice_result, data_version='synthetic-practice-v1', stage_events=()):
    if practice_result.get('source') != 'synthetic_practice':
        raise ValueError('only synthetic practice results are permitted')
    if practice_result.get('model') != 'persistence_reference_not_trained':
        raise ValueError('unexpected model family for practice interface')
    issued_at=practice_result['issued_at']
    parse_aware_datetime(issued_at)
    plot_id=practice_result['plot_id']
    stage=stage_as_of(stage_events,plot_id,issued_at)
    status=practice_result['status']
    if status not in ('provisional','stale','unavailable'):
        raise ValueError('unknown forecast status')
    if status!='provisional' and practice_result.get('forecast'):
        raise ValueError('unavailable forecasts must not contain fabricated values')

    predictions=[]
    for step in practice_result.get('forecast',()):
        end=parse_aware_datetime(step['target_end'])
        start=end-timedelta(hours=1)
        if end<=parse_aware_datetime(issued_at):
            raise ValueError('target period must be after issue time')
        for variable,measurement in step['values'].items():
            key='|'.join([plot_id,issued_at,end.isoformat(),variable,data_version])
            predictions.append({
                'prediction_id': sha256(key.encode('utf-8')).hexdigest()[:24],
                'plot_id':plot_id,
                'issued_at':issued_at,
                'target_start':start.isoformat(),
                'target_end':end.isoformat(),
                'variable':variable,
                'unit':measurement['unit'],
                'median':measurement['value'],
                'lower':None,'upper':None,'interval_level':None,
                'model_version':practice_result['model_version'],
                'data_version':data_version,
                'status':status,
                'source':'synthetic_practice',
                'prediction_type':'untrained_persistence_reference',
            })
    return {
        'message_type':'synthetic_c2_practice_forecast',
        'plot_id':plot_id,
        'issued_at':issued_at,
        'input_end':practice_result.get('input_end'),
        'status':status,
        'reason':practice_result.get('reason'),
        'growth_stage':stage,
        'predictions':predictions,
        'note':'PRACTICE ONLY; synthetic inputs, untrained reference, no intervals',
    }
