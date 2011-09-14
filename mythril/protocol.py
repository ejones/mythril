from functools import partial
from itertools import islice, count
from types import InstanceType

_nomatch = object()

class DispatchTable( object ):
    """ Stores values (typically Callables) associated with types. On lookup,
    it knows how to associate sub-classes with super-classes, values with
    abstract types, etc.
    Essentially an internal class, but could be leveraged elsewhere for
    fast subtype lookup """
    # TODO: cDispatchTable? After all, monkey C, monkey C++
    # TODO: Maintain insertion order: to concretely handle possible abstract
    #           class contentions
    def __init__( self ):
        self._table = {}

    __cache = None
    @property
    def _cache( self ):
        if self.__cache is None: self.__cache = {}
        return self.__cache
    
    def __setitem__( self, key, value ): 
        self.__cache = None
        self._table[ key ] = value

    def get( self, key, default=None ):
        ret = self._table.get( key, _nomatch )
        if ret is _nomatch: ret = self._cache.get( key, _nomatch )
        
        if ret is not _nomatch: return ret

        if key is not InstanceType:
            for base in key.mro()[ :-1 ]: # clip ``object`` because that's
                                          #  silly at this stage
                ret = self._table.get( base, _nomatch )
                if ret is not _nomatch: break

        if ret is _nomatch:
            abases = [ b for b in self._table.iterkeys() if issubclass( key, b ) ]
            ret = next( (self._table[ b ] for i, b in enumerate( abases )
                         if not any( issubclass( bsub, b ) 
                                     for bsub in islice( abases, i + 1, None ))),
                        _nomatch )

        if ret is _nomatch: ret = self._table.get( object, _nomatch )

        if ret is not _nomatch: self._cache[ key ] = ret; return ret
        return default

    def __getitem__( self, key ):
        ret = self.get( key, _nomatch )
        if ret is _nomatch: raise KeyError( key )
        return ret

class protocol( object ):
    """ Turns a function into a Callable whose behaviour can be customised
    by type. That is, when it is called, it looks up a specific definition
    based on the type of the *first* argument. 
    The original (decorated) function becomes
    the "specialization" for ``object``, that is, the default version. """
    # TODO: doctest exaples
    # TODO: repr/str based on func.__name__
    def __init__( self, func ): 
        self.dtable = DispatchTable()
        self.of( object )( func )

    def of( self, typ ):
        """ Decorator that sets up the function as the specialization of this
        protocol for values of type typ """
        def dec( func ): self.dtable[ typ ] = func
        return dec

    def __call__( self, value, *args, **kwargs ):
        target = self.dtable.get( type( value ) )
        if not target: raise ValueError( "'%s' has no handler" % type( value ) )
        return target( value, *args, **kwargs )

class multicast_protocol( object ):
    """ Like a `protocol`, but in this case, multiple functions can be registered
    for the same type and they will all be called when matched. Sort of like an
    event, or publisher, in other patterns/langauges, but with specialization
    on the originating value """
    def __init__( self, func ):
        self.dtable = DispatchTable()
        self.of( object )( func )

    def of( self, typ ):
        def dec( func ):
            listeners = self.dtable.get( typ )
            if listeners is None: listeners = self.dtable[ typ ] = [] 
            listeners.append( func )
        return dec

    def __call__( self, value, *args, **kwargs ):
        listeners = self._dtable.get( type( value ), _nomatch )
        if listeners is None:
            raise ValueError( "'%s' has no handlers" % type( value ) )
        for func in listeners: func( value, *args, **kwargs )
