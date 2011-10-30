/* Mythril JS library. Requires JSON. */
/*jslint indent: 4, nomen: true */
/*global window, document, alert, setTimeout */
(function (mythril) {
    "use strict";

    var widgets = {}, // { id: Widget }

        /** Adds an event listener for the named event. The "on" prefix must
        not be given */
        addListener = function (obj, name, callback) {
            if (obj.addEventListener) {
                obj.addEventListener(name, callback);
            } else {
                obj.attachEvent('on' + name, function () {
                    callback.call(this, window.event);
                });
            }
        },

        head = document.head || document.getElementsByTagName('head')[0],
        Class = function () {};

    /** Copy the properties of props over to obj */
    mythril.update = function (obj, props) {
        var k;
        for (k in props) {
            if (Object.prototype.hasOwnProperty.call(props, k)) {
                obj[k] = props[k];
            }
        }
    };

    /** Binds the `this` of a function to a constant value */
    if (!Function.prototype.bind) {
        Function.prototype.bind = function (context) {
            var fn = this; return function () { fn.apply(context, arguments); };
        };
    }

    /** Implements Class inheritance */
    Function.prototype.extend = function (methods) {
        var parent = this, Cctor = function () {},
            ctor = Object.prototype.hasOwnProperty.call(methods, 'constructor') ?
                    methods.constructor :
                    (methods.constructor = function () {
                        parent.apply(this, arguments);
                    });

        Cctor.prototype = parent.prototype;
        ctor.prototype = new Cctor();
        mythril.update(ctor.prototype, methods);
        return ctor;
    };

    mythril.update(mythril, {
        debug: false,

        /** If mythril.debug is true, sends a message to console, falling back on
        alerting. Remember to set mythril.debug to true in debug modes! */
        log: function () {
            if (!mythril.debug) { return; }
            if (window.console) {
                window.console.log.apply(window.console, arguments);
            } else {
                alert(Array.prototype.join.call(arguments));
            }
        },

        rpcToken: '', // prevents XSRF. Must set to a random string every page load
        _callbacks: [], // for script RPC

        /** Cross-Domain HTTP GET messaging using script tags. Takes a url and
        data (which will be serialized as JSON), and a success and error callback,
        as well as an optional timeout which defaults to 10000.  "complete" should
        take response data, "error" should take a status and status text, which
        will be -1 and "" on timeout. The url must not have a query string.

        In the GET query string parameters, the data is sent under the "data"
        key, the globally accessible names for the complete and error callbacks
        are sent under the "complete" and "error" keys respectively, and the
        `mythril.rpcToken` as "rpcToken". In the event of an error, the server
        *must* return a successful response which calls the error function
        (with a status code and text). */
        rpc: function (url, data, timeout, complete, error) {
            if (typeof timeout === 'function') {
                error = complete; complete = timeout; timeout = void 0;
            }
            if (timeout === void 0) { timeout = 10000; }

            var script = document.createElement('script'), cleanup,

                cidx = -1 + mythril._callbacks.push(function (data) {
                    if (script) { if (complete) { complete(data); } cleanup(); }
                }),

                eidx = -1 + mythril._callbacks.push(function (status, text) {
                    if (script) { if (error) { error(status, text); } cleanup(); }
                });

            cleanup = function () {
                head.removeChild(script);
                mythril._callbacks.splice(cidx, 2);
                script = complete = error = void 0;
            };

            if (timeout !== null) {
                setTimeout(function () {
                    if (script) { if (error) { error(-1, ''); } cleanup(); }
                }, timeout);
            }

            script.type = 'text/javascript';
            script.src = url + '?data=' + encodeURIComponent(JSON.stringify(data)) +
                '&complete=mythril._callbacks[' + cidx + ']' +
                '&error=mythril._callbacks[' + eidx + ']' +
                '&rpcToken=' + encodeURIComponent(mythril.rpcToken);
            head.insertBefore(script, head.firstChild);
        },

        /** Create an instance of the given widget class and associate it with
        the element with the given id. Takes as well a data object, host (RPC) URL,
        and an object, "links", identifying the UIDs of other related widgets. The
        element, data, url, and links object are passed to the widget constructor. */
        create: function (WidgetClass, id, data, hostURL, links) {
            var elem = document.all ? document.all[id] : document.getElementById(id),
                existing = widgets[id];
            if (hostURL.substring(hostURL.length - 1) === '/') {
                hostURL = hostURL.substring(0, hostURL.length - 1);
            }
            if (existing) { existing._destroy(); }
            widgets[id] = new WidgetClass(elem, data, hostURL, links);
        },

        /** General widget class. Manages behavior for HTML elements and in concert
        with other widgets. It is intended to support seamless RPC with the server
        as well as communication with other widgets; typically the server side 
        library will generate sub-classes of `Widget` with auto-generated 
        methods which invoke the RPC calls you've defined on the server or find
        in the DOM the related widgets you've defined in the server-side generation
        of the HTML. See the server-side code for more details.

        Don't call the constructor directly, preferring to use `mythril.create`. See
        the documentation there for constructing widgets */
        Widget: Class.extend({

            constructor: function (elem, data, hostURL, links) {
                this.container = elem;
                this.hostURL = hostURL;
                this._links = links;
                this.init(data);
            },

            // cleanup
            _destroy: function () {
                this.destroy();
                this.container = void 0;
            },

            /** To be overridden. Receives the data passed in on creation. */
            init: function () {},

            /** To be overridden. Called whenever an RPC method errs, so that
            you don't have to provide an error handler on every RPC method call.
            Receives the method name, the data provided, the status code, 
            and text */
            onerror: function () {},

            /** To be overridden. Called usually just before this Widget is
            replaced on the page, esp. to allow you to sever any links to 
            DOM objects to prevent GC cycles in IE */
            destroy: function () {},

            /** Listens for the event "name" in its container (or any of its
            child elements etc. thanks to bubbling). Unlike regular DOM event
            handlers, "callback", has `this` bound to the current `Widget`
            instance, allowing for fun and profit */
            listen: function (name, callback) {
                addListener(this.container, name, callback.bind(this));
            },

            /** Internal. Used in generated properties which obtain related
            widgets */
            _getLink: function (name) { return widgets[this._links[name]]; },

            /** Internal. Used in generated properties which obtain child
            elements */
            _getElem: function (name) {
                return document.all ? document.all[this._links[name]] :
                        document.getElementById(this._links[name]);
            },

            /** Internal. Used in generated properties which do RPC. */
            _rpc: function (methodName, data, complete, error) {
                var that = this;

                function oncomplete(data) {
                    if (that.container) { complete.call(that, data); }
                }

                function onerror(status, statusText) {
                    if (that.container) {
                        if (error) {
                            error.call(that, status, statusText);
                        } else {
                            that.onerror(methodName, data, status, statusText);
                        }
                    }
                }

                mythril.rpc(this.hostURL + '/' + methodName, data,
                            oncomplete, onerror);
            }

        })

    });

}(window.mythril = {}));
