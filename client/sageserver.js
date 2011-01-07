
function SageServer(host, onopen, onclose) {
    if (!("WebSocket" in window)) {
        alert("Websockets not supported in this browser - use chrome.");
        return;
    }
    this.host = host;
    this._onopen = onopen;
    this._onclose = onclose;
    this._last_id = 0;
    this._callbacks = {};
    this.connect();
}

SageServer.prototype = {
    connect: function () {
        this._socket = new WebSocket('ws://' + this.host + '/');
        this._socket.onopen = $.proxy(this.onopen, this);
        this._socket.onclose = $.proxy(this.onclose, this);
        this._socket.onerror = $.proxy(this.onerror, this);
        this._socket.onmessage = $.proxy(this.onmessage, this);
    },
    onopen: function (event) {
        //console.log("onopen:", event);
        if (this._ctimer) {
            this._ctimer.destroy();
            delete this._ctimer;
        }
        if (this._onopen) {
	    this._onopen(this);
	}
    },
    onclose: function (event) {
        //console.log("onclose:", event);
        if (!this._ctimer) {
            this._ctimer = new Reconnector(this);
            $('#errors').append(this._ctimer.ui());
            this._ctimer.start();
            if (this._onclose) {
                this._onclose(this);
            }
	    this._send_disconnects();
        } else {
            this._ctimer.trynow_failed();
        }
    },
    _send_disconnects: function () {
	var id, cbk;
	for (id in this._callbacks) {
	    cbk = this._callbacks[id];
	    cbk.callback({
		    type: "Disconnect"
	    }, cbk.data);
	    delete this._callbacks[id];
	}
    },
    onerror: function (event) {
        //console.log("onerror:", event);
    },
    onmessage: function (event) {
        //console.log("onmessage:", event);
	var m;
	try {
	    m = JSON.parse(event.data);
	} catch (e) {
	    console.log("Invalid message received:", event.data);
	    console.log(e);
	    return;
	}
	var id = m.id;
	if (id === undefined) {
	    // shutdown message?
	    console.log("message without id:", m);
	    return;
	}
	var cbk = this._callbacks[id];
	if (cbk === undefined) {
	    console.log('no callback for m.id?', m);
	    return;
	}
	if (cbk.callback(m, cbk.data) === false) {
	    //console.log("callback removed:", m);
	    delete this._callbacks[id];
	}
    },
    send: function (msg, callback, data) {
	/**
	 * Sends msg with a unique id and calls callback when messages with the
	 * same id are received.
	 *
	 * :param msg: an object with "type" as the classname of the message
	 *     and any other members being the keyword arguments for the
	 *     message.
	 * :param callback: (msg, data) returning false if there
	 *     are no more messages to be received (i.e. after a Done).
	 *     Note: if the server is lost, then the callback will be called
	 *     with a Disconnected message.
	 * :returns: the id of the sent object.
	 */
	id = this._last_id + 1;
	msg.id = id;
	if (callback) {
	    this._callbacks[id] = {
		callback: callback,
		data: data
	    };
	}
	this._last_id = id;
	// console.log("sending:", msg)
	this._socket.send(JSON.stringify(msg));
	return id;
    }
};

function Reconnector(server) {
    this._server = server;
    this._left = 2;
    this._backoff = 2;
    this._interval = 0;
}

Reconnector.prototype = {
    ui: function () {
        this._error = $('\
<span>Could not connect to sage server (' + this._server.host + ').\
  Trying again <span class="disp">in 2s</span>... \
  <a href="#trynow">Try Now</a>\
</span><br />');
        this._disp = this._error.find('.disp')[0];
        this._error.find('a').click($.proxy(this.trynow, this));
        return this._error;
    },
    start: function () {
        this._interval = setInterval($.proxy(this._seconds_counter, this), 1000);
    },
    stop: function () {
        clearInterval(this._interval);
    },
    _seconds_counter: function () {
        this._left -= 1;
        if (this._left <= 0) {
            if (this._backoff < 200) {
                this._backoff = Math.round(this._backoff * 1.75);
            }
            this.trynow();
        } else {
            this._update_disp();
        }
    },
    _update_disp: function () {
        this._disp.innerHTML = 'in ' + this._left + 's';
    },
    trynow: function () {
        this._disp.innerHTML = 'now';
        this.stop();
        this._server.connect();
        return false;
    },
    trynow_failed: function () {
        this._left = this._backoff;
        this._update_disp();
        this.start();
    },
    destroy: function () {
        this.stop();
        this._error.remove();
        delete this._disp;
        delete this._error;
    },
};
