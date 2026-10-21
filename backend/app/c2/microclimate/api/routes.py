"""Router integrated with the existing shared FastAPI application."""
from fastapi import APIRouter, HTTPException, Query
import logging

from .schemas import ForecastRequest, ForecastResponse, DemoInput, ModelID, NodeID
from .service import forecast, InvalidHistory, ModelUnavailable, InferenceFailure
from .demo import demo_input

router=APIRouter(prefix='/api/c2/microclimate',tags=['C2 Microclimate Forecasting'])


def _safe_call(function,*args):
    try:
        return function(*args)
    except InvalidHistory as exc:
        raise HTTPException(status_code=422,detail=dict(code='invalid_history',message=str(exc))) from exc
    except ModelUnavailable as exc:
        raise HTTPException(status_code=503,detail=dict(code='model_unavailable',message=str(exc))) from exc
    except InferenceFailure as exc:
        raise HTTPException(status_code=500,detail=dict(code='forecast_failed',message=str(exc))) from exc
    except Exception as exc:
        logging.getLogger(__name__).exception('Unexpected microclimate request failure')
        raise HTTPException(status_code=500,detail=dict(code='forecast_failed',message='Unable to complete forecast request')) from exc


@router.post('/forecast',response_model=ForecastResponse,
             summary='Frozen 336-to-168-hour synthetic-prototype forecast',
             responses={422:{'description':'Invalid or unsupported historical input'},
                        413:{'description':'Request exceeds 256 KiB'},503:{'description':'Frozen model artifacts unavailable'}})
def forecast_endpoint(request:ForecastRequest):
    return _safe_call(forecast,request)


@router.get('/demo-input',response_model=DemoInput,
            summary='Read-only synthetic historical request; no future targets')
def demo_endpoint(model:ModelID='attention_bilstm',node_id:NodeID='NODE_01',
                  sample_index:int=Query(default=0,ge=0,le=810)):
    return _safe_call(demo_input,model,node_id,sample_index)
