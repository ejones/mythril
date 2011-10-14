import inspect
from operator import itemgetter

class TupleMeta( type ):
    """ Internal for use by ``customtuple`` """
    def __new__( meta, name, bases, dct ):
        dct = dict( dct )
        dct.setdefault( '__slots__', () )

        if not any( b.__name__ == 'customtuple' for b in bases ):
            # assume we are in a subclass etc.
            # TODO: validate?
            return type.__new__( meta, name, bases, dct )
            
        meth_new = dct.get( '__new__' )
        if not meth_new:
            raise ValueError( ('customtuple used with type %s which does not '
                               'define __new__') % name )

        members = tuple( inspect.getargspec( meth_new ).args[ 1: ] )
        for i, memb in enumerate( members ): 
            (lambda i: dct.setdefault( memb, 
                    property( lambda self: tuple.__getitem__( self, i ) )))( i )
        dct.setdefault( '__repr__', lambda self:
            name + '(' + ', '.join( '%s=%r' % (memb, getattr( self, memb ))
                                    for memb in members ) + ')' )

        return type.__new__( meta, name, bases, dct )

class customtuple( tuple ):
    """ Facilitates the creation of tuple classes that support accessing by
    name, complex constructors with defaults, etc. To use, inherit from this.
    You must implement ``__new__`` which may have defaults but no varargs or
    kwargs.  Remember to call 
    ``tuple.__new__( cls, (<Your>, <values>, <here>))`` at the end of that 
    method. """
    __metaclass__ = TupleMeta
    __slots__ = ()
    __getnewargs__ = lambda self: tuple( self )

def asmethod( cls, name=None ):
    """ Decorator that attaches the function as a method of ``cls``. Use ``name``
    to override the default, which uses the function's ``__name__``, to get the
    member name to use. Returns the function. """
    def dec( f ): 
        mname = name
        if not mname:
            try: mname = f.__name__
            except AttributeError as e:
                try: mname = f.__get__(0).__name__
                except AttributeError: raise e
        setattr( cls, mname, f )
        return f
    return dec
