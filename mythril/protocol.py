from functools import partial
from itertools import islice, count, chain, imap
from types import InstanceType
from operator import itemgetter

nomatch = object() # sentinel for collections

def dispatch_values( dtable, typ ):
    """ Takes a dict of { type: value } and a type, and returns a
    sequence of (type, value) for all the matching (sub)types & values in the
    dict """
    if typ is not InstanceType: 
        for base in typ.mro()[ :-1 ]: # -1 is object
             if base in dtable: yield base, dtable[ base ]
    elif typ in dtable: yield typ, dtable[ typ ]

    for abase in dtable.iterkeys(): 
        if issubclass( typ, abase ) and not typ == abase: 
            yield abase, dtable[ abase ]
          
    if object in dtable: yield object, dtable[ object ]

def dispatch( dtable, typ, default=None ):
    """ Takes a dict of { type: value } and a type, and returns
    the most appropriate value, considering base classes and ABCs. 
    If this is used often you should cache the results. """
    types_x_vals = list( dispatch_values( dtable, typ ) )
    for i, (typ, val) in enumerate( types_x_vals ):
        for bsub, _subval in islice( types_x_vals, i + 1, None ):
            if issubclass( bsub, typ ): break
        else: return val
    return default

class protocol( object ):
    """ Turns a function into a Callable whose behaviour can be customised
    by type. That is, when it is called, it looks up a specific definition
    based on the type of the *first* argument. 
    The original (decorated) function becomes
    the "specialization" for ``object``, that is, the default version. """
    # TODO: doctest exaples
    # TODO: repr/str based on func.__name__
    def __init__( self, func ): 
        self.dtable = {}
        self.cache = None
        self.of( object )( func )

    def of( self, typ ):
        """ Decorator that sets up the function as the specialization of this
        protocol for values of type typ """
        def dec( func ): 
            self.dtable[ typ ] = func
            self.cache = None
        return dec

    def __call__( self, value, *args, **kwargs ):
        typ = type( value )

        if self.cache is None: self.cache = self.dtable.copy()
        target = self.cache.get( typ )

        if not target: target = self.cache[ typ ] = dispatch( self.dtable, typ )

        if not target: raise ValueError( "'%s' has no handler" % typ )
        return target( value, *args, **kwargs )

class multicast_protocol( object ):
    """ Like a `protocol`, but in this case, multiple functions can be registered
    for the same type and they will all be called when matched. Sort of like an
    event, or publisher, in other patterns/langauges, but with specialization
    on the originating value """
    def __init__( self, func ):
        self.dtable = DispatchTable()
        self.cache = None
        self.of( object )( func )

    def of( self, typ ):
        def dec( func ):
            listeners = self.dtable.get( typ )
            if listeners is None: listeners = self.dtable[ typ ] = [] 
            listeners.append( func )
            self.cache = None
        return dec

    def __call__( self, value, *args, **kwargs ):
        typ = type( value )

        if self.cache is None: self.cache = {}
        funs = self.cache.get( typ )

        if funs is None:
            funs = self.cache[ typ ] = \
                list( f for _t, fs in dispatch_values( self.dtable, typ )
                        for f in fs )

        for fun in funs: fun( value, *args, **kwargs )
