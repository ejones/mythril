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
    eq_( dumps([ 'a', 'b', u'c', ('d', u'e'), set([ 'f', 'f' ]), 4, 4.5,
                  (i*2 for i in xrange(5)) ]),
         u'abcdef44.502468' )

    eq_( dumps(Page( 'An Example', encoding='UTF-8', lang='en',
            content=[
                p[ 'Stuff ', a( 'some-link', href='#!' )[ 'more stuff' ] ],
                form( target='_blank', action='#!', method='GET',
                      onsubmit='func_with_esc_args(1, "b&ar")' )[
                    input( type='text', name='stuff' ),
                    input( type='submit', value='Click me' )],
                'Ze unicode: ', '你好', u'你好', br,
                'Escaped: ', '<', u'> &',
                safe_unicode( u'<b>Hello, world!!</b>' ),
                script( type='text/javascript' )[
                    'var x = 1 < 2, y = "&";' ],
                style( type='text/css' )[
                    'body:after { content: \'&\'; }' ] ]), encoding='UTF-8'),
         u'<!DOCTYPE html><html lang="en"><head><meta http-equiv="Content-Type" '
         u'content="text/html;charset=UTF-8"><title>An Example</title>'
         u'<style type="text/css"></style></head><body>'
         u'<p>Stuff <a class="some-link" href="#!">more stuff</a></p>'
         u'<form action="#!" method="GET" '
         u'onsubmit="func_with_esc_args(1, &quot;b&amp;ar&quot;)" target="_blank">'
         u'<input name="stuff" type="text"><input type="submit" value="Click me">'
         u'</form>'
         u'Ze unicode: 你好你好<br>Escaped: &lt;&gt; &amp;<b>Hello, world!!</b>'
         u'<script type="text/javascript">var x = 1 < 2, y = "&";</script>'
         u'<style type="text/css">body:after { content: \'&\'; }</style>'
         u'<script type="text/javascript"></script></body></html>' )

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
            safe_unicode( u'</script>' ))),
        u'<span>before css files</span><link href="/path/to/css.css" '
        u'rel="stylesheet"'
        u' type="text/css"><link href="/path/to/other.css" rel="stylesheet"'
        u' type="text/css"><span>before css</span><style type="text/css">'
        u'body{ margin: 0; }</style><span>before js stuff</span><script '
        u'src="/path/to/js.js" type="text/javascript"></script><script '
        u'type="text/javascript">var x = "foo";</script>' )

    eq_( js_wrap_content( 'garply', [
            span[ "Some content" ],
            CSSFile( '/some/stylesheet.css' ),
            ScriptResource( 'var x = "bar";' )] ),
        u'garply={content:"<link href=\\"/some/stylesheet.css\\" '
        u'rel=\\"stylesheet\\" type=\\"text/css\\"><span>Some content</span>",init:'
        u'function(){var x = "bar";}}' )
            


