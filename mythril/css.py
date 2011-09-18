"""
Python values representing CSS rules, allowing you to create (nestable) 
CSS rules in Python. Here is an example::

    from mythril.css import css
    css( MyClass, border='1px solid #CCC', padding=5, size=( 200, 50 ) )[
        css( ('some-class', SomeUtility), pos=( 1, 0, 'relative' ) ) ]

Corresponds to something equivalent to::

    my-class { border: 1px solid #CCC; padding: 5px; width: 200px; height: 50px; }
    my-class some-class, my-class some-utility { 
         position: relative; top: 1px; left: 0px; }

Use the ``css_write`` function in this module to write the css. It's just an
instance of ``mythril.protocol.protocol``, so you can register any Python value
to be converted to css as well. Just decorate a function with
``mythril.css.css_write.of( <Your Type> )`` and implement the correct iface.
"""

from mythril.html import Element, Attribute

class CSSType( tuple ):
    __slots__ = ()
    selector = property( lambda self: tuple.__getitem__( self, 0 ) )
    attrs = property( lambda self: tuple.__getitem__( self, 1 ) )
    children = property( lambda self: tuple.__getitem__( self, 2 ) )

    def __new__( cls, selector, attrs, children ):
        return tuple.__new__( cls, selector, attrs, children) )

    def __getnewargs__( self ): return tuple( self )

    def __repr__( self ):
        return ('css(' + repr( self.selector ) +
            ', '.join( repr( tuple( a ) ) for a in self.attrs ) + ')' +
            (('[' + ', '.join( imap( repr, self.children ) ) + ']')
                    if self.children else ''))

    def __call__( self, selector, *attr_pairs, **attrs ):
        return type( self )( selector, Attribute
