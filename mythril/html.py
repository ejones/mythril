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
import sys
from types import NoneType
from functools import partial
from itertools import chain, starmap
from collections import namedtuple, Callable, Iterable
from numbers import Number
from cgi import escape as html_escape
from cStringIO import StringIO

from mythril.protocol import protocol

default_encoding = 'UTF-8'
default_lang = 'en'

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

    Please give the name in ``unicode``.
    """
    mod = sys.modules[ cls.__module__ ]
    etype_name = name.title() + 'Type'
    etype = type( cls )( (etype_name if isinstance( etype_name, str )
                          else etype_name.encode( 'ascii' )),
                          (cls,), { 'name': name, 'empty': empty } )
    setattr( mod, etype_name, etype )
    setattr( mod, name, etype( attrs=(), children=() ) )

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
                
class Page( tuple ):
    """ Useful wrapper for the usual features of a full HTML document """
    __slots__ = ()
    def __new__( cls, title, content, encoding=None, lang=None ):
        encoding = encoding or default_encoding
        lang = lang or default_lang
        return tuple.__new__( cls, (title, content, encoding, lang) )
        
    def __getnewargs__( self ): return tuple( self )
    def __repr__( self ):
        return 'Page(title=%r, content=%r, encoding=%r, lang=%r)' % self
    def __str__( self ): return repr( self )
        

@protocol
def html_write( obj, out, encoding ):
    """ ``protocol`` that writes the html representation of ``obj`` to
    the the file-like (writable) object ``out``. Any ``str``s that need to
    be HTML-escaped are decoded according to ``encoding``. Only bytes are 
    written to the output file (as ``str``s encoded by ``encoding``).

    If you expect to have ``str``s in your app encoded to a different
    encoding than the one you are using here, remember to unicode them
    in advance """
    # default handler
    html_write( repr( obj ), out, encoding )

def html_bytes( value, encoding=None ):
    """ Convenience """
    encoding = encoding or default_encoding
    s = StringIO(); html_write( value, s, encoding )
    return s.getvalue()

@html_write.of( str )
def _( s, out, enc ):
    out.write( html_escape( unicode( s, enc, 'strict' ), True )
                    .encode( enc, 'strict' ) )

@html_write.of( unicode )
def _( s, out, enc ): out.write( html_escape( s, True ).encode( enc, 'strict' ) )

@html_write.of( safe_bytes )
def _( s, out, enc ): out.write( s )

@html_write.of( safe_unicode )
def _( s, out, enc ): out.write( s.encode( enc, 'strict' ) )

@html_write.of( NoneType )
def _( n, out, enc ): pass

@html_write.of( bool )
def _( b, out, enc ): out.write( unicode( b ).encode( enc, 'strict' ) )

@html_write.of( Number )
def _( num, out, enc ): out.write( unicode( num ).encode( enc, 'strict' ) )

@html_write.of( Callable )
def _( f, out, enc ): html_write( f(), out, enc )

@html_write.of( Iterable )
def _( seq, out, enc ):
    for x in seq: html_write( x, out, enc )

@html_write.of( Attribute )
def _( attr, out, enc ):
    html_write( (safe_unicode( u' ' ), attr.name, 
                 safe_unicode( u'="' ), attr.value, safe_unicode( u'"' )), 
                out, enc )

@html_write.of( Element )
def _( elem, out, enc ):
    html_write( (safe_unicode( u'<' ), elem.name, elem.attrs, safe_unicode( u'>' )),
                out, enc )
    if not elem.empty: 
        html_write( (elem.children, safe_unicode( u'</' ),
                     elem.name, safe_unicode( u'>' )), out, enc )

def __write_script_and_style( elem, out, enc ):
    html_write( (safe_unicode( u'<' ), elem.name, elem.attrs, safe_unicode( u'>' )),
                out, enc )
    for s in elem.children:
        if isinstance( s, str ): out.write( s )
        else: out.write( s.encode( enc, 'strict' ) )
    html_write( (safe_unicode( u'</' ), elem.name, safe_unicode( u'>' )), out, enc )
        
html_write.of( ScriptType )( __write_script_and_style )
html_write.of( StyleType )( __write_script_and_style )
                
@html_write.of( DocType )
def _( elem, out, enc ):
    html_write( (u'<!DOCTYPE html>', HtmlType( self.attrs, self.children )),
                out, enc )

@html_write.of( Page )
def _( pg, out, enc ):
    html_write( doc( lang='en' )[
        head[ meta( http_equiv=u'Content-Type', 
                    content=u'text/html;charset=' + pg.encoding ),
              title[ pg.title ] ],
        body[ pg.content ] ], out, enc )
