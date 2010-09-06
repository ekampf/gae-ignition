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
import traceback

import webob
import webob.exc
from wsgiref.handlers import CGIHandler

__version__ = "0.1"
__version_info__ = tuple(int(n) for n in __version__.split('.'))

default_config = {

}

# Allowed request methods.
ALLOWED_METHODS = frozenset(['DELETE', 'GET', 'HEAD', 'OPTIONS', 'POST', 'PUT', 'TRACE'])

class IgnitionException(Exception):
    pass

class Request(webob.Request):
    pass

class Response(webob.Response):
    pass

class Config(dict):
    pass

class Ignition(object):
    """The Ignition main WSGI application"""

    #: Default class for requests.
    request_class = Request
    #: Default class for responses.
    response_class = Response
    #: The active :class:`Ignition` instance.
    instance = None
    #: The active :class:`Request` instance.
    request = None

    def __init__(self, config=None, debug=False):
        self.set_instance()

        self.debug = debug
        self.routes = []

    def __call__(self, environ, start_response):
        return self.wsgi_app(environ, start_response)

    def wsgi_app(self, environ, start_response):
        environ['ignition.app'] = self

        cleanup = True
        try:
            # Set the currently active request so that it can be accessed via Ignition.request
            request = self.request_class(environ)
            self.set_request(request)

             # Make sure that the requested method is allowed in App Engine.
            if request.method not in ALLOWED_METHODS:
                self.halt(code=501) # raise webob.exec.HTTPNotImplemented()

            matched_route = self.match_route(request)
            if not matched_route:
                self.halt(code=404)

            # TODO: Pre-dispatch filters

            result = matched_route.dispatch(request)
            response = self.make_response(request, result)

            # TODO: Post-dispatch filters

            return response(environ, start_response)

        except webob.exc.WSGIHTTPException, ex:
            cleanup = False # TODO: should only happen on development
            return ex(environ, start_response)
        except Exception, e:
            cleanup = False # TODO: should only happen on development
            response = self.handle_exception(request, e)
            response = self.make_response(request, response)
        finally:
            if cleanup:
                self.cleanup()

    def match_route(self, request):
        for r in self.routes:
            if r.match(request.path, request.method):
                return r

        return None

    def make_response(self, request, result):
        if isinstance(result, self.response_class):
            return result

        if isinstance(result, basestring):
            return self.response_class(result)

        if isinstance(result, tuple):
            return self.response_class(*result)

        if result is None:
            raise ValueError('Handler did not return a response.')

    def handle_exception(self, request, ex):
        """Handles HTTPException or uncaught exceptions raised by the WSGI
        application, optionally applying exception middleware.

        :param request:
            A :class:`Request` instance.
        :param ex:
            The catched exception.
        :return:
            A :class:`Response` instance, if the exception is not raised.
        """
        logging.exception("Unhandled exception")

        # TODO: Implement

        # Execute handle_exception middleware.
        #for hook in self.middleware.get('handle_exception', []):
        #    response = hook(e)
        #    if response is not None:
        #        return response


        #if self.dev:
        #    raise


        lines = ''.join(traceback.format_exception(*sys.exc_info()))
        return webob.exc.HTTPInternalServerError(detail='%s' % lines)

    def halt(self, code=None, explanation=None, headers=None):
        exception_classes = {
            # Client errors
            400 : webob.exc.HTTPBadRequest,
            401 : webob.exc.HTTPUnauthorized,
            402 : webob.exc.HTTPPaymentRequired,
            403 : webob.exc.HTTPForbidden,
            404 : webob.exc.HTTPNotFound,
            405 : webob.exc.HTTPMethodNotAllowed,
            406 : webob.exc.HTTPNotAcceptable,
            407 : webob.exc.HTTPProxyAuthenticationRequired,
            408 : webob.exc.HTTPRequestTimeout,
            409 : webob.exc.HTTPConflict,
            410 : webob.exc.HTTPGone,
            411 : webob.exc.HTTPLengthRequired,
            412 : webob.exc.HTTPPreconditionFailed,
            413 : webob.exc.HTTPRequestEntityTooLarge,
            414 : webob.exc.HTTPRequestURITooLong,
            415 : webob.exc.HTTPUnsupportedMediaType,
            416 : webob.exc.HTTPRequestRangeNotSatisfiable,
            417 : webob.exc.HTTPExpectationFailed,
            
            # Server errors
            500 : webob.exc.HTTPInternalServerError,
            501 : webob.exc.HTTPNotImplemented,
            502 : webob.exc.HTTPBadGateway,
            503 : webob.exc.HTTPServiceUnavailable,
            504 : webob.exc.HTTPGatewayTimeout,
            505 : webob.exc.HTTPVersionNotSupported,
        }

        ex_cls = exception_classes.get(code, webob.exc.WSGIHTTPException)

        ex = ex_cls()
        if explanation:
            ex.explanation = explanation

        if headers:
            ex.headerlist = headers

        raise ex


    def route(self, url, func, method):
        """Attaches a view function to a url or a list of urls"""

        if url is None:
            url = '/' + func.__name__ + '/'

        if type(url) == str:
            self.routes.append(Route(url, func, method))
        else:
            for u in url:
                self.routes.append(Route(u, func, method))

    def run(self):
        CGIHandler().run(self)

    def set_instance(self):
        if not Ignition.instance == None :
            raise RuntimeError, 'Only one instance of TestSingleton is allowed!'
        Ignition.instance = self

    def set_request(self, request):
        """Sets the currently active :class:`Request` instance.

        :param request:
            The currently active :class:`Request` instance.
        """
        Ignition.request = request

    def cleanup(self):
        """Cleans :class:`Ignition` variables at the end of a request."""
        Ignition.request = None


class Route(object):
    url_syntax = re.compile(r'''\{(\w+)(?::([^}]+))?\}''', re.VERBOSE)

    def __init__(self, url, func, method):
        # url has to begin and end with '/'
        if url[0] != '/': url = '/' + url
        if url[-1] != '/': url += '/'
        self.str_url = url

        # Convert the uri to a regular expression
        regex = Route.template_to_regex(url)

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
        return '<Route: %s %s - %s()>' % (self.method, self.str_url, self.func.__name__)

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

def init(config=None):
    """Sets up the global Ignition singleton variable"""
    if Ignition.instance is None:
        # Create a new instance of Ignition if it wasnt already created
        app = Ignition(config)

    return Ignition.instance

def run():
    if Ignition.instance is None:
        init()

    Ignition.instance.run()


# Decorators to add routing semantics to view functions
#########################################################

def route(url=None, method='*'):
    if Ignition.instance is None:
        init()

    def wrap(f):
        Ignition.instance.route(url, f, method)

    return wrap

def post(url=None):   return route(url, 'post')
def get(url=None):    return route(url, 'get')
def head(url=None):   return route(url, 'head')
def put(url=None):    return route(url, 'put')
def delete(url=None): return route(url, 'delete')

# Misc. Helpers
#########################################################

def halt(code=None, explanation=None, header=None):
    Ignition.instance.jalt(code, explanation=explanation, header=header)

def content_type(content_type):
    def decorator(view_function):
        def wrapper(*args, **kwargs):
            result = view_function(*args, **kwargs)

            if isinstance(result, basestring):
                response = Ignition.response_class()
                response.content_type = content_type
                response.body = result
                return response

            if isinstance(result, Ignition.response_class):
                result.content_type = content_type
                return result

            # If view didn't return a string then we have nothing to do here
            return result

        return wrapper
    return decorator


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