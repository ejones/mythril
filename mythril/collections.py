import inspect
from operator import itemgetter

class TupleMeta( type ):
    """ Facilitates the creation of tuple classes that support
    accessing by name, complex constructors with defaults, etc. To use, just
    apply this as ``__metaclass__`` to a class deriving from ``tuple``. You must
    implement ``__new__`` which may have defaults but no varargs or kwargs. 
    Remember to call ``tuple.__new__( cls, (<Your>, <values>, <here>) )`` at the 
    end of that method. """
    def __new__( meta, name, bases, dct ):
        if not tuple in bases: 
            raise ValueError( ('TupleMeta used on type %s which does not '
                               'inherit from tuple') % name )

        meth_new = dct.get( '__new__' )
        if not meth_new:
            raise ValueError( ('TupleMeta used on type %s which does not '
                               'define __new__') % name )

        members = tuple( inspect.getargspec( meth_new ).args[ 1: ] )

        # actually add everything to the mix
        dct.setdefault( '__slots__', () )
        dct.setdefault( '__getnewargs__', lambda self: tuple( self ) )
        for i, memb in enumerate( members ): 
            dct.setdefault( memb, property( itemgetter( i ) ) )
        dct.setdefault( '__repr__', lambda self:
            name + '(' + ', '.join( '%s=%r' % (memb, getattr( self, memb ))
                                    for memb in members ) + ')' )

        return type.__new__( meta, name, bases, dct )
