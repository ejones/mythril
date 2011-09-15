
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

def test_multicast_protocol():
    results = defaultdict( int )
    
    @multicast_protocol
    def run( obj, arg ):
        print obj
        results[ (object, 'default', arg) ] += 1

    @run.of( object )
    def _( obj, arg ):
        results[ (object, 'obj2', arg) ] += 1

    results.clear()
    run( object(), 42 ); run( Corge( 'derp' ), 42 )
    eq_( results, { (object, 'default', 42): 2, (object, 'obj2', 42): 2 } )

    @run.of( Foo )
    def _( f, arg ):
        results[ (Foo, f.name, arg) ] += 1

    results.clear()
    run( object(), 42 )
    run( Foo( 'Bob' ), 'garply' )
    run( Bar( 'Bob' ), 'garply' )
    run( Corge( 'Carole' ), 'plugh' )
    eq_( results, { (object, 'default', 42): 1,
                    (object, 'obj2', 42): 1,
                    (object, 'default', 'garply'): 2,
                    (object, 'obj2', 'garply'): 2,
                    (object, 'default', 'plugh'): 1,
                    (object, 'obj2', 'plugh'): 1,
                    (Foo, 'Bob', 'garply'): 2,
                    (Foo, 'Carole', 'plugh'): 1 } )

    @run.of( Bar )
    def _( f, arg ):
        results[ (Bar, f.name, arg) ] += 1

    results.clear()
    run( object(), 42 )
    run( Foo( 'Bob' ), 'garply' )
    run( Bar( 'Bob' ), 'garply' )
    run( Corge( 'Carole' ), 'plugh' )
    eq_( results, { (object, 'default', 42): 1,
                    (object, 'obj2', 42): 1,
                    (object, 'default', 'garply'): 2,
                    (object, 'obj2', 'garply'): 2,
                    (object, 'default', 'plugh'): 1,
                    (object, 'obj2', 'plugh'): 1,
                    (Foo, 'Bob', 'garply'): 2,
                    (Bar, 'Bob', 'garply'): 1,
                    (Foo, 'Carole', 'plugh'): 1,
                    (Bar, 'Carole', 'plugh'): 1 } )

    @run.of( Iterable )
    def _( seq, arg ):
        results[ (Iterable, str( seq ), arg) ] += 1

    results.clear()
    run( object(), 'test' )
    run( 'foo', 'bar' )
    eq_( results, { (object, 'default', 'test'): 1,
                    (object, 'obj2', 'test'): 1,
                    (object, 'default', 'bar'): 1,
                    (object, 'obj2', 'bar'): 1,
                    (Iterable, 'foo', 'bar'): 1 } )
