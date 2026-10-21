"""Loopback-only local access control. Legacy stateless synthetic APIs stay unchanged."""
from functools import lru_cache
import hmac
import ipaddress
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from .schemas import Login, Register, NewUser, UserUpdate, NewFarm, FarmWrite, SiteWrite, NodeWrite, Assignment, Membership, ForecastSelection
from .store import Store, DEMO_FARM, csrf_token, default_path
from ..microclimate.api.demo import demo_input
from ..microclimate.api.routes import _safe_call
from ..microclimate.api.service import forecast

COOKIE = 'c2_local_session'
COOKIE_PATH = '/api/c2'
ORIGINS = {f'http://{host}:{port}' for host in ('localhost','127.0.0.1') for port in (5173,8000)}


def local_only(request: Request):
    try: local = ipaddress.ip_address(request.client.host).is_loopback
    except (ValueError, AttributeError): local = False
    if not local or request.url.hostname not in ('127.0.0.1','localhost','::1'):
        raise HTTPException(403,'This PP1 access service is available on loopback only')
    origin=request.headers.get('origin')
    if origin and origin not in ORIGINS: raise HTTPException(403,'Origin not permitted')


@lru_cache(maxsize=4)
def _open(path):
    return Store(path)


def get_store():
    return _open(str(default_path()))


def authenticated(request: Request, db: Store=Depends(get_store)):
    return db.principal(request.cookies.get(COOKIE))


def mutation(request: Request, user=Depends(authenticated)):
    token=request.cookies.get(COOKIE,'')
    supplied=request.headers.get('x-csrf-token','')
    if not hmac.compare_digest(supplied,csrf_token(token)):
        raise HTTPException(403,'Valid CSRF token required')
    return user


def admin(user=Depends(mutation)):
    if user['role']!='admin': raise HTTPException(403,'Administrator permission required')
    return user


def runner(user=Depends(mutation)):
    if user['role'] not in ('admin','researcher','viewer'): raise HTTPException(403,'Forecast permission required')
    return user


def farm_editor(user=Depends(mutation)):
    if user['role'] not in ('admin','viewer'): raise HTTPException(403,'Farmer or Admin permission required')
    return user


def yield_access(request: Request,user=Depends(authenticated)):
    # Yield accepts manual agronomic inputs, not farm IDs or protected observations.
    if user['role'] not in ('admin','researcher','viewer'): raise HTTPException(403,'Prediction permission required')
    if request.method not in ('GET','HEAD','OPTIONS'): mutation(request,user)
    return user


def research_access(request: Request,user=Depends(authenticated),db: Store=Depends(get_store)):
    """Conservative rule for legacy research APIs without farm ownership fields."""
    if user['role'] not in ('admin','researcher'):
        raise HTTPException(403,'Research access requires Admin or Researcher permission; use assigned saved forecasts')
    if user['role']!='admin':
        with db.db() as connection: db.farm_access(connection,user,DEMO_FARM,member=True)
    if request.method not in ('GET','HEAD','OPTIONS'):
        mutation(request,user)
    return user


def session_cookie(response,token,remaining):
    # Migrate earlier access-only cookies without changing their server-side session.
    response.delete_cookie(COOKIE,path='/api/c2/access')
    response.set_cookie(COOKIE,token,max_age=remaining,httponly=True,samesite='strict',secure=False,path=COOKIE_PATH)


router=APIRouter(prefix='/api/c2/access',tags=['C2 Local Access & Farms'],dependencies=[Depends(local_only)])


@router.post('/register',status_code=201)
def register(data: Register,request: Request,db: Store=Depends(get_store)):
    # Mandatory trusted browser origin prevents cross-site account creation.
    if request.headers.get('origin') not in ORIGINS: raise HTTPException(403,'Trusted origin required')
    db.register(data,request.client.host)
    return {'status':'created','role':'viewer'}


@router.post('/login')
def login(data: Login, request: Request, response: Response, db: Store=Depends(get_store)):
    old=request.cookies.get(COOKIE)
    token=db.login(data.username,data.password.get_secret_value(),request.client.host)
    if old: db.logout(old)
    session_cookie(response,token,db.session_remaining(token))
    return dict(user=db.principal(token),csrf_token=csrf_token(token))


@router.get('/me')
def me(request: Request,response: Response,user=Depends(authenticated),db: Store=Depends(get_store)):
    session_cookie(response,request.cookies[COOKIE],db.session_remaining(request.cookies[COOKIE]))
    return dict(user=user,csrf_token=csrf_token(request.cookies[COOKIE]))


@router.post('/logout')
def logout(request: Request,response: Response,user=Depends(mutation),db: Store=Depends(get_store)):
    db.logout(request.cookies[COOKIE]);response.delete_cookie(COOKIE,path=COOKIE_PATH)
    response.delete_cookie(COOKIE,path='/api/c2/access')
    return {'status':'signed_out'}


@router.get('/users')
def users(user=Depends(authenticated),db: Store=Depends(get_store)):
    if user['role']!='admin':raise HTTPException(403,'Administrator permission required')
    return db.users()


@router.post('/users',status_code=201)
def create_user(data: NewUser,user=Depends(admin),db: Store=Depends(get_store)):
    return {'user_id':db.create_user(data)}


@router.put('/users/{user_id}')
def update_user(user_id: str,data: UserUpdate,user=Depends(admin),db: Store=Depends(get_store)):
    db.update_user(user_id,data);return {'status':'updated; sessions revoked'}


@router.get('/farms')
def farms(user=Depends(authenticated),db: Store=Depends(get_store)):
    return db.farms(user)


@router.post('/farms',status_code=201)
def create_farm(data: NewFarm,user=Depends(farm_editor),db: Store=Depends(get_store)):
    return {'farm_id':db.write_farm(user,data)}


@router.put('/farms/{farm_id}')
def update_farm(farm_id: str,data: FarmWrite,user=Depends(farm_editor),db: Store=Depends(get_store)):
    return {'farm_id':db.write_farm(user,data,farm_id)}


@router.post('/farms/{farm_id}/sites',status_code=201)
def create_site(farm_id: str,data: SiteWrite,user=Depends(admin),db: Store=Depends(get_store)):
    return {'site_id':db.site(user,farm_id,data.site_name)}


@router.put('/farms/{farm_id}/members/{user_id}')
def membership(farm_id: str,user_id: str,data: Membership,user=Depends(admin),db: Store=Depends(get_store)):
    db.membership(user,farm_id,user_id,data.granted);return {'status':'updated'}


@router.put('/farms/{farm_id}/sites/{site_id}')
def rename_site(farm_id: str,site_id: str,data: SiteWrite,user=Depends(admin),db: Store=Depends(get_store)):
    db.rename_site(user,farm_id,site_id,data.site_name);return {'site_id':site_id}


@router.get('/nodes')
def nodes(user=Depends(authenticated),db: Store=Depends(get_store)):
    if user['role']!='admin':raise HTTPException(403,'Administrator permission required')
    with db.db() as connection:return [dict(row) for row in connection.execute('SELECT * FROM nodes ORDER BY node_id')]


@router.post('/nodes',status_code=201)
def register_node(data: NodeWrite,user=Depends(admin),db: Store=Depends(get_store)):
    db.register_node(data);return {'node_id':data.node_id}


@router.put('/farms/{farm_id}/nodes/{node_id}')
def assign_node(farm_id: str,node_id: str,data: Assignment,user=Depends(admin),db: Store=Depends(get_store)):
    db.assign_node(user,farm_id,data.site_id,node_id);return {'status':'assigned'}


@router.get('/farms/{farm_id}/history')
def history(farm_id: str,site_id: str,node_id: str,user=Depends(authenticated),db: Store=Depends(get_store)):
    db.source(user,farm_id,site_id,node_id)
    return _safe_call(demo_input,'attention_bilstm',node_id,0)


@router.post('/farms/{farm_id}/forecast')
def run_forecast(farm_id: str,data: ForecastSelection,user=Depends(runner),db: Store=Depends(get_store)):
    db.source(user,farm_id,data.site_id,data.node_id)
    history=_safe_call(demo_input,data.model,data.node_id,0)
    result=_safe_call(forecast,history.request)
    forecast_id=db.save_forecast(user,farm_id,data,history.request,result)
    return dict(forecast_id=forecast_id,farm_id=farm_id,site_id=data.site_id,response=result)


@router.get('/farms/{farm_id}/forecasts')
def saved_forecasts(farm_id: str,site_id: str,node_id: str,user=Depends(authenticated),db: Store=Depends(get_store)):
    return db.forecasts(user,farm_id,site_id,node_id)
