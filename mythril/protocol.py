from itertools import islice, chain
from types import InstanceType
from operator import add
from collections import defaultdict

nomatch = object() # sentinel for collections

def dispatch( dtable, typ, default=None ):
    """ Takes a dict of { type: value } and a type, and returns
    the most appropriate value, considering base classes and ABCs. 
    If this is used often you should cache the results. """
    if typ is not InstanceType:
        for base in typ.mro()[ :-1 ]: # last is always ``object``
            if base in dtable: return dtable[ base ]

    # of the keys (types) which are superclasses of this type,
    #  which is the first one that none of the rest are subclasses of it.
    abases = [ b for b in dtable.iterkeys() 
               if b is not object and issubclass( typ, b ) ]
    ret = next( (dtable[ b ] for i, b in enumerate( abases ) if not any(
                     issubclass( sb, b ) for sb in islice( abases, i + 1, None ))),
                nomatch )
    if ret is not nomatch: return ret

    if object in dtable: return dtable[ object ]
    else: return default

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
        self.dtable = defaultdict( list )
        self.cache = None
        self.of( object )( func )

    def of( self, typ ):
        def dec( func ):
            self.dtable[ typ ].append( func )
            self.cache = None
        return dec

    def __call__( self, value, *args, **kwargs ):
        typ = type( value )

        if self.cache is None: self.cache = {}
        funs = self.cache.get( typ )

        if funs is None:
            # each type has zero or more associated handlers, but
            # need all the handlers for all the (abstract and concrete) base
            # types for typ (and itself and object)
            funs = self.cache[ typ ] = \
                reduce( add, (v for b, v in self.dtable.iteritems()
                              if issubclass( typ, b )), [] )

        for fun in funs: fun( value, *args, **kwargs )
