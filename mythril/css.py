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

The functions `dumps` and `dump` in this module are responsible for
writing values to CSS. It is recommended that you separately write your CSS
into a static file (i.e, at app startup), rather than regenerating it on every
request.  Nonetheless, anything is doable.

`special` is a dict that contains the definitions for, and allows you to
extend, special property names like "pos", "size". See `CssType` for
documentation.
"""
import Image
from cStringIO import StringIO
from functools import partial
from itertools import izip, imap
from numbers import Number
from uuid import uuid4
from operator import add
import os

import mythril.html
from mythril.html import Element, Attribute as HtmlAttribute, cssid
from mythril.protocol import protocol
from mythril.util import customtuple

default_encoding = mythril.html.default_encoding

# used by special and CssType
resource_url_path = u'/cssres'
resource_file_path = os.path.join( u'data', u'cssres' )

class CssWriter( object ):
    """ Writes arbitrary Python values to CSS. For advanced use. See
    `dumps` or `dump` in this module for a simple way of converting to
    the CSS byte representation. Any arbitrary Python type can support/extend
    conversion to CSS by implementing a ``__css__`` method that takes the
    `CssWriter` instance as a sole argument.
    
    Before being written, all ``unicode`` instances are encoded using 
    its ``encoding`` attribute. 

    Note: at the moment, input strings are not "validated" because data-driven
    CSS is pretty rare. If you plan on using user-submitted css rules/property
    values, be sure to validate them ... somehow.
    """
    def __init__( self, file, encoding=None ):
        self.encoding = encoding or default_encoding
        self.file = file
        self.stack = []
        self.selector = ('',)

    def write( self, value ):
        """ Translates the arbitrary Python ``value`` into CSS. """
        self.stack.append( value )

        oldselector = self.selector
        if hasattr( value, 'selector' ):
            childsel = value.selector if isinstance( value.selector, tuple ) \
                       else (value.selector,)
            self.selector = tuple( a + u' ' + b for a in self.selector
                                                for b in childsel)

        if hasattr( value, '__css__' ): value.__css__( self )

        elif isinstance( value, basestring ):
            self.file.write( value if isinstance( value, str ) else
                             value.encode( self.encoding, 'strict' ) )

        elif isinstance( value, Number ):
            self.file.write( (unicode( value ) + u'px').encode( self.encoding ) )

        elif isinstance( value, Iterable ):
            for item in value: self.write( item )

        elif isinstance( value, Callable ): self.write( value() )

        else: self.write( unicode( value ).encode( self.encoding, 'strict' ) )

        self.selector = oldselector
        self.stack.pop()
        return self

def dump( value, file, encoding=None ):
    """ Writes the CSS byte representation of ``value`` to ``file``.

    Before being written, all ``unicode`` instances are encoded using 
    its ``encoding`` attribute. 

    Note: at the moment, input strings are not "validated" because data-driven
    CSS is pretty rare. If you plan on using user-submitted css rules/property
    values, be sure to validate them ... somehow.
    """
    CssWriter( file, encoding or default_encoding ).write( value )

def dumps( value, encoding=None ):
    """ Returns the CSS byte representation of ``value``. See `dump` for
    details. """
    encoding = encoding or default_encoding
    s = StringIO(); CssWriter( s, encoding ).write( value )
    return s.getvalue()
    
class Attribute( HtmlAttribute ):
    __slots__ = ()
    def __css__( self, writer ):
        writer.write( (self.name, u':') )

        if isinstance( self.value, tuple ):
            for i, item in enumerate( self.value ): 
                if i > 0: writer.write( u' ' )
                writer.write( item )
        else:
            writer.write( self.value )

class CssType( customtuple ):
    """ Represents the type of `css` and its derived (constructed) values.

    Use `special` in this module to add new special properties. By default, a number
    of such properties, like "size", "pos", and "background_gradient" exist
    which expand to multiple declarations (for example, the aforementioned
    expand to "width" and "height", "left" or "right" and "top" or "bottom" and
    "position", and multiple "background-image" declarations). To add a new
    one, add a function which takes the "arguments" (which is the tuple
    assigned to the property in the css declaration), and returns a sequence of
    ``(property_name, property_value)``, to the ``special`` dict. It must be
    added by CSS-name (i.e., "background-gradient", not "background_gradient").

    Some special properties statically generating images, eg. gradients and
    corners for speed and for downlevel browsers. The host application should
    configure ``resource_url_path`` and ``resource_file_path``
    if it plans to use them. Data URIs are used where the size is small.  For
    IE6/7, these properties always use images.
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
            selector=cssid( selector ),
            attrs=tuple( CssType.run_specials( 
                            Attribute.from_args( attr_pairs, attrs ))),
            children=self.children )

    def __getitem__( self, arg ):
        """
        css[ child1, ... childN ]
        """
        if not isinstance( arg, tuple ): arg = (arg,)
        return type( self )( self.selector, self.attrs, arg )

    def __css__( self, writer ):
        writer.write( (writer.selector, u'{') )
        for i, attr in enumerate( self.attrs ):
            if i > 0: writer.write( u',' )
            writer.write( attr )
        writer.write( u'}' )

        for child in self.children:
            writer.write( child )

css = CssType()

class _CssSpecials( dict ):
    
    def register( name=None ):
        """ Decorator. Registers the function as a "special" css property by
        the name of the function or ``name`` if it is given. Whenever this
        property is used in ``css`` values, the tuple or single value it is
        given is passed to the function as argument(s), and the returned
        key/value pair(s) are used as the real (expanded) attributes.

        Note: remember that ``css`` attribute names undergo "cssification", so the
        name given here is 'background_gradient', it will still be activated
        if an attribute called "background-gradient" is given. """
        def dec( f ): self[ name or cssid( f ) ] = f; return f

        # in case this is called without a name and without parens
        if name and not isinstance( name, basestring ): return dec( name )
        return dec
    
    def run( attrs ):
        """ Internal utility for expanding special attribute names """
        for a in attrs:
            if a.name in self:
                args = a.value if isinstance( a.value, tuple ) else (a.value,)
                for name, value in self[ a.name ]( *args ):
                    yield Attribute( name, value )
            else: yield a

special = _CssSpecials()

def color( r, g, b, a=None ):
    """ Mostly internal helper method for formatting color channel values
    into strings """
    if a: return u'rgba(%s,%s,%s,%s)' % (r, g, b, a)
    else: return u'rgb(%s,%s,%s)' % (r, g, b)

@special.register
def pos( x, y, rel='' ):
    return (
        (u'position', u'relative' if 'relative' in rel 
                      else u'fixed' if 'fixed' in rel 
                      else u'absolute'),
        (u'right' if 'right' in rel else u'left', x),
        (u'bottom' if 'bottom' in rel else u'top', y))

@special.register
def size( w, h ): return ( (u'width', w), (u'height', h) )

@special.register
def border_radius( radius, desc=None ):
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

@special.register
def box_shadow( x, y, blur, spread, color, inset='' ):
    return ((u'box-shadow', (x, y, blur, spread, color, inset)),
            (u'-webkit-box-shadow', (x, y, blur, spread, color, inset)))
            (u'-moz-box-shadow', (x, y, blur, spread, color, inset)))
    # NB: we don't do DXImageTransform effects like Shadow and DropShadow
    #   because they fuck with the rendering of the rest of the element

# TODO: support multiple color stops
@special.register
def background_gradient( frm, to, angle=None ):

    origin = u'top' if not angle else angle
    bgcolor = tuple( (a + b) // 2 for a, b in izip( frm, to ) )
    cfrom, cto = color( *frm ), color( *to )
    args = u'(' + origin + u',' + cfrom + u',' + cto + u')'

    yield (u'background-color', bgcolor)
    # TODO: angle for old webkit-gradient syntax
    yield (u'background-image', 
           u'-webkit-gradient(linear, left top, left bottom, from(' +
                cfrom + u'), to(' + cto + u'))')
    for prov in (u'-webkit-', u'-moz-', u'-o-', u'-ms-', u''):
        yield (u'background-image', prov + u'linear-gradient' + args)

# TODO: horizontal?
@special.register
def static_background_gradient( frm, to, height ):
    cpairs = zip( frm, to )
    im = Image.new( 'RGBA' if len( frm ) > 3 else 'RGB', (1, height) )
    im.putdata( list( tuple( a + (b - a) * i // (height - 1) for a, b in cpairs )
                      for i in xrange( height ) ))
    sio = StringIO(); im.save( sio, 'PNG' )
    data = sio.getvalue()
    
    fname = u'_%x.png' % uuid4().fields[5]
    with open( os.path.join( resource_file_name, fname ), 'wb' ) as f: f.write( data )
    
    return ((u'background', u'url(data:image/png;base64,' +
                data.encode( 'base64' ) + u') 0 0 repeat-x'),
            (u'*background', u'url(' + 
                resource_url_path + u'/' + fname + u') 0 0 repeat-x'))

