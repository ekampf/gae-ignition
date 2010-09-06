# Welcome to GAE-Ignition!

## Summary

Ignite your Google AppEngine project with GAE-Ignition.
Ignition is a small but powerful web framework inspired by Ruby's Sinatra and developed specifically
for use with Google AppEngine.

Useful Links:

* [Documentation](http://github.com/ekampf/gae-ignition/wiki/Documentation)

## Igniting your App Engine App

Simple hello world:

    from ignition import *

    @route('/')
    def index(request):
        "Hello World!"

    run()

## Changelog
