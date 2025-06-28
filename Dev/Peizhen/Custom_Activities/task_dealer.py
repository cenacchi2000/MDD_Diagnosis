"""
Set up sockets etc for custom tasks. 

See https://docs.engineeredarts.co.uk/ for more information
"""
import zmq
import zmq.asyncio
from zmq.asyncio import Context

HOST_ADDR = system.import_library('../conf.py').HOST_ADDR
CONST = system.import_library("../const.py")
ENCODING = CONST.ENCODING
CustomTasks = CONST.CustomTasks


class TaskDealer:
    def __init__(self):
        super(TaskDealer, self).__init__()
        print('=====init task dealer=====')
        ctx = Context.instance() 
        self._deal_sock = ctx.socket(zmq.DEALER)
        self._deal_sock.setsockopt(zmq.IDENTITY, CONST.SOCK_DEALER_ID)
        # self._deal_sock.setsockopt(zmq.CONFLATE, 1) # NOTE, use this will cause some args being swallowed
        self._deal_sock.bind(HOST_ADDR)
        
        
        
    def __del__(self):
        print('=====del vtask dealer=====')
        if self._deal_sock:
            self._deal_sock.setsockopt(zmq.LINGER, 0)
        if hasattr(self, '_deal_sock'):
            self._deal_sock = None

    # TODO check args (should be bytes-like object)
    async def deal_custom_tasks(self, *args):
        encoded_args = [arg.encode(ENCODING) for arg in args]
        await self._deal_sock.send_multipart(encoded_args) 
        resp = await self._deal_sock.recv_multipart()
        return [item.decode(ENCODING) for item in resp]
