""" Enables Python classes which have JavaScript mirrors; the two seamlessly
communicate with RPC and you can define properties (of DOM nodes and other
JSObjects) that are transferred from server to client. The JavaScript classes
are ``Widget``s from ``mythril.js``, the JavaScript component of this library.

To create such a class, see `JSObject`. To enable RPC, you need to serve
`rpcApp`, a WSGI application, and set up `rpcHost` (default /_rpc) to the
virtual path it is served from.
"""

rpcHost = u'/_rpc'

def rpcmethod(func):
    """ Marks a method for `JSObject` classes to expose over RPC with
    JS widgets. ``func`` must be an instance method, and this must
    be declared in the initial definition of the class """
    func._mythril__isrpc = True

class childproperty(object):
    """ Acts like a ``property``, but gives the JS version of the `JSObject` a
    property by the same name, prefixed by "get_", and when HTML objects or
    other widgets have been assigned to this property on the Python side, the
    rendered JS wigdet can access the rendered object by that property.

    Objects assigned to this must either have an "id" property (as in `JSObject`s),
    or an "attrs" collection (tuple of ``(name, value)``, as in ``mythril.html.*``).

    Must be used on `JSObject`s. Takes no arguments. Must be defined in the 
    initial creation of the class. 
    """
    def __init__(self):
        self._prop = '_childproperty__' + str(id(self))
        self.name = '' # assigned by JSObject

    def __get__(self, inst):
        return getattr(inst, self._prop, None)

    def __set__(self, inst, value):
        id = getattr(value, 'id', None)
        if not id: # HTML node
            id = next((v for k, v in value.attrs if k == u'id'), None)
            if not id:
                id = (u'id', inst.id + u'__' + self.name)
                value.attrs.insert(0, id)
        
        inst._links[self.name] = id 
        return setattr(inst, self._prop, value)


_rpcIndex = {} # str -> instancemethod

class _JSObjectMeta(type):
    """ Enables the `JSObject` type to so stealthily set up RPC endpoints from
    methods and JS properties """
    def __init__(cls, name, bases, attrs):
        if 'js_class_name' not in attrs:
            cls.js_class_name = name
        for k, v in attrs.iteritems():
            pass

class JSObject(object):
    """
    """
    __metaclass__ = _JSObjectMeta
    js_namespace = 'window'

    def __init__(self, id):
        self.id = id
        self._links = {} # stores the ids of `childproperty` related objects

    def __html__(self, writer):
        writer.write(InlineScript(u'mythril.createWidget(%s.%s, %s, %s, %s
