# -*- coding: utf-8 -*-
from nose.tools import *
from mythril.html import *

class CamelCasedName: pass
class CamelC4se3Name( object ): pass
def some_func_name(): pass

def test_cssid():
    eq_( Element.cssid( 'foo-bar' ), 'foo-bar' )
    eq_( Element.cssid( CamelCasedName ), 'camel-cased-name' )
    eq_( Element.cssid( some_func_name ), 'some-func-name' )
    eq_( Element.cssid( (CamelCasedName, (CamelC4se3Name, some_func_name), 'foo') ),
            ('camel-cased-name', ('camel-c4se3-name', 'some-func-name'), 'foo') )
    
def test_html():
    eq_( html_bytes([ 'a', 'b', u'c', ('d', u'e'), 
                      set([ 'f', 'f' ]), 4, 4.5,
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
                    'body:after { content: \'&\'; }' ] ]).to_bytes(),
         '<!DOCTYPE html><html lang="en"><head><meta http-equiv="Content-Type" '
         'content="text/html;charset=UTF-8"><title>An Example</title></head><body>'
         '<p>Stuff <a class="some-link" href="#!">more stuff</a></p>'
         '<form target="_blank" action="#!" method="GET" '
         'onsubmit="func_with_esc_args(1, &quot;b&amp;ar&quot;)">'
         '<input type="text" name="stuff"><input type="submit" value="Click me"></form>'
         'Ze unicode: 你好你好<br>Escaped: &lt;&gt; &amp;<b>Hello, world!!</b>'
         '<script type="text/javascript">var x = 1 < 2, y = "&";</script>'
         '<style type="text/css">body:after { content: \'&\'; }</style>'
         '</body></html>' )
