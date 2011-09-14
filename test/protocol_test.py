
from collections import Iterable
from mythril.protocol import *
from nose.tools import *

class Foo (object):
    def __init__( self, name ): self.name = name
class Bar (Foo): pass
class Corge (Bar): pass

def test_protocol():
    """ test protocol: defaults; types; subtypes; ABCs; updates """
    @protocol
    def run( obj, arg ):
        return 'object: %s' % arg

    eq_( run( object(), 'foo' ) + '; ' + run( Corge( 'fas' ), 'a corge' ),
         'object: foo; object: a corge' ) 

    @run.of( Foo )
    def _( f, arg ):
        return 'Foo: %s (%s)' % (f.name, arg)

    eq_( '; '.join( (run( object(), 'foo' ),
                     run( Foo( 'Bob' ), 'garply' ),
                     run( Bar( 'Alice' ), 'quux' ),
                     run( Corge( 'Carole' ), 'plugh' )) ),
         'object: foo; Foo: Bob (garply); Foo: Alice (quux); '
         'Foo: Carole (plugh)' )

    @run.of( Bar )
    def _( b, arg ):
        return 'Bar: %s (%s)' % (b.name, arg)

    eq_( '; '.join( (run( object(), 'foo' ),
                     run( Foo( 'Bob' ), 'garply' ),
                     run( Bar( 'Alice' ), 'quux' ),
                     run( Corge( 'Carole' ), 'plugh' )) ),
         'object: foo; Foo: Bob (garply); Bar: Alice (quux); '
         'Bar: Carole (plugh)' )

    eq_( run( '', 'blah' ), 'object: blah' )

    @run.of( Iterable )
    def _( s, arg ):
        return 'iter: %s (%s)' % (repr( s ), arg)

    eq_( run( object(), 'blech' ) + '; ' + run( 'egah', 'qux' ),
         "object: blech; iter: 'egah' (qux)" )

