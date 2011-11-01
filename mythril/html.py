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

default_lang = 'en'

class _HtmlWriterBlock( list ):
    __slots__ = ('followed_by', 'section')
    def __init__( self, section, *args, **kwargs ): 
        self.followed_by = None
        self.section = section
        list.__init__( self, *args, **kwargs )

class _HtmlWriterSection( list ):
    __slots__ = ('seen_keys',)
    def __init__( self, *args, **kwargs ): 
        self.seen_keys = set()
        list.__init__( self, *args, **kwargs )

class HtmlWriter( object ):
    """ Writes Python values as an HTML unicode representation. For advanced use.
    See `dump` or `dumps` in this module for a simpler method of generating
    HTML. Any arbitrary Python type can support/extend being written to
    ``HtmlWriter`` by implementing an ``__html__`` method; it should take the
    ``HtmlWriter`` instance as its sole argument.
    
    The output is always a unicode string. Plain ``str``s are converted to unicode.
    If provided, the ``encoding`` is used for decoding ``str``s, otherwise, the
    system default will be used.
    
    It is designed to support writing keyed "resources" to specific
    locations in the document (mostly, CSS and JS includes) this allows these
    resources to appear multiple times at any location in the document and
    be moved, and only appear once, at the appropriate location. See the
    classes `mythril.html.Resource` and `mythril.html.Include`. Be careful not
    to `Include` a resource inside itself; cycles are not detected. 
    """
    # TODO: implement in C
    def __init__( self, encoding=None ):
        self.encoding = encoding or sys.getdefaultencoding()
        self.stack = []
        self.current = _HtmlWriterBlock( None )
        self.sections = { None: _HtmlWriterSection( (self.current,) ) }
                           # { section_name: [ _HtmlWriterBlock ] }. 
                           # None will be the default section

    def write( self, value ):
        """ Writes the arbitrary Python value ``value`` as HTML to the internal
        buffers. """
        self.stack.append( value )
        
        if hasattr( value, '__html__' ): value.__html__( self )

        elif isinstance( value, basestring ):
            unesc = value if isinstance(value, unicode) \
                    else value.decode(self.encoding)
            self.current.append(html_escape(unesc, True))

        elif isinstance( value, Iterable ):
            for item in value: self.write( item )

        elif isinstance( value, Callable ): self.write( value() )

        else: self.current.append(unicode(value))
        
        self.stack.pop()
        return self
        
    def append_section( self, section_name, lst ):
        """ Internal. """
        section = self.sections.get( section_name )
        if section:
            for block in section:
                for data in block: lst.append(data)
                if block.followed_by is not None: 
                    self.append_section(block.followed_by, lst)

    def getvalue( self, section=None ):
        """ Concats all the seen data into a single buffer """
        ret = []; self.append_section(section, ret)
        return u''.join(ret)

def dumps( value, encoding=None ):
    """ Converts ``value`` to its HTML unicode representation.

    The output is always a unicode string. Plain ``str``s are converted to unicode.
    If provided, the ``encoding`` is used for decoding ``str``s, otherwise, the
    system default will be used.
    
    It is designed to support writing keyed "resources" to specific
    locations in the document (mostly, CSS and JS includes) this allows these
    resources to appear multiple times at any location in the document and
    be moved, and only appear once, at the appropriate location. See the
    classes `mythril.html.Resource` and `mythril.html.Include`. Be careful not
    to `Include` a resource inside itself; cycles are not detected. 

    For advanced usage and customization, see `HtmlWriter` in this module.
    """
    return HtmlWriter(encoding).write( value ).getvalue()

def dump( value, fp, encoding=None, output_encoding='UTF-8' ):
    """ Serializes ``value`` as HTML to the writable file-like object ``fp``.
    
    If provided, ``output_encoding`` is used to encode the HTML unicode before
    writing, otherwise, UTF-8 is used. Note: if you are writing to an HTTP
    response, remember to set a Content-Type header with this *same* encoding
    for proper display.

    For all other behavior/arguments are equivalent to `dumps` in this module.

    Note that the HTML writing process involves backreferences (ie.,
    substitutions), so the converted data must be buffered anyway. The use of
    this rather than `dumps` would be purely a matter of convenience (and it is
    here for similarity to other Python serialization APIs)
    """
    fp.write(dumps(value, encoding).encode(output_encoding))

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
        return type( self )( list( Attribute.from_args( attr_pairs, attrs ) ), 
                             self.children )
                                 
    def __getitem__( self, arg ):
        """
        Element[ child1, child2, ... childN ]
        """
        if not type( arg ) == tuple: children = [arg]
        else: children = list(arg)
        return type( self )( self.attrs, children )

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
        etype = type(cls)(str(etype_name), (cls,), {'name': name, 'empty': empty})
        setattr( mod, etype_name, etype )
        setattr( mod, name, etype( attrs=[], children=[] ) )

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
        if isinstance(s, str): wr.current.append(s.decode(wr.encoding))
        elif isinstance(s, unicode): wr.current.append(s)
        else: raise ValueError( 
                'script/style tag: unknown type ' + type( s ).__name__ )
                        
    wr.write( (safe_unicode( u'</' ), self.name, safe_unicode( u'>' )) )

@asmethod( DocType, '__html__' )
def __doc_html__( self, wr ):
    wr.write( (safe_unicode( u'<!DOCTYPE html>' ), 
                 HtmlType( self.attrs, self.children )) )

# safe_bytes and safe_unicode adapted from Travis Rudd's "markup.py"
_as_safe = lambda s: safe_bytes(s) if isinstance(s, str) else safe_unicode(s)

class safe_bytes(str):
    def decode(self, *args, **kws):
        return _as_safe(super(safe_bytes, self).decode(*args, **kws))

    def __add__(self, o):
        res = super(safe_bytes, self).__add__(o)
        if isinstance(o, (safe_unicode, safe_bytes)): return _as_safe(res)
        else: return res

    def __html__(self, writer): 
        writer.current.append(self.decode(writer.encoding))

class safe_unicode(unicode):
    def encode(self, *args, **kws):
        return _as_safe(super(safe_unicode, self).encode(*args, **kws))

    def __add__(self, o):
        res = super(safe_unicode, self).__add__(o)
        if isinstance(o, (safe_unicode, safe_bytes)): return _as_safe(res)
        else: return res

    def __html__( self, writer ):
        writer.current.append(self)
                
class Page( customtuple ):
    """ Useful wrapper for the usual features of a full HTML document """
    def __new__( cls, title, content, encoding=None, lang=None ):
        lang = lang or default_lang
        return tuple.__new__( cls, (title, content, encoding, lang) )

    def __html__( self, wr ):
        wr.write( doc( lang=self.lang )[
            head[ meta((u'http-equiv', u'Content-Type'),
                       (u'content', u'text/html;charset=' + self.encoding))
                    if self.encoding else None,
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
                _HtmlWriterSection( (_HtmlWriterBlock( self.section ),) )
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
        wr.current = _HtmlWriterBlock( sec )
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

class InlineStyle( customtuple ):
    """ A `Resource` for inline CSS rules. The ``<style>`` tag is added
    automatically. Resource section name is 'css' """
    def __new__( cls, content, key=None ):
        return tuple.__new__( cls, (content, key or object()) )
    
    def __html__( self, wr ):
        wr.write(Resource('css', key=self.key, content=_as_safe(self.content)))


class InlineScript( customtuple ):
    """ A `Resource` for inline JS code. The ``<script>`` tag is added
    automatically. Resource section name is 'js' """
    def __new__( cls, content, key=None ):
        return tuple.__new__( cls, (content, key or object()) )

    def __html__( self, wr ):
        wr.write(Resource('js', key=self.key, content=_as_safe(self.content)))

def js_wrap_content( lvalue, content, encoding=None ):
    """ Utility for wrapping your HTML, CSS, and JS in a JS object, which is
    useful for, say, injecting content into a running Page.  In JavaScript,
    assigns an object of ``{ content: "<HTML string>", init: <JS function> }``
    to ``lvalue``. Renders ``content`` and includes css & js resources
    (``content`` holds the HTML & CSS, ``init`` wraps all the JS fragments),
    files included. Custom `Resource` types would have to be `Include`d
    separately
    """
    wr = HtmlWriter( encoding )
    wr.write((content, Include('js_files')))

    content = wr.getvalue()
    css_files = wr.getvalue('css_files')
    css = wr.getvalue('css')
    js = wr.getvalue('js')

    inject = css_files
    if css: 
        inject += u'<style type="text/css">'
        inject += css
        inject += u'</style>'
    inject += content

    if isinstance(lvalue, str): lvalue = lvalue.decode(wr.encoding)
    return lvalue + u'={content:' + json.dumps(inject).decode('ascii') + \
            u',init:function(){' + js + u'}}'

# For convenience, here is a definition of a js script loader (in unicode)
# TODO: document. add to main module documentation?
js_load_script_fn = u"""
function loadScript(url, params, onload) {
    if (typeof params == 'function') {
        onload = params; params = void 0;
    }
    var script = document.createElement('script'),
        head = document.head || document.getElementsByTagName('head')[0],
        hasOwnProp = Object.prototype.hasOwnProperty,
        k, firstParam = url.indexOf('?') == -1,
        done = false;

    if (params) for (k in params) if (hasOwnProp.call(params, k)) {
        if (firstParam) { url += '?'; firstParam = false; }
        else url += '&';
        url += encodeURIComponent(k) + '=' + encodeURIComponent(params[k]);
    }
    
    function finish(aborted) {
        script.parentNode.removeChild(script);
        if (!aborted && onload) onload.call(script);
        onload = script = void 0;
    }

    script.type = 'text/javascript;
    script.onload = script.onreadystatechange = function(e, aborted) {
        if (done) return;

        if (aborted || !this.readyState || this.readyState == 'complete') 
            finish(aborted);
        else if (this.readyState == 'interactive' || this.readyState == 'loaded')
            setTimeout(function() { finish(aborted); }, 0);
        else return;

        e = void 0;
        done = true;
    };
    script.src = url;
    head.appendChild(script);
    head = void 0; // IE mem leaks
};
"""
