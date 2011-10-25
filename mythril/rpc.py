"""
Enables classes to seamlessly communicate with JavaScript versions of themselves.
To activate classes for RPC, see `register`. You will need to serve the RPCs; the
function `app` is a valid wsgi application for this purpose.
"""
_index = {}

def register(cls): pass
