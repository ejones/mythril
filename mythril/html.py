"""
Python values representing HTML elements. These allow for the creation of HTML
documents and fragments in Python. The standard HTML tags, such as "p" and
"div" are represented as a "builder" instance, like ``mythril.html.div``
and as a specific type, like ``mythril.html.DivType`` that represents 
elements of that tag. 

The function ``mythril.html.html_write`` actually serializes anything into 
HTML, including primitive values, and can be extended to turn other types into
HTML. Just define a function decorated with 
``@mythril.html.html.of( <Your Type> )``. Because of this, there is no
"html" tag in this module. The "doc" tag handles adding the doctype *and*
the "html" wrapper tag.
"""

from types import NoneType
from functools import partial
from itertools import chain, starmap
from collections import namedtuple, Callable, Iterable
from numbers import Number
from cgi import escape as html_escape
from cStringIO import StringIO

from mythril.protocol import protocol

Attribute = namedtuple( 'Attribute', 'name,value' )

Element = namedtuple( 'Element', 'attrs,children' )
Element.name = ''
Element.empty = False

@partial( setattr, Element, '__call__' )
def __call__( self, *attr_pairs, **attrs ):
    """ 
    Element( (attr_name, attr_value), ..., attr_name=attr_value, ...) ->
    Element( css_class, (attr_name, attr_value), ..., attr_name=attr_value, ...) ->
    """
    def correct_attr( name ):
        if name.endswith( '_' ): name = name[ :-1 ]
        name = name.replace( '__', ':' ).replace( '_', '-' )
        return name
    
    if len( attr_pairs ) > 0 and isinstance( attr_pairs[ 0 ], basestring ):
        attr_pairs = ((u'class', attr_pairs[ 0 ]),) + attr_pairs[ 1: ]

    return type( self )( 
        tuple( chain( starmap( Attribute, attr_pairs ),
                      (Attribute( correct_attr( name ), value )
                       for name, value in attrs.iteritems()) ) ),
        self.children )
                         
@partial( setattr, Element, '__getitem__' )
def __getitem__( self, arg ):
    """
    Element[ child1, child2, ... childN ]
    """
    if not isinstance( arg, tuple ): arg = (arg,)
    return type( self )( self.attrs, arg )

@partial( setattr, Element, 'register' )
@classmethod
def register( cls, name, empty=False ):
    """
    Registers the given name as an html tag. A subtype of the current type 
    (e.g., `Element`) is added to its module as well as a root instance that 
    must be used to construct the tags of that type. If ``name`` is "article",
    for instance, a subtype named "ArticleType", and a builder instance named
    "article", would be added to the current type's module (e.g., `mythril.html`)
    """
    mod = cls.__module__
    etype_name = name.title() + 'Type'
    etype = type( cls )( etype_name, (cls,), { 
                            'name': name, 'empty': empty } )
    setattr( mod, etype_name, etype )
    setattr( mod, name, etype( (), () ) )

map( Element.register, u'''
    a abbr acronym address applet b bdo big blockquote body button
    caption center cite code colgroup dd dfn div dl dt doc html em fieldset
    font form frameset h1 h2 h3 h4 h5 h6 head i iframe ins kbd label
    legend li menu noframes noscript ol optgroup option pre q s samp
    select small span strike strong style sub sup table tbody td
    textarea tfoot th thead title tr tt u ul var script frame p'''.split() )

map( lambda name: Element.register( name, True ),
     u"area base br col hr img input link meta param".split() )

# safe_bytes and safe_unicode borrowed from Travis Rudd's "markup.py"
class safe_bytes(str):
    def decode(self, *args, **kws):
        return safe_unicode(super(safe_bytes, self).encode(*args, **kws))

    def __add__(self, o):
        res = super(safe_bytes, self).__add__(o)
        if isinstance(o, safe_unicode):
            return safe_unicode(res)
        elif isinstance(o, safe_bytes):
            return safe_bytes(res)
        else:
            return res

class safe_unicode(unicode):
    def encode(self, *args, **kws):
        return safe_bytes(super(safe_unicode, self).encode(*args, **kws))

    def __add__(self, o):
        res = super(safe_unicode, self).__add__(o)
        return (safe_unicode(res)
                if isinstance(o, (safe_unicode, safe_bytes)) else res)
                
@protocol
def html_write( obj, out, in_encoding ):
    """ ``protocol`` that writes the html representation of ``obj`` to
    the the file-like (writable) object ``out``. Any ``str``s are 
    decoded according to ``in_encoding`` """
    # default handler
    html_write( repr( obj ), out, in_encoding )

def html_string( value, in_encoding )
    """ Convenience """
    s = StringIO(); html_write( value, s, in_encoding )
    return s.getvalue()

@html_write.of( str )
def _( s, out, in_enc ):
    out.write( html_escape( unicode( s, in_enc, 'strict' ), True ) )

@html_write.of( unicode )
def _( s, out, in_enc ): out.write( html_escape( s, True ) )

@html_write.of( safe_bytes )
def _( s, out, in_enc ): out.write( unicode( s, in_enc, 'strict' ) )

@html_write.of( safe_unicode )
def _( s, out, in_enc ): out.write( s )

@html_write.of( NoneType )
def _( n, out, in_enc ): pass

@html_write.of( bool )
def _( b, out, in_enc ): out.write( unicode( b ) )

@html_write.of( Number )
def _( num, out, in_enc ): out.write( unicode( num ) )

@html_write.of( Callable )
def _( f, out, in_enc ): html_write( f(), out, in_enc )

@html_write.of( Iterable )
def _( seq, out, in_enc ):
    for x in seq: html_write( x, out, in_enc )

@html_write.of( Attribute )
def _( attr, out, in_enc ):
    html_write( (u' ', attr.name, u'="', attr.value, u'"'), out, in_enc )

@html_write.of( Element )
def _( elem, out, in_enc ):
    out.write( u'<' + elem.name )
    for a in elem.attrs: html_write( a, out, in_enc )
    out.write( u'>' )
    if not elem.empty:
        for c in elem.children: html_write( c, out, in_enc )
        out.write( u'</' + elem.name + u'>' )

