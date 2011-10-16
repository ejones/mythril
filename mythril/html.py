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

Use `dump` or `dumps` to write out the HTML.
"""
import sys
import re
from types import NoneType
from functools import partial
from itertools import imap
from collections import namedtuple, Callable, Iterable
from numbers import Number
from operator import itemgetter
from cgi import escape as html_escape
from cStringIO import StringIO

try: import simplejson as json
except ImportError: import json # should this be the other way around?

from mythril.util import customtuple, asmethod

noarg = object()

default_encoding = 'UTF-8'
default_lang = 'en'

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
    """ Writes Python values as an HTML byte representation. For advanced use.
    See `dump` or `dumps` in this module for a simpler method of generating
    HTML. Any arbitrary Python type can support/extend being written to
    ``HtmlWriter`` by implementing an ``__html__`` method; it should take the
    ``HtmlWriter`` instance as its sole argument.
    
    For escaping, ``str`` instances are decoded according to its ``encoding``.
    Before being written, all ``unicode`` instances are encoded, again, using
    its ``encoding`` attribute. The string types ``safe_bytes`` and ``safe_unicode``,
    in this module, are not escaped (use with caution!).
    
    It is designed to support writing keyed "resources" to specific
    locations in the document (mostly, CSS and JS includes) this allows these
    resources to appear multiple times at any location in the document and
    be moved, and only appear once, at the appropriate location. See the
    classes `mythril.html.Resource` and `mythril.html.Include`. Be careful not
    to `Include` a resource inside itself; cycles are not detected. 
    """
    # TODO: implement in C
    def __init__( self, encoding=None ):
        self.encoding = encoding or default_encoding
        self.stack = []
        self.current = HtmlWriterBlock( None )
        self.sections = { None: HtmlWriterSection( (self.current,) ) }
                           # { section_name: [ HtmlWriterBlock ] }. 
                           # None will be the default section

    def write( self, value ):
        """ Writes the arbitrary Python value ``value`` as HTML to the internal
        buffers. """
        self.stack.append( value )
        
        if hasattr( value, '__html__' ): value.__html__( self )
        elif isinstance( value, basestring ):
            unesc = value if isinstance( value, unicode ) \
                    else value.decode( self.encoding, 'strict' )
            self.current.append( 
                html_escape( unesc, True ).encode( self.encoding, 'strict' ) )
        elif isinstance( value, Iterable ):
            for item in value: self.write( item )
        elif isinstance( value, Callable ): self.write( value() )
        else: self.current.append( 
                    unicode( value ).encode( self.encoding, 'strict' ) )
        
        self.stack.pop()
        return self
        
    def write_section( self, section_name, file ):
        """ Internal. """
        section = self.sections.get( section_name )
        if section:
            for block in section:
                for data in block: file.write( data )
                if block.followed_by is not None: 
                    self.write_section( block.followed_by, file )

    def getvalue( self, section=noarg ):
        """ Concats all the seen data into a single buffer """
        s = StringIO(); self.write_section( None, s )
        return s.getvalue()

def dumps( value, encoding=None ):
    """ Converts ``value`` to its HTML byte representation.

    For escaping, ``str`` instances are decoded according ``encoding``.
    Before being written, all ``unicode`` instances are encoded, again, using
    ``encoding``. The string types ``safe_bytes`` and ``safe_unicode``,
    in this module, are not escaped (use with caution!).
    
    It is designed to support writing keyed "resources" to specific
    locations in the document (mostly, CSS and JS includes) this allows these
    resources to appear multiple times at any location in the document and
    be moved, and only appear once, at the appropriate location. See the
    classes `mythril.html.Resource` and `mythril.html.Include`. Be careful not
    to `Include` a resource inside itself; cycles are not detected. 

    For advanced usage and customization, see `HtmlWriter` in this module.
    """
    return HtmlWriter( encoding or default_encoding ).write( value ).getvalue()

def dump( value, fp, encoding=None ):
    """ Serializes ``value`` as HTML to the writable file-like object ``fp``.
    For all other behavior/arguments are equivalent to `dumps` in this module.

    Note that the HTML writing process involves backreferences (ie.,
    substitutions), so the converted data must be buffered anyway. The use of
    this rather than `dumps` would be purely a matter of convenience (and it is
    here for similarity to other Python serialization APIs)
    """
    fp.write( dumps( value, encoding ) )

def cssid( val ):
    """
    Normalizes the identifiers in ``val`` into css-ish strings. If
    ``val`` is a ``basestring``, it is returned. If it is something with
    a ``.__name__`` (class, function) it will be turned into the
    hyphenated representation (e.g, MyWidget -> 'my-widget'). If ``val`` is
    a ``tuple``, `cssid` is called on its members.
    """
    if isinstance( val, basestring ): return val
    elif isinstance( val, tuple ): return tuple( imap( cssid, val ) )
    name = val.__name__
    if '_' in name: return name.replace( '_', '-' )
    return re.sub( r'(?<=[a-z0-9])(?=[A-Z])', '-', name ).lower()

Attribute = namedtuple( 'Attribute', 'name,value' )

@asmethod( Attribute )
@classmethod
def from_args( cls, args=(), kwargs={} ):
    for k, v in args:
        if k == u'class': v = cssid( v )
        yield cls( k, v )
    # undocumented feature: we have no guaranteed order on dict items (and thus
    # on kwargs). so we force an order with ``sorted``.
    for k, v in sorted( kwargs.iteritems() ):
        if k.endswith( '_' ): k = k[ :-1 ]
        k = k.replace( '__', ':' ).replace( '_', '-' )
        if k == u'class': v = cssid( v )
        yield cls( k, v )

@asmethod( Attribute )
def __html__( self, wr ):
    wr.write( (safe_unicode( u' ' ), self.name, 
                 safe_unicode( u'="' ), self.value, safe_unicode( u'"' )) )

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
        if not type( arg ) == tuple: arg = (arg,)
        return type( self )( self.attrs, arg )

    @classmethod
    def register( cls, name, empty=False ):
        """
        Registers the given name as an html tag. A subtype of the current type 
        (e.g., `Element`) is added to its module as well as a root instance that 
        must be used to construct the tags of that type. If ``name`` is "article",
        for instance, a subtype named "ArticleType", and a builder instance named
        "article", would be added to the current type's module (e.g., `mythril.html`)

        ``empty`` is for tags like ``input`` which require no closing tag.

        Please give the name in ``unicode``.
        """
        mod = sys.modules[ cls.__module__ ]
        etype_name = name.title() + 'Type'
        etype = type( cls )( (etype_name if isinstance( etype_name, str )
                              else etype_name.encode( 'ascii' )),
                              (cls,), { 'name': name, 'empty': empty } )
        setattr( mod, etype_name, etype )
        setattr( mod, name, etype( attrs=(), children=() ) )

    def __html__( self, wr ):
        wr.write( (safe_unicode( u'<' ), self.name, 
                    self.attrs, safe_unicode( u'>' )) )
        if not self.empty: 
            wr.write( (self.children, safe_unicode( u'</' ),
                         self.name, safe_unicode( u'>' )) )

map( Element.register, u'''
    a abbr acronym address applet b bdo big blockquote body button
    caption center cite code colgroup dd dfn div dl dt doc html em fieldset
    font form frameset h1 h2 h3 h4 h5 h6 head i iframe ins kbd label
    legend li menu noframes noscript ol optgroup option pre q s samp
    select small span strike strong style sub sup table tbody td
    textarea tfoot th thead title tr tt u ul var script frame p tail'''.split() )

map( lambda name: Element.register( name, True ),
     u"area base br col hr img input link meta param".split() )

@asmethod( ScriptType, '__html__' )
@asmethod( StyleType, '__html__' )
def __script_and_style_html__( self, wr ):
    wr.write( (safe_unicode( u'<' ), self.name, self.attrs, safe_unicode( u'>' )) )
    for s in self.children:
        if isinstance( s, str ): wr.current.append( s )
        elif isinstance( s, unicode ): wr.current.append( s.encode( enc, 'strict' ) )
        else: raise ValueError( 
                'script/style tag: unknown type ' + type( s ).__name__ )
                        
    wr.write( (safe_unicode( u'</' ), self.name, safe_unicode( u'>' )) )

@asmethod( DocType, '__html__' )
def __doc_html__( self, wr ):
    wr.write( (safe_unicode( u'<!DOCTYPE html>' ), 
                 HtmlType( self.attrs, self.children )) )

# safe_bytes and safe_unicode borrowed from Travis Rudd's "markup.py"
class safe_bytes(str):
    def decode(self, *args, **kws):
        return safe_unicode(super(safe_bytes, self).encode(*args, **kws))

    def __add__(self, o):
        res = super(safe_bytes, self).__add__(o)
        if isinstance(o, safe_unicode): return safe_unicode(res)
        elif isinstance(o, safe_bytes): return safe_bytes(res)
        else: return res

    def __html__( self, writer ):
        writer.current.append( self )

class safe_unicode(unicode):
    def encode(self, *args, **kws):
        return safe_bytes(super(safe_unicode, self).encode(*args, **kws))

    def __add__(self, o):
        res = super(safe_unicode, self).__add__(o)
        if isinstance(o, (safe_unicode, safe_bytes)): return safe_unicode(res)
        else: return res

    def __html__( self, writer ):
        writer.current.append( self.encode( writer.encoding, 'strict' ) )
                
class Page( customtuple ):
    """ Useful wrapper for the usual features of a full HTML document """
    def __new__( cls, title, content, encoding=None, lang=None ):
        encoding = encoding or default_encoding
        lang = lang or default_lang
        return tuple.__new__( cls, (title, content, encoding, lang) )
        
    def dumps( self ):
        """ Convenience for `dump` since we already have the
        encoding """
        return dumps( self, self.encoding )

    def dump( self, fp ):
        """ Convenience for `dumps` since we already have the encoding """
        return dump( self, fp, self.encoding )

    def __html__( self, wr ):
        wr.write( doc( lang=self.lang )[
            head[ meta( (u'http-equiv', u'Content-Type'),
                        (u'content', u'text/html;charset=' + self.encoding) ),
                  title[ self.title ],
                  Include( 'css_files' ),
                  safe_unicode( u'<style type="text/css">'),
                  Include( 'css' ),
                  safe_unicode( u'</style>' ) ], # TODO: check if there actually
                                                 #  is any CSS (also for JS below)
            body[ self.content,
                  Include( 'js_files' ),
                  safe_unicode( u'<script type="text/javascript">' ),
                  Include( 'js' ),
                  safe_unicode( u'</script>' )]] )

class Resource( customtuple ):
    """ Describes a part of an HTML document that must appear at a specific 
    location (e.g., in the ``<head>`` or at the end) and, if given a 
    unique key, only once per unique key. """
    def __new__( cls, section, content, key=None ):
        return tuple.__new__( cls, (section, content, key or object()) )

    def __html__( self, wr ):
        section = wr.sections.get( self.section )
        if section is None: 
            section = wr.sections[ self.section ] = \
                HtmlWriterSection( (HtmlWriterBlock( self.section ),) )
        elif self.key in section.seen_keys: return

        section.seen_keys.add( self.key )
        old = wr.current
        wr.current = section[ -1 ]
        wr.write( self.content )
        wr.current = old

class Include( customtuple ):
    """ Marks its location in the doucment as the point for inclusion of
    the corresponding `Resource` elements """
    def __new__( cls, section ):
        return tuple.__new__( cls, (section,) )

    def __html__( self, wr ):
        wr.current.followed_by = self.section
        sec = wr.current.section
        wr.current = HtmlWriterBlock( sec )
        wr.sections[ sec ].append( wr.current )

class CSSFile( customtuple ):
    """ Represents a `Resource` of a single CSS file. Resource section name is
    'css_files' """
    def __new__( cls, url, key=None ):
        return tuple.__new__( cls, (url, key or object()) )

    def __html__( self, wr ):
        wr.write( Resource( 'css_files', key=self.key,
                            content=link( rel=u'stylesheet', type=u'text/css',
                                          href=self.url )))

class JSFile( customtuple ):
    """ Represents a `Resource` of a single JS file. Resource section name is
    'js_files' """
    def __new__( cls, url, key=None ):
        return tuple.__new__( cls, (url, key or object()) )

    def __html__( self, wr ):
        wr.write( Resource( 'js_files', key=self.key,
                            content=script( type=u'text/javascript',
                                            src=self.url )))

class StyleResource( customtuple ):
    """ A `Resource` for inline CSS rules. The ``<style>`` tag is added
    automatically. Resource section name is 'css' """
    def __new__( cls, content, key=None ):
        return tuple.__new__( cls, (content, key or object()) )
    
    def __html__( self, wr ):
        c = self.content
        wr.write( Resource( 'css', key=self.key,
                            content=( safe_unicode( c ) if isinstance( c, unicode )
                                      else safe_bytes( c ) )))

class ScriptResource( customtuple ):
    """ A `Resource` for inline JS code. The ``<script>`` tag is added
    automatically. Resource section name is 'js' """
    def __new__( cls, content, key=None ):
        return tuple.__new__( cls, (content, key or object()) )

    def __html__( self, wr ):
        c = self.content
        wr.write( Resource( 'js', key=self.key,
                            content=( safe_unicode( c ) if isinstance( c, unicode )
                                      else safe_bytes( c ) )))

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
        s = StringIO(); wr.write_section( section_name, s )
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

    if isinstance( lvalue, unicode ): lvalue = lvalue.encode( encoding, 'strict' )
    return ''.join( 
        (lvalue, u'={content:'.encode( encoding, 'strict' ),
         json.dumps( binject, encoding=encoding ).encode( encoding, 'strict' ),
         u',init:function(){'.encode( encoding, 'strict' ),
         js, u'}}'.encode( encoding, 'strict' )) )
