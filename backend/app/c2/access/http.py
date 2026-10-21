"""Small private-route body limit, no-store responses and sanitized validation."""
from starlette.responses import JSONResponse
from ..microclimate.api.http import validation_error_handler as existing_handler


async def validation_error_handler(request,exc):
    if not request.url.path.startswith('/api/c2/access/'):
        return await existing_handler(request,exc)
    return JSONResponse(status_code=422,content={'detail':[
        {'loc':list(error['loc']),'msg':error['msg'],'type':error['type']} for error in exc.errors()]})


class AccessHTTP:
    def __init__(self,app):self.app=app

    async def __call__(self,scope,receive,send):
        if scope['type']!='http' or not scope.get('path','').startswith('/api/c2/access/'):
            return await self.app(scope,receive,send)
        async def no_store(message):
            if message['type']=='http.response.start':
                message['headers']=[*message.get('headers',[]),(b'cache-control',b'no-store'),(b'x-content-type-options',b'nosniff')]
            await send(message)
        chunks=[];size=0
        while True:
            message=await receive()
            if message['type']=='http.disconnect':return
            chunk=message.get('body',b'');size+=len(chunk)
            if size>16384:
                return await JSONResponse(status_code=413,content={'detail':'Local access requests must not exceed 16 KiB'})(scope,receive,no_store)
            chunks.append(chunk)
            if not message.get('more_body',False):break
        delivered=False
        async def replay():
            nonlocal delivered
            if not delivered:
                delivered=True;return {'type':'http.request','body':b''.join(chunks),'more_body':False}
            return await receive()
        return await self.app(scope,replay,no_store)
