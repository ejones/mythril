"""
Defines the `Component` (base) class, which you can can use to create "View
classes" - logical units of HTML and CSS. It also automates linking up a
JavaScript class to manage the behaviour of the HTML elements it defines, and
linking up RPC methods between the Python and JavaScript sides of the class.
"""
# TODO: document all the customization points / low-level details *urgh*
# TODO: need examples

from uuid import uuid4
from hashlib import md5

from mythril import css

# A kind of "forward define"
Component = None

class ComponentMeta(type):
    def __init__(cls, name, bases, attrs):
        cls.js_class = name
        
        comcls = Component or cls
        cssfrag = css.dumps(cls.css) if cls.css else ''
        comcls.css_md5.update(cssfrag)



class Component(object):
    """
    Base class for defining logical units of HTML, CSS & JS. Define a class
    attribute ``css`` to attach style information, and define a (parameterless)
    method ``html`` to specify how the ``Component`` is rendered.  ``css``
    should hold a something serializable by `mythril.css.dumps`, and the
    ``html`` method must return an HTML element; the modules `mythril.css` and
    `mythril.html` contain the helper classes representing CSS styles and HTML
    elements for this purpose. Importantly, ``Component``s are directly
    serializable by `mythril.html.dumps`, so you can render other components
    recursively (mixed together with HTML and so on). Each Component is given
    a unique id, which is transferred to the ``html`` (return) value as its "id"
    attribute.

    The CSS for all of your components is compiled into a single CSS file that
    you can then include on the page (this could be extended to support
    multiple CSS files, but this is optimal for 99.99% of websites). This file
    is stored in `mythril.css.resource_file_path` and accessible from
    `mythril.css.resource_url_path` (remember to configure these) as
    component_<...>.css where <...> is an MD5 hash for cache-busting goodness.
    See this module's use `Component.css_file_name` to get the current name.
    
    For each ``Component`` class, you can define a corresponding JavaScript
    class (in fact, deriving from the ``Component`` JS class in the JS file
    "mythril.js" in this package). By default, it should have the same name as
    the Python class and be exposed in the global ``window`` scope.  If so, the
    JavaScript class is instantiated for every use of the ``Component`` on the
    page/AJAX response/etc., and is given the HTML element representing the
    HTML part of the ``Component``. So it is able to organize the behaviours for
    the HTML, and there are helpers in the JS ``Component`` class for this 
    purpose, including jQuery integration.

    Finally, your ``Component`` class can define RPC methods. That is, for each
    RPC method on the (Python) ``Component`` class, there will be defined a
    method on the JavaScript class which will RPC (ie., AJAX) that method. In 
    addition to wrapping up the AJAX, it includes protections for XSRF and works
    cross-domain.
    """
    __metaclass__ = ComponentMeta
    css = None
    css_md5 = md5()

    def __init__(self, *args, **kwargs):
        self.id = u'_' + uuid4().hex
        self.init(*args, **kwargs)

    def init(self, *args, **kwargs): pass
    def html(self): pass

    def __html__(self, writer):
        elem = self.html()

