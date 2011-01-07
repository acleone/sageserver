"""
twistd -noy manager.py
"""

from zope.interface import Interface, implements

from twisted.internet import epollreactor
epollreactor.install()

from twisted.application import internet, service
from twisted.internet import protocol, reactor, defer, error
from twisted.python import components, log

from twisted.web.resource import Resource

class WorkerProcess(protocol.ProcessProtocol):
    def __init__(self, key):
        self.key = key
    def outReceived(self, data):
        print "outReceived: " + str(data)
    def errReceived(self, data):
        print "errReceived: " + str(data)
    def processEnded(self, reason):
        print "processEnded, status %s" % (reason.value.exitCode,)
    

class WorkerProtocol(protocol.Protocol):
    def __init__(self):
        self._buf = b''
        self._worker = None
        
    def set_worker(self, worker):
        self._buf = None
        self._feed_parser = msg.FeedParser()
        self._worker = worker
        
    def dataReceived(self, data):
        print "dataReceived: " + repr(data)
        if self._worker: # we have successfully authed, parse messages.
            for m in self._feed_parser.feed(data):
                self._worker.msg_recv(m)
        else: # we haven't authed yet, still receiving key
            self._buf += data
            keysize = self.factory.config['exc_keysize'] * 2
            if len(self._buf) > keysize:
                return self.invalid_key(self._buf)
            elif len(self._buf) == keysize:
                self.factory.service.auth_worker(self._buf, self)


    def invalid_key(self, key):
        print "Invalid Key: " + repr(key)
        return self.transport.loseConnection()


class IWorkerService(Interface):
    def startService(self):
        """lalalala"""
    
class IWorkerFactory(Interface):
    def buildProtocol(addr):
        """Return a protocol returning a string"""

class WorkerFactoryFromService(protocol.ServerFactory):
    implements(IWorkerFactory)
    protocol = WorkerProtocol
    
    def __init__(self, service):
        self.service = service
        self.config = service.config

components.registerAdapter(WorkerFactoryFromService,
                           IWorkerService,
                           IWorkerFactory)
                           
class Worker(object):
    def __init__(self, process, protocol):
        self.process = process
        self.protocol = protocol
        protocol.set_worker(self)
        self._client = None
        
    def set_client(self, c):
        self._client = c
        
    def msg_recv(self, m):
        """
        Called by WorkerProtocol when messages are received.
        """
        print repr(m)
        if self._client:
            self._client.msg_send(m)
            
        
    def msg_send(self, m):
        """
        Sends a message via protocol.transport.write().
        """
        self.protocol.transport.write(m.encode())
        
class Client(object):
    def __init__(self, protocol):
        self.protocol = protocol
        
    def msg_recv(m):
        """
        Client sent us a message.
        """
        
    def msg_send(m):
        """
        Send Client a message.
        """
        
class WebSocketClient(websocket.WebSocketHandler):
    def __init__(self, transport):
        websocket.WebSocketHandler.__init__(self, transport)
        self._service = self.transport._request.site.service
        self._worker = None
    
    def set_worker(self, worker, exec_msg):
        self._worker = worker
        worker.set_client(self)
        worker.msg_send(exec_msg)
        
    def msg_send(self, m):
        self.transport.write(json.dumps(m.json_dict()))
        
        
    def frameReceived(self, frame):
        """
        Called when a frame is received.

        @param frame: a I{UTF-8} encoded C{str} sent by the client.
        @type frame: C{str}
        """
        print "Got frame " + repr(frame)
        mjson = json.loads(frame)
        clsname = mjson['type']
        cls = getattr(msg, clsname)
        del mjson['type']
        m = cls(**mjson)
        if self._worker:
            self._worker.msg_send(m)
        elif isinstance(m, msg.Exec):
            # assign ourselves to a worker
            self._service.get_worker(self.set_worker, m)
            


    def frameLengthExceeded(self):
        """
        Called when too big a frame is received. The default behavior is to
        close the connection, but it can be customized to do something else.
        """
        self.transport.loseConnection()


    def connectionLost(self, reason):
        """
        Callback called when the underlying transport has detected that the
        connection is closed.
        """
        # TODO: replace this with a timeout
        if self._worker:
            self._worker.msg_send(msg.Shutdown())

        
class WorkerService(service.Service):
    implements(IWorkerService)

    def __init__(self, config):
        self.config = config
        self._unauthed = {} # key -> WorkerProcess
        from collections import deque
        self._idle = deque() # (wp, protocol)
        self._get_worker_callbacks = deque() # (cb_func, args, kwargs)
        
    def startService(self):
        self._spawn_workers()
        
    def _spawn_workers(self):
        """
        Starts idle worker processes to fill the idle pool.
        """
        n = self.config['exc_idle_workers'] - (
                len(self._unauthed) + len(self._idle))
        if n <= 0:
            return
            
        for i in range(n):
            from os import urandom
            key_bytes = urandom(self.config['exc_keysize'])
            key = ''.join( ['%02x' % ord(b) for b in key_bytes] )
            wp = WorkerProcess(key)
            timeout = reactor.callLater(self.config['exc_auth_timeout'],
                    self._unauthed_timeout, key, wp)
            self._unauthed[key] = (wp, timeout)
            reactor.spawnProcess(wp, "python",
                                 args=["python", "worker.py",
                                       self.config['exc_host'],
                                       str(self.config['exc_port']), key])
        
    def auth_worker(self, key, protocol):
        """
        call protocol.invalid_key(key) if the key was invalid.
        """
        try:
            process, timeout = self._unauthed[key]
        except KeyError:
            return protocol.invalid_key(key)
        timeout.cancel()
        del self._unauthed[key]
        w = Worker(process, protocol)
        self._idle.append(w)
        self._assign_workers()
        
    def get_worker(self, callback_func, *args, **kwargs):
        self._get_worker_callbacks.append((callback_func, args, kwargs))
        self._assign_workers()

    def _assign_workers(self):
        """
        Tries to service any get_worker calls.
        """
        log.msg("idle size: %d  get_worker size: %d" % (len(self._idle),
                len(self._get_worker_callbacks)))
        if self._get_worker_callbacks and self._idle:
            # match them up
            w = self._idle.popleft()
            cb, args, kwargs = self._get_worker_callbacks.popleft()
            cb(w, *args, **kwargs)
            self._fill_idle_pool()
            
            
    def _unauthed_timeout(self, key, wp):
        """
        Called when a worker hasn't authed yet and should be removed.
        """
        if key not in self._unauthed:
            log.err("Not found in self._unauthed!")
            return
        log.err("Unauthed timeout: " + repr(wp))
        wp.transport.loseConnection()
        wp.transport.signalProcess('KILL')
        del self._unauthed[key]
        self._fill_idle_pool()
        
    def add_client(self, client):
        ws_handler.service


def makeService(config):
    # tcp for execution clients that we will spawn
    s = service.MultiService()
    w = WorkerService(config)
    w.setServiceParent(s)
    h = internet.TCPServer(config['wkr_port'], IWorkerFactory(w))
    h.setServiceParent(s)
    
    return s
    
ser = makeService({
    'wkr_host': '127.0.0.1',
    'wkr_port': 8045,
    'wkr_keysize': 10,
    'wkr_n_idle': 2,
    'wkr_auth_timeout': 5.0,
})
application = service.Application('sage_worker')
ser.setServiceParent(service.IServiceCollection(application))