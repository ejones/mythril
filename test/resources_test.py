import os
from os import path
from hashlib import md5
from glob import glob
from tempfile import mkdtemp
from nose.tools import *

from mythril.resources import *

noop = lambda: None

def test_url_path():
    set_url_path('/foo/')
    eq_(get_url_path(), '/foo')
    set_url_path('/resources')

def teardown_foo_file(): 
    for f in glob(path.join(get_file_path(), '*foo')): os.remove(f)

@with_setup(noop, teardown_foo_file)
def test_put_string():
    put_string('foo', 'bar')
    eq_(get_url('foo'), '/resources/foo')
    with open(path.join(get_file_path(), 'foo')) as f: eq_(f.read(), 'bar')

@with_setup(noop, teardown_foo_file)
def test_appendables():
    hash = md5()
    def fname(): return hash.hexdigest() + '__foo'

    put_string('foo', 'bar') # to test zat eet eez le cleared
    create_appendable('foo')

    resdata = ['']
    def update_it(data):
        old = fname()
        hash.update(data)
        resdata[0] += data
        add_to_appendable('foo', data)
        with open(path.join(get_file_path(), fname())) as f: 
            eq_(f.read(), resdata[0])
        assert not path.isfile(path.join(get_file_path(), old))
        eq_(get_url('foo'), '/resources/' + fname())

    update_it('Mary had a')
    update_it('little lamb')

@with_setup(noop, teardown_foo_file)
def test_change_file_path():
    put_string('afoo', 'bar')
    put_string('bfoo', 'bar')

    def exists(name): assert path.isfile(path.join(get_file_path(), name))

    exists('afoo'); exists('bfoo')
    old = get_file_path()
    change_file_path(mkdtemp())
    assert not path.isdir(old)
    exists('afoo'); exists('bfoo')
