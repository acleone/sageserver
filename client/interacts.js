function get_interact(node) {
    return $(node).closest('.interact').data('interact');
}

function Interact(cell, opts) {
    /**
     * opts -- object sent from interacts.py
     */
    this._cell = cell;
    this._server = get_worksheet(cell).server;
    this._opts = opts;
    this.jdiv = null;
    this._update_timer = null;
}

var InteractEvents = {
    click_update: function (event) {
	/**
	 * this -- update <button>
	 * event.data -- the Interact.
	 */
	var interact = event.data;
	interact.eval();
    }
};

Interact.prototype = {
    ui: function () {
	this.jdiv = $('\
<div class="interact">\
  <div class="controls"></div>\
  <div class="update_button">\
    <button>Update</button>\
  </div>\
  <div class="output"></div>\
</div>').addClass((this._opts.update_timeout === null)? 'manual': 'timeout')
	.data('interact', this);
	this.jdiv.find('button').bind('click', this,
				       InteractEvents.click_update);
	this._jcontrols = this.jdiv.find('.controls');
	this._controls = [];
	var i, control_obj, control, len = this._opts.controls.length;
	for (i = 0; i < len; i += 1) {
	    control_obj = this._opts.controls[i];
	    control = new interacts[control_obj.js_class](this, control_obj);
	    this._controls[i] = control;
	    this._jcontrols.append(control.ui());
	}
	return this.jdiv;
    },
    after_attached: function () {
	var i, len = this._controls.length;
	for (i = 0; i < len; i += 1) {
	    this._controls[i].after_attached();
	}
    },
    onchange: function () {
	/**
	 * Called by any controls when they change.
	 */
	if (this._opts.update_timeout !== null) {
	    if (this._update_timer !== null) {
		clearTimeout(this._update_timer);
	    }
	    this._update_timer = setTimeout(
		    $.proxy(this, this.on_update_timeout),
		    this._opts.update_timeout);
	}
    },

    on_update_timeout: function () {
	this._update_timer = null;
	this.eval();
    },

    eval: function (event) {
	var i, vals = [];
	for (i = 0; i < this._controls.length; i += 1) {
	    vals[i] = this._controls[i].val();
	}
	var id = this._server.send({
	    type: 'ExecInteract',
	    dict: {
		id: this._opts.id,
		vals: vals
	    }
	});
    }

};

function InputBox(interact, opts) {
    this._interact = interact;
    this._opts = opts;
}

var InputBoxEvents = {
    onchange: function (event) {
	/**
	 * this -- <input>
	 * event.data -- this InputBox.
	 */
	var self = event.data;
	self._interact.onchange();
    }
};

InputBox.prototype = {
    ui: function () {
	this.jdiv = $('\
<div class="control">\
  <span class="label"></span>\
  <input type="text" size="40" value="" />\
</div>').data('control', this)
	.find('.label')
	    .text(this._opts.label)
	.end();
	this._input = this.jdiv.find('input')
	    .attr('size', this._opts.width)
	    .val(this._opts['default'])
	    .bind('change', this, InputBoxEvents.onchange);
	return this.jdiv;
    },
    after_attached: function () {

    },
    val: function () {
	return this._input.val();
    }
};

var interacts = {
    InputBox: InputBox
};