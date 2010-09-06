# -*- coding: utf-8 -*-
import os
import sys

if 'lib' not in sys.path:
    # Add /lib as primary libraries directory, with fallback to /distlib
    # and optionally to distlib loaded using zipimport.
    sys.path[0:0] = ['lib', 'distlib', 'distlib.zip']

# Is this the development server?
debug = os.environ.get('SERVER_SOFTWARE', '').startswith('Dev')

from ignition import *

@route('/')
def index(request):
    return 'App Engine Ignited!'

@get('/json')
@content_type('application/json')
def example_json(request):
    return '{ "value": 200, "message" : "Hello world!" }'

def main():
    run()

if __name__ == '__main__':
    main()