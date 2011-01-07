/**
   css class states:
     - .worksheet.noserver -- can't find the execution server.

   Events: most events (evaluate, interrupt, insert_new_cell, etc) are attached
     to the worksheet div (see jQuery.delegate).  For events that happen more
     frequently, like keydown events, these are attached to the elements in the
     cell.  */

function get_worksheet(node_or_cell) {
    /**
    Gets the first Worksheet object above us in the dom tree.
    */
    if (node_or_cell.hasOwnProperty('id') &&
	    node_or_cell.hasOwnProperty('div')) {
        return get_worksheet(node_or_cell.div);
    }
    return $(node_or_cell).closest('.worksheet').data('worksheet');
}

function get_cell(node) {
    /**
    Gets the first Cell object above us in the dom tree.
    */
    return $(node).closest('.cell').data('cell');
}


function Worksheet(div, opts) {
    /**
       this.div -- jQuery element of the container div.
       this.cells {id -> Cell Objects}
       this.last_focused {int} -- the id of the last focused code cell.
    */
    $.extend(this, {
        id: "sage_worksheet_0",
        title: "Simple Sage Worksheet"
    }, opts);

    this.div = $(div)
	.addClass('worksheet')
	.data('worksheet', this)
        .empty()
        .append('<div class="insert_new_cell"></div>')
	.delegate('.insert_new_cell', 'click', this,
	          CellEvents.insert_new_cell)
        .delegate('.cell.code .controls a.eval', 'click', this,
	          CellEvents.evaluate_cell)
        .delegate('.cell.code .controls a.interrupt', 'click', this,
	          CellEvents.interrupt_cell)
        .delegate('.cell.code .controls .kill > a', 'click', this,
	          CellEvents.kill_cell)
        .delegate('.cell.text > .save_cancel .save', 'click', this,
	          CellEvents.save_text_cell)
        .delegate('.cell.text > .save_cancel .cancel', 'click', this,
	          CellEvents.cancel_text_cell)
        .delegate('.cell.text > .save_cancel .del', 'click', this,
	          CellEvents.remove_cell)
        .delegate('.cell.text > .input', 'dblclick', this,
	          CellEvents.open_text_editor);
    this.cells = {};
    this.last_focused = -1;
    this.server = new SageServer('127.0.0.1:8044',
				 $.proxy(this.server_onopen, this),
				 $.proxy(this.server_onclose, this));
    this.storage = new SageLocalStorage(this.id);
    if (this.storage.is_new()) {
        // create an empty input cell to begin with.
        this.last_id = 0;
        this.div.children().first().click();
    } else {
        // rebuild from storage
        this.load(this.storage.load());
    }
    this.stimer = setInterval($.proxy(function () {
        this.storage.save(this.dump());
    }, this), 2000);
}

var CellEvents = {
    insert_new_cell: function (event) {
	/**
	 * this -- insert_new_cell <div>.
	 * event.data -- the worksheet.
	 */
	var ws = event.data,
            cell = ws.create_cell({
		type: (event.shiftKey)? CellType.TEXT : CellType.CODE
	    });
	ws.insert_new_cell(cell, this);
    },

    remove_cell: function (event) {
	/**
	 * this -- something in the cell div
	 * event.data -- the worksheet
	 */
	var ws = event.data,
            cell = get_cell(this);
	ws.remove_cell(cell);
    },

/*=============================================================================
 *      .cell.code events
 * ==========================================================================*/
    evaluate_cell: function (event) {
	/**
	 * this -- evaluate <a>.
	 * event.data -- this worksheet.
	 */
	var cell = get_cell(this),
            ws = event.data;
	ws.evaluate_cell(cell);
	return false;
    },

    interrupt_cell: function (event) {
	/**
	 * this -- interrupt <a>.
	 * event.data -- this worksheet.
	 */
	var cell = get_cell(this),
            ws = event.data;
	if (cell.div.hasClass('computing')) {
            cell.div.addClass('interrupting');
            console.log("Interrupt:", cell.id);
	    cell.div.find('.controls .interrupt_failed')
		    .css('display', 'none');
            ws.server.send({
		type: "Interrupt"
	    }, ws.recv_from_Interrupt, {
		ws: ws,
		cell_id: cell.id
	    });
	}
	return false;
    },

    kill_cell: function (event) {
	/**
	 * this -- kill <a>.
	 * event.data -- this worksheet.
	 */
	var cell = get_cell(this),
	    ws = event.data;
	if (cell.div.hasClass('computing')) {
	    cell.div.addClass('killing');
	    console.log("Kill:", cell.id);
	    ws.server.send({type: "Shutdown"});
	}
	return false;
    },

    stdin_keydown: function (event) {
	/**
	 * this -- <input.stdin> element
	 * event.data = {cell: cell object, ws: worksheet object}
	 */
	var cell = event.data.cell,
	    ws = event.data.ws;
	if (Kb.stdin_EOF(event)) { // Ctrl+D
	    ws.send_stdin(this.value);
	    ws.send_stdin('');
	    return false;
	} else if (Kb.enter(event)) { // enter
	    ws.send_stdin(this.value + '\n');
	    return false;
	} else if (Kb.up(event)) { // up arrow
	    return false;
	} else if (Kb.down(event)) { // down arrow
	    return false;
	}
    },

    codemirror_focus: function (event) {
	/**
	 * event.data = {cell: cell object, ws: worksheet object}
	 */
	var cell = event.data.cell,
            ws = event.data.ws,
	    last_cell = ws.cells[ws.last_focused];
	if (last_cell) {
            last_cell.div.removeClass('last_focused');
	    if (last_cell.inspect) {
		last_cell.inspect.remove();
	    }
	}
	cell.div.addClass('last_focused');
	ws.last_focused = cell.id;
	cell.div.addClass('focus');
    },

    codemirror_blur: function (event) {
	/**
	 * event.data = {cell: cell object, ws: worksheet object}
	 */
	var cell = event.data.cell,
            ws = event.data.ws;
	cell.div.removeClass('focus');
    },

    codemirror_keydown: function (event) {
	/**
	 * event.data = {cell: cell object, ws: worksheet object}
	 */
	var cell = event.data.cell,
	    ws = event.data.ws;
	if (cell.inspect) {
	    if (!cell.inspect.loading) {
		if (cell.inspect.handle_keydown(event)) {
		    // handled by an opened inspect
		    return false;
		} // else { // unhandled, remove the inspect window
	    } else if (Kb.tab(event)) {
		// inspect is loading, close if anything other than tab
		return false;
	    }
	    cell.inspect.remove();
	} else if (Kb.tab(event)) {
	    var line_info = cell.get_line_info();
	    if (line_info === null) {
		// no last word - indent.
		return;
	    }
	    cell.inspect = new Inspect(cell.div.find('.inspect')[0],
				       line_info);
	    return false;
        }
	if (Kb.evaluate(event)) { // shift + enter
	    ws.evaluate_cell(cell);
	    return false;
	}
    },

    codemirror_keydown_after: function (event) {
	/**
	 * event.data = {cell: cell object, ws: worksheet object}
	 */
	var cell = event.data.cell,
            ws = event.data.ws;
	if (Kb.bkspace(event)) { // bkspace
            if ($.trim(cell.editor.getCode()).length === 0 &&
	           ws.div.children('.cell').length > 1) {
		ws.remove_cell(cell);
		return false;
            }
	}
    },

    codemirror_onChange: function (event) {

    },

    codemirror_initCallback: function (editor) {
	editor.focus();
    },

/*=============================================================================
 *      .cell.text events
 * ==========================================================================*/
    save_text_cell: function (event) {
	/**
	 * this -- save <button>.
	 * event.data -- this worksheet.
	 */
	var cell = get_cell(this),
            ws = event.data;
	CellEvents.close_text_editor(ws, cell, true);
    },

    cancel_text_cell: function (event) {
	/**
	 * this -- cancel <button>.
	 * event.data -- this worksheet.
	 */
	var cell = get_cell(this),
            ws = event.data;
	CellEvents.close_text_editor(ws, cell, false);
    },

    open_text_editor: function (event) {
	/**
	 * this -- cell.input <div>.
	 * event.data -- this worksheet.
	 */
	get_cell(this).after_attached();
    },

    close_text_editor: function (ws, cell, save) {
	/**
	 * ws -- this worksheet.
	 * cell -- a Cell Object.
	 * save -- boolean.
	 */
	var html = $.trim((save)? cell.editor.getData() : cell.input.innerHTML);
	try {
            cell.editor.destroy(true); // noupdate true means not to update value
	} catch (e) {}
	cell.div.removeClass('editing');
	if (html.length === 0) {
            // nothing in the text cell, we should remove it.
            ws.remove_cell(cell);
	} else if (save) {
            cell.set_text_html(html);
	}
    }
};

Worksheet.prototype = {
    next_id: function () {
        return this.last_id + 1;
    },
    create_cell: function (opts) {
	opts.id = this.next_id();
        var c = new Cell(opts);
        this.last_id = c.id;
        return c;
    },
    insert_new_cell: function (cell, beforeE) {
	/**
	 * cell -- a Cell Object.
	 * beforeE -- a DOM node to put the cell before.
	 */
	if (!beforeE) {
	    beforeE = this.div.children('.insert_new_cell').last()[0];
	}
	this.cells[cell.id] = cell;
	$(beforeE).before('<div class="insert_new_cell"></div>')
	          .before(cell.ui());
	cell.after_attached(!beforeE);
    },
    evaluate_cell: function (cell) {
	var code = cell.editor.getCode();
	if (cell.inspect) {
	    cell.inspect.remove();
	}
	if (!cell.div.hasClass('computing')) {
            cell.clear_output();
            cell.div.addClass('computing');
            console.log("Exec:", code);
            this.server.send({
		type: "Exec",
		end_bytes: code,
		dict: {
		    name: '__cell_' + cell.id.toString() + '__',
		    except_msg: true
		}
	    }, this.recv_from_Exec, {
		    ws: this,
		    cell_id: cell.id
	    });
            var next_cell = cell.div.nextAll('.cell.code:first');
            if (next_cell.length) {
		get_cell(next_cell).editor.focus();
            } else {
		this.div.children('.insert_new_cell').last().click();
	    }
	}
    },
    remove_cell: function (cell) {
	/**
	 * this -- this worksheet.
	 * cell -- the Cell object to remove.
	 */
        delete this.cells[cell.id];
        var prev_cell = cell.div.prevAll('.cell.code:first');
        if (!prev_cell.length) {
            var next_cell = cell.div.nextAll('.cell.code:first');
            if (next_cell.length) {
                get_cell(next_cell).editor.focus();
            }
        } else {
            get_cell(prev_cell).editor.focus();
        }
	cell.div.prev().remove(); // insert_new_cell div
	if (cell.inspect) {
	    cell.inspect.remove();
	}
	cell.div.removeData('cell');
        cell.div.remove();
    },
    recv_from_Exec: function (msg, data) {
	/**
	 * :param msg: instance of Stdout, Stderr, Except, etc.
	 * :param data: {ws: this worksheet, cell_id: cell.id }
	 */
	var self = data.ws,
	    cell = self.cells[data.cell_id];
        if (!cell) {
            console.log("cell is gone!", msg);
            return false;
        }
	//console.log("recv_Exec:", msg);
	if (msg.type === "Done") {
	    cell.div.removeClass('computing interrupting need_stdin');
	    return false;
	} else if (msg.type === "NeedStdin") {
	    if (!cell.div.hasClass('need_stdin')) {
		cell.div.addClass('need_stdin');
		cell.open_stdin();
	    }
	} else if (msg.type === "Interact") {
	    var i = new Interact(cell, msg.dict);
	    i.ui().appendTo(cell.output);
	    i.after_attached();
	} else {
	    if (msg.type === "Stdin") {
		cell.div.removeClass('need_stdin');
	    } else if (msg.type === "Except") {
		console.log("Except info:", msg.dict);
	    }
	    cell.append_output(msg);
	}
    },
    recv_from_Interrupt: function (msg, data) {
	/**
	 * :param msg: instance of Stdout, Stderr, Except, etc.
	 * :param data: {ws: this worksheet, cell_id: cell.id }
	 */
	var self = data.ws,
	    cell = self.cells[data.cell_id];
        if (!cell) {
            console.log("cell is gone!", msg);
            return false;
        }
	cell.div.find('.controls .interrupt_failed')
		.css('display', (msg.type === 'Yes')? 'none' : 'inline');
	cell.div.removeClass('interrupting');
    },
    send_stdin: function (s) {
        this.server.send({type: "Stdin", end_bytes: s});
    },
    dump: function () {
        /**
        returns the current worksheet state.
        */
        var cells = [];
        this.div.find('.cell').each(function () {
            cells.push(get_cell(this).dump());
        });
        return {
            id: this.id,
            last_id: this.last_id,
            title: this.title,
            cells: cells
        };
    },

    load: function (obj) {
        console.log("Loading from:", obj);
        this.id = obj.id || "sage_worksheet_0";
        this.title = obj.title || 'Simple Sage Worksheet';
        this.last_id = obj.last_id || 0;
        obj.cells = obj.cells || [];
        this.cells = {};
        for (var i = 0; i < obj.cells.length; i += 1) {
            this.insert_new_cell(Cell.load(obj.cells[i]));
        }
    },

    server_onopen: function (server) {
	/** this -> Worksheet object. */
	this.div.removeClass('noserver');
    },
    server_onclose: function (server) {
	/** this -> Worksheet object. */
	this.div.addClass('noserver');
        //this.cells_div.find('.cell.computing').removeClass('computing interrupting');
    },
};
