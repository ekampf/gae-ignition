# -*- coding: utf-8 -*-
"""
    Ignition
    ========
"""

import logging
import re
import os
import sys
import warnings

import webob
from wsgiref.handlers import CGIHandler

__version__ = "0.1"
__version_info__ = tuple(int(n) for n in __version__.split('.'))

default_config = {

}

# Allowed request methods.
ALLOWED_METHODS = frozenset(['DELETE', 'GET', 'HEAD', 'OPTIONS', 'POST', 'PUT', 'TRACE'])

class IgnitionException(Exception):
    pass





class Config(dict):
    pass

class Ignition(object):
    """The Ignition main WSGI application"""

    def __init__(self, config=None, debug=False):
        global _ignition
        if _ignition is not None:
            logging.warning("There's already an Ignition global object created! creating another might cause weird behavior")
        else:
            _ignition = self

        self.debug = debug
        self.routes = []

    def __call__(self, environ, start_response):
        return self.wsgi_app(environ, start_response)

    def wsgi_app(self, environ, start_response):
        environ['ignition.app'] = self

        request = webob.Request(environ)
        response = webob.Response(request=request, conditional_response=True)

        if request.method not in ALLOWED_METHODS:
            #abort(501)
            pass

        try:
            route = self.match_route(request)
            if not route:
                logging.error("404")
                pass


            result = route.dispatch(request)

            response.content_type = 'text/plain'
            response.body_file.write(result)
            return response(environ, start_response)

        except Exception, e:
            logging.exception("Failure")

    def match_route(self, request):
        for r in self.routes:
            if r.match(request.path, request.method):
                return r

        return None

    def route(self, url, func, method):
        """Attaches a view function to a url or a list of urls"""

        if url is None:
            url = '/' + func.__name__ + '/'

        if type(url) == str:
            self.routes.append(IgnitionRoute(url, func, method))
        else:
            for u in url:
                self.routes.append(IgnitionRoute(u, func, method))

    def run(self):
        CGIHandler().run(self)

class IgnitionRoute(object):
    url_syntax = re.compile(r'''\{(\w+)(?::([^}]+))?\}''', re.VERBOSE)

    def __init__(self, url, func, method):
        # url has to begin and end with '/'
        if url[0] != '/': url = '/' + url
        if url[-1] != '/': url += '/'
        self.str_url = url

        # Convert the uri to a regular expression
        regex = IgnitionRoute.template_to_regex(url)

        self.url = re.compile(regex)
        self.func = func
        self.method = method.upper()
        self.params = {}


    def match(self, request_uri, method):
        """Matches a given request uri to this route object"""
        result = self.url.match(request_uri)
        if result is None:
            return False

        # URIs match. Make sure request method matches too...
        if self.method != '*' and self.method != method:
            return False

        self.params.update(result.groupdict())
        return True

    def dispatch(self, request):
        """Call the route's view with any named parameters."""
        return self.func(request, **self.params)

    def __repr__(self):
        return '<IgnitionRoute: %s %s - %s()>' % (self.method, self.str_url, self.func.__name__)

    @classmethod
    def template_to_regex(cls, template):
        """Converts a uri template string into a python regular expression

        Borrowed from http://pythonpaste.org/webob/do-it-yourself.html#routing

        Examples:

        >>> print IgnitionRoute.template_to_regex('/a/static/path')
        ^\/a\/static\/path$
        >>> print IgnitionRoute.template_to_regex('/{year:\d\d\d\d}/{month:\d\d}/{slug}')
        ^\/(?P<year>\d\d\d\d)\/(?P<month>\d\d)\/(?P<slug>[^/]+)$
        """
        regex = ''
        last_pos = 0
        for match in cls.url_syntax.finditer(template):
            regex += re.escape(template[last_pos:match.start()])
            var_name = match.group(1)
            expr = match.group(2) or '[^/]+'
            expr = '(?P<%s>%s)' % (var_name, expr)
            regex += expr
            last_pos = match.end()
        regex += re.escape(template[last_pos:])
        regex = '^%s$' % regex
        return regex

# Functions that handle the global Ignition singleton
#########################################################

_ignition = None

def init(config=None):
    """Sets up the global Ignition singleton variable"""
    global _ignition
    if _ignition is None:
        # Create a new instance of Ignition if it wasnt already created
        _ignition = Ignition(config)

    return _ignition

def run():
    if _ignition is None:
        init()

    _ignition.run()


# Decorators to add routing semantics to view functions
#########################################################

def route(url=None, method='*'):
    global _ignition
    if _ignition is None:
        init()

    def wrap(f):
        _ignition.route(url, f, method)

    return wrap

def post(url=None):   return route(url, 'post')
def get(url=None):    return route(url, 'get')
def head(url=None):   return route(url, 'head')
def put(url=None):    return route(url, 'put')
def delete(url=None): return route(url, 'delete')



def make_wsgi_app(config=None, **kwargs):
    """Returns an instance of :class:'Ignition'.

    :param config:
        A dictionary of configuration values.
    :param kwargs:
        Additional keyword arguments to instantiate :class:`Tipfy`.
    :returns:
        A :class:`Ignition` instance.
    """

    app = Ignition(config=config, **kwargs)

    if app.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # Execute post_make_app middlewaes
    #for hook in app.middleware.get('post_make_app', []):
    #    app = hook(app)

    return app

if __name__ == "__main__":
    import doctest
    doctest.testmod()