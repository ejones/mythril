
from collections import namedtuple
from cgi import escape as html_escape

Attribute = namedtuple( 'Attribute', 'name,value' )


class Element( object ):
    name = ''

