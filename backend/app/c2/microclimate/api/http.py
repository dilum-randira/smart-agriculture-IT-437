"""Route-scoped payload limit and sanitized validation; other components unchanged."""
from fastapi.exception_handlers import request_validation_exception_handler
from starlette.responses import JSONResponse

MAX_REQUEST_BYTES=256*1024


async def validation_error_handler(request,exc):
    if not request.url.path.startswith('/api/c2/microclimate/'):
        return await request_validation_exception_handler(request,exc)
    # Avoid echoing a 336-row payload, exception objects or internal information.
    return JSONResponse(status_code=422,content={'detail':[
        {'loc':list(error['loc']),'msg':error['msg'],'type':error['type']} for error in exc.errors()]})


class MicroclimateBodyLimit:
    def __init__(self,app):
        self.app=app

    async def __call__(self,scope,receive,send):
        if scope['type']!='http' or scope.get('method')!='POST' or scope.get('path')!='/api/c2/microclimate/forecast':
            return await self.app(scope,receive,send)
        headers=dict(scope.get('headers',[]))
        try:
            declared=int(headers.get(b'content-length',b'0'))
        except ValueError:
            return await JSONResponse(status_code=400,content={'detail':{'code':'invalid_content_length'}})(scope,receive,send)
        if declared>MAX_REQUEST_BYTES:
            return await self._too_large(scope,receive,send)
        chunks=[];size=0
        while True:
            message=await receive()
            if message['type']=='http.disconnect':
                return
            chunk=message.get('body',b'');size+=len(chunk)
            if size>MAX_REQUEST_BYTES:
                return await self._too_large(scope,receive,send)
            chunks.append(chunk)
            if not message.get('more_body',False):
                break
        body=b''.join(chunks);delivered=False
        async def replay():
            nonlocal delivered
            if not delivered:
                delivered=True
                return {'type':'http.request','body':body,'more_body':False}
            return await receive()
        return await self.app(scope,replay,send)

    @staticmethod
    async def _too_large(scope,receive,send):
        return await JSONResponse(status_code=413,content={'detail':{
            'code':'request_too_large','message':'Microclimate forecast requests must not exceed 256 KiB'}})(scope,receive,send)
