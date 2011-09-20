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

The `CssWriter` in this module is responsible for writing values to CSS. It is
recommended that you separately write your CSS into a static file (i.e, at app
startup), rather than regenerating it on every request. Nonetheless, anything
is doable.

``CssType.special`` is a dict that contains the definitions for, and allows you
to extend, special property names like "pos", "size". See `CssType`.
"""
import Image
from cStringIO import StringIO
from functools import partial
from itertools import izip
from numbers import Number
from uuid import uuid4

import mythril.html
from mythril.html import Element, Attribute
from mythril.protocol import protocol
from mythril.util import customtuple

default_encoding = mythril.html.default_encoding

class CssType( customtuple ):
    """ Represents the type of `css` and its derived (constructed) values.

    Use ``CssType.special`` to add new special properties. By default, a number
    of such properties, like "size", "pos", and "background-gradient" exist
    which expand to multiple declarations (for example, the aforementioned
    expand to "width" and "height", "left" or "right" and "top" or "bottom" and
    "position", and multiple "background-image" declarations). To add a new
    one, add a function which takes the "arguments" (which is the tuple
    assigned to the property in the css declaration), and returns a sequence of
    ``(property_name, property_value)``, to the ``special`` dict. It must be
    added by CSS-name (i.e., "background-gradient", not "background_gradient").

    Some special properties statically generating images, eg. gradients
    and corners for speed and for downlevel browsers. The host application
    should configure ``CssWriter.imageUrlPath`` and ``CssWriter.imageFilePath``
    if it plans to use them. Data URIs are used where the size is small.
    For IE6/7 images are used all the time.
    """
    # TODO: document all the built-in special properties

    def __new__( cls, selector, attrs, children ):
        return tuple.__new__( cls, selector, attrs, children) )

    def __repr__( self ):
        return ('css(' + repr( self.selector ) +
            ', '.join( repr( tuple( a ) ) for a in self.attrs ) + ')' +
            (('[' + ', '.join( imap( repr, self.children ) ) + ']')
                    if self.children else ''))

    def __call__( self, selector, *attr_pairs, **attrs ):
        """ 
        css( selector, (attr_name, attr_value), ..., attr_name=attr_value, ... )

        The selector must be a string, a thing with a ``__name__`` (ie., 
        function or class) or a tuple, or a tuple of any of these (including
        tuples, recursively).
        """
        return type( self )( 
            selector=Element.cssid( selector ),
            attrs=tuple( CssType.run_specials( 
                            Attribute.from_args( attr_pairs, attrs ))),
            children=self.children )

    def __getitem__( self, arg ):
        """
        css[ child1, ... childN ]
        """
        if not isinstance( arg, tuple ): arg = (arg,)
        return type( self )( self.selector, self.attrs, arg )

    special = {}

    @staticmethod
    def run_specials( attrs ):
        """ Internal utility for correcting special attribute names """
        for a in attrs:
            if a.name in CssType.special:
                args = a.value if isinstance( a.value, tuple ) else (a.value,)
                for name, value in CssType.special[ a.name ]( *args ):
                    yield Attribute( name, value )
            else: yield a

    @staticmethod
    def color( r, g, b, a=None ):
        """ Mostly internal helper method for formatting color channel values
        into strings """
        if a: return u'rgba(%s,%s,%s,%s)' % (r, g, b, a)
        else: return u'rgb(%s,%s,%s)' % (r, g, b)

    imageUrlPath = u'/data-images'
    imageFilePath = u'data/images'

css = CssType()

@partial( special.__setitem__, 'pos' )
def _( x, y, rel='' ):
    return (
        (u'position', u'relative' if 'relative' in rel 
                      else u'fixed' if 'fixed' in rel 
                      else u'absolute'),
        (u'right' if 'right' in rel else u'left', x),
        (u'bottom' if 'bottom' in rel else u'top', y))

@partial( special.__setitem__, 'size' )
def _( w, h ): return ( (u'width', w), (u'height', h) )

@partial( special.__setitem__, 'border-radius' )
def _( radius, desc=None ):
    if not desc:
        yield (u'border-radius', radius)
        yield (u'-webkit-border-radius', radius)
        yield (u'-moz-border-radius', radius)
        return
    for y in (u'top', u'bottom'):
        for x in (u'left', u'right'):
            if desc == x or desc == y or desc == y + u' ' + x:
                yield (u'border-' + y + u'-' + x + u'-radius', radius)
                yield (u'-webkit-border-' + y + u'-' + x + u'-radius', radius)
                yield (u'-moz-border-radius-' + y + x, radius)

@partial( special.__setitem__, 'box-shadow' )
def _( x, y, blur, spread, color, inset='' ):
    return ((u'box-shadow', (x, y, blur, spread, color, inset)),
            (u'-webkit-box-shadow', (x, y, blur, spread, color, inset)))
            (u'-moz-box-shadow', (x, y, blur, spread, color, inset)))
    # NB: we don't do DXImageTransform effects like Shadow and DropShadow
    #   because they fuck with the rendering of the rest of the element

# TODO: support multiple color stops
@partial( special.__setitem__, 'background-gradient' )
def _( frm, to, angle=None ):

    origin = u'top' if not angle else angle
    bgcolor = tuple( (a + b) // 2 for a, b in izip( frm, to ) )
    cfrom, cto = CssType.color( *frm ), CssType.color( *to )
    args = u'(' + origin + u',' + cfrom + u',' + cto + u')'

    yield (u'background-color', bgcolor)
    # TODO: angle for old webkit-gradient syntax
    yield (u'background-image', 
           u'-webkit-gradient(linear, left top, left bottom, from(' +
                cfrom + u'), to(' + cto + u'))')
    for prov in (u'-webkit-', u'-moz-', u'-o-', u'-ms-', u''):
        yield (u'background-image', prov + u'linear-gradient' + args)

# TODO: horizontal
@partial( special.__setitem__, 'static-background-gradient' )
def _( frm, to, height ):
    cpairs = zip( frm, to )
    im = Image.new( 'RGBA' if len( frm ) > 3 else 'RGB', (1, height) )
    im.putdata( list( tuple( a + (b - a) * i // height for a, b in cpairs )
                      for i in xrange( height ) ))
    sio = StringIO(); im.save( sio, 'PNG' )
    data = sio.getvalue()
    
    fname = u'/_%x.png' % uuid4().fields[5]
    with open( CssType.imageFilePath + fname, 'wb' ) as f: f.write( data )
    
    return ((u'background', u'url(data:image/png;base64,' +
                unicode( data.encode( 'base64' ), 'ascii' ) + u') 0 0 repeat-x'),
            (u'*background', u'url(' + 
                CssType.imageUrlPath + fname + u') 0 0 repeat-x'))


class CssWriter( object ):
    """ Writes arbitrary Python values to CSS. ``CssWriter.write_of`` allows
    for the extension of this facility to new types. ``CssWriter.to_bytes`` is
    a convenience for getting a byte string out of a (complex) value in one go
    
    Before being written, all ``unicode`` instances are encoded using 
    its ``encoding`` attribute. 

    Note: at the moment, input strings are not "validated" because data-driven
    CSS is pretty rare. If you plan on using user-submitted css rules/property
    values, be sure to validate them ... somehow.
    """
    _protocol = protocol( lambda obj, self: self.write( repr( obj ) ) )

    def __init__( self, file, encoding=None ):
        self.encoding = encoding or default_encoding
        self.file = file
        self.stack = []

    def write( self, value ):
        """ Translates the arbitrary Python ``value`` into CSS. This behaviour
        can be extended with ``CssWriter.writer_of`` """
        self.stack.append( value )
        self._protocol( value, self )
        self.stack.pop()
        return self

    @classmethod
    def write_of( cls, typ ):
        """ Decorator that registers a function as the handler for when objects
        of type ``typ`` are passed to ``write``. The decorated function must
        take the `CssWriter` as its first argument and the value as the second.
        """
        return (lambda func: 
            cls._protocol.of( typ )( lambda val, self: func( self, val ) ))

    @classmethod
    def to_bytes( cls, value, encoding=None ):
        encoding = encoding or default_encoding
        s = StringIO(); cls( s, encoding ).write( value )
        return s.getvalue()

    @staticmethod
    def compute_selector( stack ):
        """ Mostly a utility for the other definitions in this module. Takes
        a stack of values with a ``selector`` property (eg., ``CssType`` instances),
        goes up the stack and returns the linearized CSS-compatible selector 
        representation.

        Selectors are understood to be comprised of only 
        """


@CssWriter.write_of( str )
def _( wr, s ): wr.file.write( s )

@CssWriter.write_of( unicode )
def _( wr, s ): wr.file.write( s.encode( wr.encoding, 'strict' ) )

@CssWriter.write_of( Number )
def _( wr, num ): wr.file.write( (unicode( num ) + u'px').encode( wr.encoding ) )

@CssWriter.write_of( tuple )
def _( wr, nums ): wr.file.write( 
    

@CssWriter.write_of( CssType )

