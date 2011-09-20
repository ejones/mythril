"""
Python values representing HTML elements. These allow for the creation of HTML
documents and fragments in Python. The standard HTML tags, such as "p" and
"div" are represented as a "builder" instance, like ``mythril.html.div``
and as a specific type, like ``mythril.html.DivType`` that represents 
elements of that tag. 

A small example::
    
    stuff = div( 'foo-bar' )[ a( 'some-link', href='#!' )[ 'More stuff here' ] ]

Corresponds to something equivalent to::
    
    <div class="foo-bar"><a class="some-link" href="#!">More stuff here</a></div>

See `mythril.html.HtmlWriter` for the class that actually writes the HTML
representation.
"""
import sys
import re
from types import NoneType
from functools import partial
from itertools import chain, starmap, imap
from collections import namedtuple, Callable, Iterable
from numbers import Number
from operator import itemgetter
from cgi import escape as html_escape
from cStringIO import StringIO

try: import simplejson as json
except ImportError: import json # should this be the other way around?

from mythril.protocol import protocol
from mythril.util import customtuple

noarg = object()

default_encoding = 'UTF-8'
default_lang = 'en'

Attribute = namedtuple( 'Attribute', 'name,value' )

@partial( setattr, Attribute, 'from_args' )
@staticmethod
def from_args( args=(), kwargs={} ):
    for k, v in args:
        if k == u'class': v = Element.cssid( v )
        yield Attribute( k, v )
    for k, v in kwargs.iteritems():
        if k.endswith( '_' ): k = k[ :-1 ]
        k = k.replace( '__', ':' ).replace( '_', '-' )
        if k == u'class': v = Element.cssid( v )
        yield Attribute( k, v )

# NB: can't use namedtuple here because its constructor seems to call
#  __getitem__, which ends up messing with the cosmos
class Element( customtuple ):
    name = ''
    empty = False
    
    def __new__( cls, attrs, children ):
        return tuple.__new__( cls, (attrs, children) )

    def __repr__( self ):
        return ((self.name or type( self ).__name__)
            + (('(' + ', '.join( repr( tuple( a ) ) for a in self.attrs ) + ')')
                    if self.attrs else '')
            + (('[' +  ', '.join( imap( repr, self.children ) ) + ']')
                    if self.children else ''))

    def __call__( self, *attr_pairs, **attrs ):
        """ 
        Element( (attr_name, attr_value), ..., attr_name=attr_value, ...) ->
        Element( css_class, (attr_name, attr_value), ..., attr_name=attr_value, ...) ->
        """
        
        if len( attr_pairs ) > 0 and isinstance( attr_pairs[ 0 ], basestring ):
            attr_pairs = ((u'class', attr_pairs[ 0 ]),) + attr_pairs[ 1: ]
        return type( self )( tuple( Attribute.from_args( attr_pairs, attrs ) ), 
                             self.children )
                                 
    def __getitem__( self, arg ):
        """
        Element[ child1, child2, ... childN ]
        """
        if not isinstance( arg, tuple ): arg = (arg,)
        return type( self )( self.attrs, arg )

    @staticmethod
    def cssid( val, camel_match=re.compile( r'(?<=[a-z0-9])(?=[A-Z])' ) ):
        """
        Normalizes the identifiers in ``val`` into css-ish strings. If
        ``val`` is a ``basestring``, it is returned. If it is something with
        a ``.__name__`` (class, function) it will be turned into the
        hyphenated representation (e.g, MyWidget -> 'my-widget'). If ``val`` is
        a ``tuple``, `cssid` is called recursively on its members.
        """
        if isinstance( val, basestring ): return val
        elif isinstance( val, tuple ): return tuple( imap( Element.cssid, val ) )
        name = val.__name__
        if '_' in name: return name.replace( '_', '-' )
        return camel_match.sub( '-', name ).lower()

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
    textarea tfoot th thead title tr tt u ul var script frame p tail'''.split() )

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
                
class Page( customtuple ):
    """ Useful wrapper for the usual features of a full HTML document """
    def __new__( cls, title, content, encoding=None, lang=None ):
        encoding = encoding or default_encoding
        lang = lang or default_lang
        return tuple.__new__( cls, (title, content, encoding, lang) )

    def write_to( self, out ):
        """ Convenience for `html_write` since we already have the encoding """
        return html_write( self, out, self.encoding )
        
    def to_bytes( self ):
        """ Convenience for `HtmlWriter.to_bytes` since we already have the
        encoding """
        return HtmlWriter.to_bytes( self, self.encoding )

class Resource( customtuple ):
    """ Describes a part of an HTML document that must appear at a specific 
    location (e.g., in the ``<head>`` or at the end) and, if given a 
    unique key, only once per unique key. """
    def __new__( cls, section, content, key=None ):
        return tuple.__new__( cls, (section, content, key or object()) )

class Include( customtuple ):
    """ Marks its location in the doucment as the point for inclusion of
    the corresponding `Resource` elements """
    def __new__( cls, section ):
        return tuple.__new__( cls, (section,) )

class CSSFile( customtuple ):
    """ Represents a `Resource` of a single CSS file. Resource section name is
    'css_files' """
    def __new__( cls, url, key=None ):
        return tuple.__new__( cls, (url, key or object()) )
        
class JSFile( customtuple ):
    """ Represents a `Resource` of a single JS file. Resource section name is
    'js_files' """
    def __new__( cls, url, key=None ):
        return tuple.__new__( cls, (url, key or object()) )

class StyleResource( customtuple ):
    """ A `Resource` for inline CSS rules. The ``<style>`` tag is added
    automatically. Resource section name is 'css' """
    def __new__( cls, content, key=None ):
        return tuple.__new__( cls, (content, key or object()) )

class ScriptResource( customtuple ):
    """ A `Resource` for inline JS code. The ``<script>`` tag is added
    automatically. Resource section name is 'js' """
    def __new__( cls, content, key=None ):
        return tuple.__new__( cls, (content, key or object()) )

class HtmlWriterBlock( list ):
    """ Internal use for `HtmlWriter` """
    __slots__ = ('followed_by', 'section')
    def __init__( self, section, *args, **kwargs ): 
        self.followed_by = None
        self.section = section
        list.__init__( self, *args, **kwargs )

class HtmlWriterSection( list ):
    """ Internal use for `HtmlWriter` """
    __slots__ = ('seen_keys',)
    def __init__( self, *args, **kwargs ): 
        self.seen_keys = set()
        list.__init__( self, *args, **kwargs )

class HtmlWriter( object ):
    """ Writes arbitrary Python values into HTML. ``HtmlWriter.write_of``
    allows for the extension of this facility to new types. See
    ``HtmlWriter.to_bytes`` for a convenience method for writing a bunch of
    stuff into HTML in one go (this should be the primary high-level use). 
    
    For escaping, ``str`` instances are decoded according to its ``encoding``.
    Before being written, all ``unicode`` instances are encoded, again, using
    its ``encoding`` attribute.
    
    Additionally, it is designed to support writing keyed "resources" to specific
    locations in the document (mostly, CSS and JS includes) this allows these
    resources to appear multiple times at any location in the document and
    be moved, and only appear once, at the appropriate location. See the
    classes `mythril.html.Resource` and `mythril.html.Include`. Be careful not
    to `Include` a resource inside itself; cycles are not detected. Neither are
    repeat `Includes`.
    """
    _protocol = protocol( lambda obj, self: self.write( repr( obj ) ) )
    
    def __init__( self, encoding=None ):
        self.encoding = encoding or default_encoding
        self.stack = []
        self.current = HtmlWriterBlock( None )
        self.sections = { None: HtmlWriterSection( (self.current,) ) }
                           # { section_name: [ HtmlWriterBlock ] }. 
                           # None will be the default section

    def write( self, value ):
        """ Writes the arbitrary Python value ``value`` as HTML to the internal
        file [sections], This facility can be extended with
        ``HtmlWriter.write_of`` """
        self.stack.append( value )
        self._protocol( value, self )
        self.stack.pop()
        return self
        
    def getvalue( self, section=noarg ):
        """ Concats all the seen data into a single buffer """
        s = StringIO(); self.write_section( None, s )
        return s.getvalue()

    def write_section( self, section_name, file ):
        """ Internal. """
        section = self.sections.get( section_name )
        if section:
            for block in section:
                for data in block: file.write( data )
                if block.followed_by is not None: 
                    self.write_section( block.followed_by, file )

    @classmethod
    def write_of( cls, type ):
        """ Allows you to extend HtmlWriter functionality to encompass new
        types.  Decorate a function with ``@HtmlWriter.write_of( <Your Type>
        )``. The function should take the ``HtmlWriter`` as the *first*
        argument and the value (of your type) as the *second*. """
        return lambda func: \
            cls._protocol.of( type )( lambda val, self: func( self, val ) )
        
    @classmethod
    def to_bytes( cls, value, encoding=None ):
        """ Convenience for quickly converting ``value`` into its equivalent
        HTML byte representation. """
        encoding = encoding or default_encoding
        return cls( encoding ).write( value ).getvalue()

@HtmlWriter.write_of( str )
def _( wr, s ):
    wr.current.append( 
        html_escape( unicode( s, wr.encoding, 'strict' ), True )
            .encode( wr.encoding, 'strict' ) )

@HtmlWriter.write_of( unicode )
def _( wr, s ): 
    wr.current.append( html_escape( s, True ).encode( wr.encoding, 'strict' ) )

@HtmlWriter.write_of( safe_bytes )
def _( wr, s ): wr.current.append( s )

@HtmlWriter.write_of( safe_unicode )
def _( wr, s ): wr.current.append( s.encode( wr.encoding, 'strict' ) )

@HtmlWriter.write_of( NoneType )
def _( wr, non ): pass

@HtmlWriter.write_of( bool )
def _( wr, b ): wr.current.append( unicode( b ).encode( wr.encoding, 'strict' ) )

@HtmlWriter.write_of( Number )
def _( wr, num ): wr.current.append( unicode( num ).encode( wr.encoding, 'strict' ) )

@HtmlWriter.write_of( Callable )
def _( wr, f ): wr.write( f() )

@HtmlWriter.write_of( Iterable )
def _( wr, seq ): 
    for x in seq: wr.write( x )

@HtmlWriter.write_of( Resource )
def _( wr, res ):
    section = wr.sections.get( res.section )
    if section is None: 
        section = wr.sections[ res.section ] = \
            HtmlWriterSection( (HtmlWriterBlock( res.section ),) )
    elif res.key in section.seen_keys: return

    section.seen_keys.add( res.key )
    old = wr.current
    wr.current = section[ -1 ]
    wr.write( res.content )
    wr.current = old

@HtmlWriter.write_of( Include )
def _( wr, inc ):
    wr.current.followed_by = inc.section
    sec = wr.current.section
    wr.current = HtmlWriterBlock( sec )
    wr.sections[ sec ].append( wr.current )

@HtmlWriter.write_of( Attribute )
def _( wr, attr ):
    wr.write( (safe_unicode( u' ' ), attr.name, 
                 safe_unicode( u'="' ), attr.value, safe_unicode( u'"' )) )

def __write_element( wr, elem ):
    wr.write( (safe_unicode( u'<' ), elem.name, elem.attrs, safe_unicode( u'>' )) )
    if not elem.empty: 
        wr.write( (elem.children, safe_unicode( u'</' ),
                     elem.name, safe_unicode( u'>' )) )

HtmlWriter.write_of( Element )( __write_element )

def __write_script_and_style( wr, elem ):
    wr.write( (safe_unicode( u'<' ), elem.name, elem.attrs, safe_unicode( u'>' )) )
    for s in elem.children:
        if isinstance( s, str ): wr.current.append( s )
        elif isinstance( s, unicode ): wr.current.append( s.encode( enc, 'strict' ) )
        else: raise ValueError( 
                'script/style tag: unknown type ' + type( s ).__name__ )
                        
    wr.write( (safe_unicode( u'</' ), elem.name, safe_unicode( u'>' )) )
        
HtmlWriter.write_of( ScriptType )( __write_script_and_style )
HtmlWriter.write_of( StyleType )( __write_script_and_style )
                
@HtmlWriter.write_of( DocType )
def _( wr, elem ):
    wr.write( (safe_unicode( u'<!DOCTYPE html>' ), 
                 HtmlType( elem.attrs, elem.children )) )

@HtmlWriter.write_of( CSSFile )
def _( wr, cssf ):
    wr.write( Resource( 'css_files', key=cssf.key,
                        content=link( (u'rel', u'stylesheet'), 
                                      (u'type', u'text/css'),
                                      href=cssf.url )))

@HtmlWriter.write_of( JSFile )
def _( wr, jsf ):
    wr.write( Resource( 'js_files', key=jsf.key,
                        content=script( (u'type', u'text/javascript'), src=jsf.url )))

@HtmlWriter.write_of( StyleResource )
def _( wr, styl ):
    c = styl.content
    wr.write( Resource( 'css', key=styl.key,
                        content=( safe_unicode( c ) if isinstance( c, unicode )
                                  else safe_bytes( c ) )))

@HtmlWriter.write_of( ScriptResource )
def _( wr, styl ):
    c = styl.content
    wr.write( Resource( 'js', key=styl.key,
                        content=( safe_unicode( c ) if isinstance( c, unicode )
                                  else safe_bytes( c ) )))

@HtmlWriter.write_of( Page )
def _( wr, pg ):
    wr.write( doc( lang=pg.lang )[
        head[ meta( (u'http-equiv', u'Content-Type'),
                    (u'content', u'text/html;charset=' + pg.encoding) ),
              title[ pg.title ],
              Include( 'css_files' ),
              safe_unicode( u'<style type="text/css">'),
              Include( 'css' ),
              safe_unicode( u'</style>' ) ], # TODO: check if there actually
                                             #  is any CSS (also for JS below)
        body[ pg.content,
              Include( 'js_files' ),
              safe_unicode( u'<script type="text/javascript">' ),
              Include( 'js' ),
              safe_unicode( u'</script>' )]] )

def js_injection( lvalue, content, encoding=None ):
    """ Utility for injecting content into a running Page.  In JavaScript,
    assigns an object of ``{ content: "<HTML string>", init: <JS function> }``
    to ``lvalue``. Renders ``content`` and includes css & js resources, files
    included. Custom `Resource` types would have to be `Include`d separately
    """
    encoding = encoding or default_encoding
    wr = HtmlWriter( encoding )
    bcontent = wr.write( (content, Include( 'js_files' )) ).getvalue()
    
    def get_section_value( section_name ):
        s = StringIO(); wr.write_section( section_name, s );
        return s.getvalue()
        
    css_files = get_section_value( 'css_files' )
    css = get_section_value( 'css' )
    js = get_section_value( 'js' )

    binject = css_files
    if css: 
        binject += u'<style type="text/css">'.encode( encoding, 'strict' )
        binject += css
        binject += u'</style>'.encode( encoding, 'strict' )
    binject += bcontent
    inject_html = unicode( binject, encoding, 'strict' )

    if isinstance( lvalue, unicode ): lvalue = lvalue.encode( encoding, 'strict' )
    return ''.join( (lvalue, u'={content:'.encode( encoding, 'strict' ),
                     json.dumps( inject_html ).encode( encoding, 'strict' ),
                     u',init:function(){'.encode( encoding, 'strict' ),
                     js, u'}}'.encode( encoding, 'strict' )) )
