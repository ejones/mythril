(function(mythril) {
    var slice = Array.prototype.slice, 
        hasOwnProperty = Object.prototype.hasOwnProperty,
        noop = function(){},

        requestsIE: window.ActiveXObject ? void 0 : [], // of XMLHttpRequests
        widgets: {}, // { id: Widget }

        /** Copy the properties of props over to obj */
        merge = function(obj, props) {
            for (k in props) if (hasOwnProperty.call(props, k)) obj[k] = props[k];
        },
        
        /** Adds an event listener for the named event. The "on" prefix must
        not be given */
        addListener = function(obj, name, callback) {
            if (obj.addEventListener) obj.addEventListener(name, callback);
            else obj.attachEvent('on' + name, function() { 
                    callback.call(this, window.event);
                 });
        },

        /** Turns an object into urlencoded params */
        urlSerialize = function(obj) {
            var fst = true, ret = '', k;
            for (k in obj) if (hasOwnProperty.call(obj, k)) {
                if (fst) fst = false; else ret += '&';
                ret += encodeURIComponent(k) + '=' + encodeURIComponent(obj[k]);
            }
            return ret;
        },

        /** Turns a urlencoded string into a Prince */
        urlUnserialize = function(str) {
            var pairs = str.split('&'), i, kvp, ret = {};
            for (i = 0; i < pairs.length; i++) {
                kvp = pairs[i].split('=');
                ret[decodeURIComponent(kvp[0])] = decodeURIComponent(kvp[1]);
            }
            return ret;
        },

        SameDomainHost, CrossDomainHost; // for RPC

    /** Binds the `this` of a function to a constant value */
    if (!Function.prototype.bind) Function.prototype.bind = function( context ) {
        var fn = this; return function() { fn.apply( context, arguments ); };
    }

    /** Implements Class inheritance */
    Function.prototype.extend = function( methods ) {
        var parent = this, cctor = function() {}, k,
        ctor = hasOwnProperty.call( methods, 'constructor' ) ? methods.constructor :
            (methods.constructor = function() { parent.apply( this, arguments ); });

        cctor.prototype = parent.prototype;
        ctor.prototype = new cctor;
        merge(ctor.prototype, methods);
        return ctor;
    }

    merge(mythril, {
        debug: false,
        rpcToken: '', // prevents XSRF. should be set to some shared secret by the host

        /** If mythril.debug is true, sends a message to console, falling back on
        alerting. Remember to set mythril.debug to true in debug modes! */
        log: function(/* args... */) {
            if (!mythril.debug) return;
            try { console.log.apply(console, arguments); }
            catch (exn) { alert(Array.prototype.join.call(arguments)); }
        },

        /** Same-domain HTTP POST implementation using XHRs. Takes a url and
        the parameters, which will be serialized as POST variables, and a callback.
        The "complete" callback should take the response text. The "error" callback
        should take the status code and status text, which will both be -1 and an
        empty string, respectively, in case of timeout or network error. An optional 
        timeout, in milliseconds, defaults to 10000.

        Params are not optional. It must either be a x-www-form-urlencoded string or
        an object, with values being primitive values (Strings and Numbers) */
        post: function(url, params, timeout, complete, error) {
            var xhr, xhrIdx, 
                bodyText = typeof params == 'string' ? bodyText : urlSerialize(params);
            
            if (typeof timeout == 'function') { 
                error = complete; complete = timeout; timeout = void 0;
            }
            if (!timeout) timeout = 10000;
    
            try { xhr = new XMLHttpRequest(); } catch (_) {}
            try { xhr = xhr || new ActiveXObject("Msxml2.XMLHTTP.6.0"); } catch (_) {}
            try { xhr = xhr || new ActiveXObject("Msxml2.XMLHTTP.3.0"); } catch (_) {}
            xhr = xhr || new ActiveXObject("Microsoft.XMLHTTP");
            
            xhr.open('POST', url, true);
            if (requestsIE) xhrIdx = requestsIE.push(xhr);

            xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
            xhr.setRequestHeader('Content-Length', bodyText.length);
            xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
            xhr.setRequestHeader('X-RPC-Token', mythril.rpcToken);
            xhr.send(bodyText);

            function onComplete(_, aborted) {
                var status = -1, statusText = '';
                
                if (!(aborted || xhr.readyState == 4)) return;
                xhr.onreadystatechange = noop;

                try { status = xhr.status; } catch (_) {}
                try { statusText = xhr.statusText; } catch (_) {}

                if (Math.floor(status/100) == 2) complete(xhr.responseText);
                else error(status, statusText);
                
                // cleanup for IE
                if (requestsIE) requestsIE.splice(xhrIdx, 1);
                xhr = complete = error = void 0;
            }

            if (xhr.readyState == 4) onComplete(); // completed synchronously
            else {
                xhr.onreadystatechange = onComplete;
                setTimeout(function() { onComplete(0, true); }, timeout);
            }
        },


        /** Create an instance of the given widget class and associate it with 
        the element with the given id and RPC host at "hostURL". The widget class 
        is expected to take the hostURL, element and initialization data in the 
        constructor. */
        create: function(widgetClass, id, data, hostURL) {
            elem = document.all ? document.all[id] : document.getElementById(id);
            widgets[id] = new widgetClass(elem, data, hostURL);
        },

        
    });
 
    // Cleans up lingering XHRs in IE
    if (requestsIE) {
        window.attachEvent('onunload', function() {
            for (var i = 0; i < requestsIE.length; i++) {
                requestsIE[i].onreadystatechange = noop;
                requestsIE[i].abort();
            }
        });
    }
       
    /** Implements an RPC Host for requests on the Same-Origin */
    SameDomainHost = (function(){}).extend({
        constructor: function(url) {
            this.url = url;
        },

        send: function(params, oncomplete, onerror) {
            mythril.post(this.url, params, oncomplete, onerror);
        }
    });

})(window.mythril = {});
