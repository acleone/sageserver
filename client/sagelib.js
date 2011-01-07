
function SageServer(host, worksheet) {
    if (!("WebSocket" in window)) {
        alert("Websockets not supported in this browser - use chrome.");
        return {};
    }
    this.host = host;
    this.worksheet = worksheet;
    this.connect();
}

SageServer.prototype = {
    connect: function () {
        this.socket = new WebSocket('ws://' + this.host + '/');
        this.socket.onopen = $.proxy(this.onopen, this);
        this.socket.onclose = $.proxy(this.onclose, this);
        this.socket.onerror = $.proxy(this.onerror, this);
        this.socket.onmessage = $.proxy(this.onmessage, this);
    },
    onopen: function (event) {
        console.log("onopen:", event);
        if (this.ctimer) {
            this.ctimer.stop();
            this.cerror.remove();
            delete this.ctimer;
            delete this.cerror;
        }
            
    },
    onclose: function (event) {
        console.log("onclose:", event);
        if (!this.ctimer) {
            this.cerror = $('\
<span>Could not connect to sage server (' + this.host + ').\
  Trying again <span class="disp">in 2s</span>... \
  <a href="#trynow">Try Now</a>\
</span><br />');
            var self = this;
            this.ctimer = {
                disp: this.cerror.find('.disp'),
                left: 2,
                backoff: 2,
                interval: 0,
                start: function () {
                    self.ctimer.interval = setInterval(self.ctimer.int_func, 1000);
                },
                stop: function () {
                    clearInterval(self.ctimer.interval);
                },
                int_func: function () {
                    self.ctimer.left -= 1;
                    if (self.ctimer.left <= 0) {
                        if (self.ctimer.backoff < 200) {
                            self.ctimer.backoff *= 2;
                        }
                        self.ctimer.trynow();
                    } else {
                        self.ctimer.update_disp();
                    }
                },
                update_disp: function () {
                    self.ctimer.disp.text('in ' + self.ctimer.left + 's');
                },
                trynow: function () {
                    self.ctimer.disp.text('now');
                    self.ctimer.stop();
                    self.connect();
                    return false;
                },
            };
            this.ctimer.start();
            this.cerror.find('a').click(this.ctimer.trynow);
            $('#errors').append(this.cerror);
        } else { // trynow failed.
            this.ctimer.left = this.ctimer.backoff;
            this.ctimer.update_disp();
            this.ctimer.start();
        }
    },
    onerror: function (event) {
        console.log("onerror:", event);
    },
    onmessage: function (event) {
        console.log("onmessage:", event);
    },
};

function SageLocalStorage(id, worksheet) {
    if (!("localStorage" in window)) {
        alert("localStorage not supported in this browser - use chrome.");
        return {};
    }
    this.id = id;
    this.worksheet = worksheet;
    this.store = localStorage;
}

SageLocalStorage.prototype = {
    is_new: function () {
        return this.store.getItem(this.id) === null;
    },
};
