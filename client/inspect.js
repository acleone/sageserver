function Inspect(div, line_info) {
    /**
       this.div -- {jQuery element}
       this.cell -- {Cell Object}
       this.line_info -- see Cell.get_line_info()
       this.opened -- 'Completions', 'Doc', 'Source'
       this.loading -- boolean
     */
    this.div = $(div);
    this.cell = get_cell(this.div);
    this.cell.div.addClass('inspecting');
    this.line_info = line_info;
    var word = line_info.word;
    this.is_completion = true;
    if (word.slice(-1) === '?' || word.slice(-1) === '(') {
	this.is_completion = false;
	if (word.slice(-2) === '??') { // get source
	    this.get('Source', word.slice(0, -2));
	} else { // get doc
	    this.get('Doc', word.slice(0, -1));
	}
    } else { // completions
	this.get('Completions', word);
    }
}

Inspect.prototype = {

    get: function (type, word) {
	this.div.append($('\
<div class="' + type + '" style="display: block;">\
  <img src="computing.gif" alt="computing.gif" />\
  &nbsp; Getting ' + type + " for '" + word + "'...</div>").data('word', word));
	this.set_opened(type);
	this.loading = true;
	this.send_id = get_worksheet(this.cell).server.send({
	    type: 'Get' + type,
	    end_bytes: word
	}, this.recv, {
	    self: this,
	    type: type,
	    word: word
	});
    },

    recv: function (msg, data) {
	/**
	 * :param msg: Completions, Doc, Source or NotDone.
	 * :param data: {self: this, type:'Completions', etc, word: 'adsf'}
	 */
	var self = data.self;
	if (!self.div || msg.id != self.send_id) {
	    console.log("[inspect] Another request made?", msg, data);
	    return false;
	}
	if (msg.type === 'Disconnect') { // server lost
	    self.remove();
	    return false;
	}
	var d = self.div.children('.' + data.type);
	if (msg.type === 'No') {
	    d.html('No ' + data.type + " found for '" + data.word + "'");
	} else if (msg.type === 'Completions') {
	    var comps = JSON.parse(msg.end_bytes);
	    if (!comps.length) {
		d.html("No completions found for '" + data.word + "'");
		self.sel = false;
	    } else if (comps.length === 1) {
		self.sel = {
		    text: function () {
			return comps[0];
		    }
		};
		self.do_completion();
	    } else {
		self.build_completions_selector(comps, d);
	    }
	} else {
	    d.html(msg.end_bytes);
	}
	self.loading = false;
	return false;
    },

    set_opened: function (type) {
	if (this.opened) {
	    this.div.children('.' + this.opened).css('display', 'none');
	}
	this.opened = type;
	this.div.children('.' + type).css('display', 'block');
    },

    do_completion: function () {
	/** this -> Inspect object. */
	var li = this.line_info;
	var before_cursor = li.before + this.sel_text(true);
	var editor = this.cell.editor;
	editor.focus();
	editor.setLineContent(li.lineh, before_cursor + li.after);
	editor.selectLines(li.lineh, before_cursor.length);
	this.remove();
    },

    click_completions: function (event) {
	/**
	 * this -- td element
	 * event.data -- this Inspect object
	 */
	var self = event.data;
	self.set_sel(this);
	if (event.shiftKey) {
	    self.toggle();
	    self.cell.editor.focus();
	} else {
	    self.do_completion();
	}
	return false;
    },

    sel_text: function (without_paren) {
	/** Returns the text of the currently selected completion, with '('
	    removed from the end if without_paren is omitted. */
	var t = this.sel.text();
	if (!without_paren && t.slice(-1) === '(') {
	    return t.slice(0, -1);
	}
	return t;
    },

    set_sel: function (element) {
	if (this.sel) {
	    this.sel.removeClass('sel');
	}
	this.sel = $(element).addClass('sel');
    },

    handle_keydown: function (event) {
	/** this -> Inspect object. */
	if (Kb.inspect(event)) { // tab
	    this.toggle();
	    return true;
	} else if (this.opened === 'Completions' && this.sel) {
	    if (Kb.left(event)) {
		this.set_sel(this.move_left());
		return true;
	    } else if (Kb.up(event)) {
		this.set_sel(this.move_up());
		return true;
	    } else if (Kb.right(event)) {
		this.set_sel(this.move_right());
		return true;
	    } else if (Kb.down(event)) {
		this.set_sel(this.move_down());
		return true;
	    } else if (Kb.enter(event)) {
		this.do_completion();
		return true;
	    } else if (Kb.shift(event)) { // just shift key
		return true;
	    }
	}
    },

    toggle: function () {
	/** toggle between completions and docstring for completions or
	 * docstring and source */
	var c = this.div.children();
	if (this.is_completion) { // toggle between Completions/Doc
	    if (this.opened === 'Completions') {
		var t = this.sel_text();
		if (c.length === 1 || c.last().data('word') !== t) {
		    c.slice(1).remove();
		    this.get('Doc', t);
		} else { // we already have the Doc
		    this.set_opened('Doc');
		}
	    } else { // Doc for a completion currently visible
		this.set_opened('Completions');
	    }
	} else { // toggle between Doc/Source
	    if (c.length < 2) {
		this.get((this.opened === 'Doc')? 'Source': 'Doc',
			 c.first().data('word'));
	    } else {
		this.set_opened((this.opened === 'Doc')? 'Source' : 'Doc');
	    }
	}
    },

    move_left: function () {
	var ptd = this.sel.prev();
	if (ptd.length) {
	    return ptd[0];
	} // else { // we're at the first column, get last td of previous row
	var ptr = this.sel.parent().prev();
	if (ptr.length) {
	    return ptr.children().last()[0];
	} // else { // we're at the top-left, get bottom right
	return this.sel.parent().parent().children().last().children().last()[0];
	/*                        tbody              last tr       last td */
    },
    move_up: function () {
	var col = this.sel.index();
	var ptr = this.sel.parent().prev();
	if (ptr.length) {
	    return ptr.children().get(col);
	} // else { // we're at the top row, get the bottom row
	return this.sel.parent().parent().children().last().children().get(col);
	/*                        tbody             last tr       col td    */
    },

    move_right: function () {
	var ntd = this.sel.next();
	if (ntd.length) {
	    return ntd[0];
	} // else { // we're at the last column, get the first td of the next row
	var ntr = this.sel.parent().next();
	if (ntr.length) {
	    return ntr.children().first()[0];
	} // else { // we're at the bottom-right, get the top-left
	return this.sel.parent().parent().children().first().children().first()[0];
	/*                        tbody             first tr        first td  */
    },

    move_down: function () {
	var col = this.sel.index();
	var ntr = this.sel.parent().next();
	if (ntr.length) {
	    return ntr.children().get(col);
	} // else { // we're at the bottom row, get the top row
	return this.sel.parent().parent().children().first().children().get(col);
	/*                       tbody               first tr       col td    */
    },

    remove: function () {
	this.cell.div.removeClass('inspecting');
	this.div.empty();
	delete this.div;
	delete this.opened;
	delete this.cell.inspect;
	delete this.cell;
    },

    build_completions_selector: function (comps, div) {
	var max_w = div.width();
	var cols = Math.max(1, Math.floor(max_w / 100));
	var inc = null, w, t, last_t;
	while (true) {
	    if (inc === 1) {
		last_t = t;
	    }
	    t = this.build_comps_table(comps, cols);
	    div[0].innerHTML = t.html;
	    w = div.children().first().width();
	    /*                 <table> */
	    if (inc === null) {
		inc = (w > max_w)? -1 : 1;
	    }
	    if (inc === -1 && (cols === 1 || w < max_w)) {
		break;
	    } else if (inc === 1) {
		if (w <= max_w && t.rows === 1) {
		    break;
		} else if (w > max_w) {
		    // too many cols
		    t = last_t;
		    div[0].innerHTML = t.html;
		    cols -= 1;
		    break;
		}
	    }
	    cols += inc;
	}
	div.delegate('td', 'click', this, this.click_completions)
	   .append('\
<div class="completions_help">\
  click or enter to replace, shift+click or tab to see documentation\
</div>');
	this.set_sel(div.find('tr').first().children()[0]);
    },

    build_comps_table: function (comps, cols) {
	var rows = [];
	var i = 0, j, row, last_cols;
	while (true) {
	    row = [];
	    for (j = 0; j < cols && i < comps.length; j += 1) {
		row.push(comps[i]);
		i += 1;
	    }
	    rows.push('<td>' + row.join('</td><td>') + '</td>');
	    if (i === comps.length) {
		last_cols = cols;
		break;
	    }
	}
	return {
	    html: '<table><tbody><tr>' + rows.join('</tr><tr>') +
	    '</tr></tbody></table>',
	    rows: rows.length,
	    last_cols: last_cols
	};
    }
};