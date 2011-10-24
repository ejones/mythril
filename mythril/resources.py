"""
Shepherds generated resource files (eg., CSS and JS). Uses a directory for
storage; see the functions `get_file_path` and `change_file_path` to modify
these. The directory defaults to a temp; on app startup, you should move it to
whichever folder you've designated for serving public files. To create callable
resource URLs, see `get_url_path` or the convenience `get_url`.

Where necessary, MD5 hashes are embedded into the served names of resources. As
such, Last-Modified and ETag headers are unneccsary and you can and should
configure the server that serves your static files to use "aggressive caching"
techniques like far-future Expires.

NOTE: if you are serving your resources from a dedicated subdomain (as you should)
you must set the url path (with `set_url_path`) to include the host and port. (eg.,
"http://res.your-domain.com/resources"), so that script tags and such resolve
correctly.
"""
import os
from os import path
from os.path import normpath
from tempfile import mkdtemp
from shutil import copytree, rmtree
from hashlib import md5

_fp = mkdtemp()
def get_file_path():
    """ Returns the path to (the directory) where resource files are stored. The
    path will have no trailing slash. """
    return _fp

def change_file_path(dst):
    """ Sets the resource file storage to the new value ``dst``. Note that this 
    involves copying the old directory to preserve resource state. """
    global _fp
    dst = normpath(dst)
    rmtree(dst, ignore_errors=True)
    copytree(_fp, dst)
    rmtree(_fp, ignore_errors=True)
    _fp = dst

_up = '/resources'
def get_url_path():
    """ Returns the URL base path where consumers should expect to download the
    resource files managed here (for example, if you call 
    ``put_string('foo', 'bar')``, and ``get_url_path()`` gives ``'/resources'``,
    a ``GET /resources/foo`` should respond with "bar".

    The returned string will be rooted but have no trailing slash. Defaults to
    "/resources".
    """
    return _up

def set_url_path(new_path):
    """ Sets the URL path used for obtaining resources (returned by
    ``get_url_path``). Call this with caution, and preferably only at app
    startup, since any existing resource links that have been sent out (think
    ``script`` and ``link`` tags) will be invalidated if the path is modified.
    """
    global _up
    if new_path.endswith('/'): new_path = new_path[:-1]
    _up = new_path

def put_string(name, data):
    """ Hosts the resource string ``data`` under ``name``. """
    with open(path.join(get_file_path(), name), 'w') as f: f.write(data)

_appendables = {} # { str: md5 }

def get_appendable_file_name(name, ignore_errors=False):
    try: return path.join(get_file_path(), 
                          _appendables[name].hexdigest() + '__' + name)
    except KeyError as e:
        if ignore_errors: return None
        else: raise e

# TODO: unify "strings" and "appendables"?

def create_appendable(name):
    """ Creates a resource for the app to repeatedly append data to. As this
    resource is updated, so is an MD5 hash. The resource is actually hosted under
    the name given prefixed with "<HASH>__" where HASH is the current MD5 of its
    contents (this allows you to aggressively browser cache your resources while
    notifying of updates in a cross-browser way (read: cache-busting)).
    
    See `add_to_appendable` to modify it, and `get_url` to conveniently generate 
    resource URLs. """
    existing = get_appendable_file_name(name, ignore_errors=True)
    if existing: os.remove(existing)
    _appendables[name] = md5()

def add_to_appendable(name, data):
    """ Appends data to the resource and updates its MD5 hash """
    existing = get_appendable_file_name(name)
    # TODO: phased/"transacted" update?
    with open(existing, 'a') as f: f.write(data)
    _appendables[name].update(data)
    new = get_appendable_file_name(name)
    os.rename(existing, new)

def get_url(name):
    """ Returns the URL (path) corresponding to the named resource. Works for 
    resources created both with `put_string` and `create_appendable`. """
    apndhash = _appendables.get(name)
    return get_url_path() + '/' + (name if not apndhash 
                                   else apndhash.hexdigest() + '__' + name)
