# -*- coding: utf-8 -*-
from nose.tools import *
from mythril.html import *

class CamelCasedName: pass
class CamelC4se3Name( object ): pass
def some_func_name(): pass

def test_cssid():
    eq_( cssid( 'foo-bar' ), 'foo-bar' )
    eq_( cssid( CamelCasedName ), 'camel-cased-name' )
    eq_( cssid( some_func_name ), 'some-func-name' )
    eq_( cssid( (CamelCasedName, (CamelC4se3Name, some_func_name), 'foo') ),
            ('camel-cased-name', ('camel-c4se3-name', 'some-func-name'), 'foo') )
    
def test_html():
    eq_( dumps( [ 'a', 'b', u'c', ('d', u'e'), set([ 'f', 'f' ]), 4, 4.5,
                  (i*2 for i in xrange(5)) ],
               'UTF-8'),
         'abcdef44.502468' )

    eq_( Page( 'An Example', encoding='UTF-8', lang='en',
            content=[
                p[ 'Stuff ', a( 'some-link', href='#!' )[ 'more stuff' ] ],
                form( (u'target', u'_blank'), (u'action', u'#!'), (u'method', u'GET'),
                      onsubmit='func_with_esc_args(1, "b&ar")' )[
                    input( (u'type', u'text'), name='stuff' ),
                    input( (u'type', u'submit'), value='Click me' )],
                'Ze unicode: ', '你好', u'你好', br,
                'Escaped: ', '<', u'> &',
                safe_unicode( u'<b>Hello, world!!</b>' ),
                script( type='text/javascript' )[
                    'var x = 1 < 2, y = "&";' ],
                style( type='text/css' )[
                    'body:after { content: \'&\'; }' ] ]).dumps(),
         '<!DOCTYPE html><html lang="en"><head><meta http-equiv="Content-Type" '
         'content="text/html;charset=UTF-8"><title>An Example</title>'
         '<style type="text/css"></style></head><body>'
         '<p>Stuff <a class="some-link" href="#!">more stuff</a></p>'
         '<form target="_blank" action="#!" method="GET" '
         'onsubmit="func_with_esc_args(1, &quot;b&amp;ar&quot;)">'
         '<input type="text" name="stuff"><input type="submit" value="Click me"></form>'
         'Ze unicode: 你好你好<br>Escaped: &lt;&gt; &amp;<b>Hello, world!!</b>'
         '<script type="text/javascript">var x = 1 < 2, y = "&";</script>'
         '<style type="text/css">body:after { content: \'&\'; }</style>'
         '<script type="text/javascript"></script></body></html>' )

    eq_( dumps((
            span[ "before css files" ],
            Include( 'css_files' ),
            span[ "before css" ],
            safe_unicode( u'<style type="text/css">' ),
            Include( 'css' ),
            safe_unicode( u'</style>' ),
            StyleResource( 'body{ margin: 0; }' ),
            CSSFile( '/path/to/css.css', 'css.css' ),
            JSFile( '/path/to/js.js' ),
            CSSFile( '/path/to/other.css' ),
            span[ "before js stuff" ],
            CSSFile( '/repeated/resource', 'css.css' ),
            ScriptResource( 'var x = "foo";' ),
            Include( 'js_files' ),
            safe_unicode( u'<script type="text/javascript">' ),
            Include( 'js' ),
            safe_unicode( u'</script>' )), 'UTF-8'),
        '<span>before css files</span><link rel="stylesheet" type="text/css" '
        'href="/path/to/css.css"><link rel="stylesheet" type="text/css" '
        'href="/path/to/other.css"><span>before css</span><style type="text/css">'
        'body{ margin: 0; }</style><span>before js stuff</span><script '
        'type="text/javascript" src="/path/to/js.js"></script><script '
        'type="text/javascript">var x = "foo";</script>' )

    eq_( js_injection( 'garply', [
            span[ "Some content" ],
            CSSFile( '/some/stylesheet.css' ),
            ScriptResource( 'var x = "bar";' )], 'UTF-8'),
        'garply={content:"<link rel=\\"stylesheet\\" type=\\"text/css\\" '
        'href=\\"/some/stylesheet.css\\"><span>Some content</span>",init:'
        'function(){var x = "bar";}}' )
            


