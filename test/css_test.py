# -*- coding: utf-8 -*-
from os import mkdir, path
from os.path import dirname
from shutil import rmtree
from uuid import uuid4
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
    eq_( dumps(
            css( 'a', ('border-radius', 5),
                      ('border_radius', (10, 'left top')),
                      border_radius=(15, 'bottom'),
                      pos=(5, 3),
                      size=(10,15),
                      box_shadow=(1, 0, 3, 1, 'black'),
                      background_gradient((24, 56, 128), (0, 0, 0)) )),
         ' a{border-radius:5px;-webkit-border-radius:5px;-moz-border-radius:5px;'
         'border-top-left-radius:10px;-webkit-border-top-left-radius:10px;'
         '-moz-border-radius-topleft:10px;'
         'background-color:'
         'border-bottom-left-radius:15px;'
         '-webkit-border-bottom-left-radius:15px;-moz-border-radius-bottomleft:15px'
         'border-bottom-right-radius:15px;-webkit-border-bottom-right-radius:15px;'
         '-moz-border-radius-bottomright:15px;box-shadow:1px 0px 3px 1px black ;'
         '-webkit-box-shadow:1px 0px 3px 1px black ;'
         '-moz-box-shadow:1px 0px 3px 1px black ;

def teardown():
    rmtree( mythril.css.resource_file_path )
    mythril.css.resource_file_path = resource_file_path
