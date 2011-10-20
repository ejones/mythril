# -*- coding: utf-8 -*-
from os import mkdir, path
from os.path import dirname
from shutil import rmtree
from uuid import uuid4
import Image
from itertools import imap
from operator import eq
import re
from cStringIO import StringIO
from nose.tools import *

import mythril.css
from mythril.css import *

class MyClass: pass
class SomeUtility: pass

def setup():
    tmpdir = path.join( dirname(__file__), '_%x' % uuid4().fields[5] )
    mkdir( tmpdir )
    mythril.css.resource_file_path = tmpdir

def test_css():
    eq_( dumps(
            css( MyClass, ('color', 'white'), 
                       border=(1, 'solid', '#CCC'), 
                       padding=5, 
                       size=(200, 50), 
                       box_sizing='border-box' )[
            css( (u'some-class', SomeUtility), pos=(1, 0, 'relative bottom') )]),

         ' my-class{color:white;border:1px solid #CCC;box-sizing:border-box;'
         'padding:5px;width:200px;height:50px;} my-class some-class, my-class '
         'some-utility{position:relative;left:1px;bottom:0px;}' )

    eq_( dumps( css( ('a','b'), padding=0 )[ css( ('c','d'), padding=0 ) ] ),
         ' a, b{padding:0px;} a c, a d, b c, b d{padding:0px;}' )

def test_special():
    eq_( color(32, 64, 128), u'#204080' )
    eq_( color(32, 64, 128, 255), u'rgba(32,64,128,1.0)' )
    eq_( color(255,255,255,127/255.0), color(255,255,255,127) )

    def speq( name, args, attrs ):
        eq_( css( '', (name,args) ).attrs, attrs )
        
    speq( 'pos', (5,10), ((u'position', u'absolute'),
                          (u'left', 5), (u'top', 10)))
    speq( 'pos', (5,10,u'fixed right'), ((u'position', u'fixed'),
                                         (u'right', 5), (u'top', 10)))
    speq( 'pos', (5,10,u'bottom relative'), ((u'position', u'relative'),
                                             (u'left',5), (u'bottom',10)) )
    
    speq( 'size', (5,10), ((u'width',5), (u'height',10)) )

    speq( 'border-radius', 5, ((u'border-radius', 5),
                               (u'-webkit-border-radius', 5),
                               (u'-moz-border-radius',5)) )
    eq_( css('', border_radius=5).attrs, ((u'border-radius', 5),
                                          (u'-webkit-border-radius', 5),
                                          (u'-moz-border-radius',5)) )
    speq( 'border-radius', (5,'top'), ((u'border-top-left-radius', 5),
                                       (u'-webkit-border-top-left-radius', 5),
                                       (u'-moz-border-radius-topleft', 5),
                                       (u'border-top-right-radius', 5),
                                       (u'-webkit-border-top-right-radius', 5),
                                       (u'-moz-border-radius-topright', 5)) )
    speq( 'border-radius', (5,'top left'), ((u'border-top-left-radius', 5),
                                            (u'-webkit-border-top-left-radius', 5),
                                            (u'-moz-border-radius-topleft', 5),) )

    speq( 'box-shadow', (5,10,5,5,'#CCC'), 
                ((u'box-shadow', (5,10,5,5,'#CCC','')),
                 (u'-webkit-box-shadow', (5,10,5,5,'#CCC','')),
                 (u'-moz-box-shadow', (5,10,5,5,'#CCC',''))) )

    speq( 'background-gradient', ((0,0,0), (32, 128, 64)),
                ((u'background-color', u'#104020'),
                 (u'background-image', u'-webkit-gradient(linear, left top, '
                                       u'left bottom, from(#000000), to(#208040))'),
                 (u'background-image', 
                    u'-webkit-linear-gradient(top,#000000,#208040)'),
                 (u'background-image',
                    u'-moz-linear-gradient(top,#000000,#208040)'),
                 (u'background-image',
                    u'-o-linear-gradient(top,#000000,#208040)'),
                 (u'background-image',
                    u'-ms-linear-gradient(top,#000000,#208040)'),
                 (u'background-image', u'linear-gradient(top,#000000,#208040)')) )

    speq( 'opacity', .7, ((u'opacity', .7),
                          (u'filter', u'alpha(opacity=70)'),
                          (u'zoom', u'1')) )
    
    @special.register( name='-testy-test' )
    def _test_abc( arg ):
        return ((u'a',arg), (u'b',arg), (u'c',arg))
    speq( '-testy-test', 5, ((u'a',5), (u'b',5), (u'c',5)) )

def test_resource_generators():
    
    def pngeq( file1, file2 ):
        im1, im2 = Image.open(file1), Image.open(file2)
        assert all(imap(eq, im1.getdata(), im2.getdata())), \
              'Images were not equal: %r, %r' % (file1, file2)

    inlattr, fattr = css('', 
        static_background_gradient=((255,34,128), (23,69,128), 50)).attrs
    eq_(inlattr.name, 'background')
    eq_(fattr.name, '*background')
    
    bkgd_grad_test_image = path.join(dirname(__file__), 
                                     'static_background_gradient_test_image.png')

    m = re.match(r'^url\(data:image/png;base64,([^)]+)\) 0 0 repeat-x$', 
                 inlattr.value)
    assert m, 'Incorrect format of inline image attribute: ' + repr(inlattr.value)
    pngeq(StringIO(m.group(1).decode('base64')), bkgd_grad_test_image)

    m = re.match(r'^url\((/[^/]+)/([^)]+)\) 0 0 repeat-x$', fattr.value)
    assert m, 'Incorrect format of file image attribute: ' + repr(fattr.value)
    assert m.group(1) == mythril.css.resource_url_path, \
          'Bad image url: ' + repr(fattr.value)
    pngeq(path.join(mythril.css.resource_file_path, m.group(2)),
          bkgd_grad_test_image)
    

def teardown():
    rmtree( mythril.css.resource_file_path )
    mythril.css.resource_file_path = resource_file_path
