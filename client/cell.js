/**
Worksheet cells.

Careful about changing css classes - a lot of state is encoded in the classes.

Cell states:
    - .cell.code -- a code cell
        - .queued -- this cell is queued for evaluation.
        - .computing -- this cell is currently being computed.
        - .interrupting -- an interrupt is in progress.
	- .killing -- a kill is in progress
        - .focus -- the cell with focus
        - .last_focused -- this was the last cell with focus.
        - .need_stdin -- sys.stdin.read() was called.
	- .inspecting -- we are currently introspecting
    - .cell.text -- a text cell
        - .editing -- the html wsiwyg editor is open
*/

var CellType = {
    CODE: 1,
    TEXT: 2
};

var CellHtml = {};

CellHtml[CellType.CODE] = function (cell) {
    cell.div = $('\
<div class="cell code">\
  <div class="input"></div>\
  <div class="controls">\
    <a class="eval" href="#eval" title="Click here or press shift-enter to evaluate">evaluate</a>\
    <img class="computing" src="computing.gif" alt="computing.gif" title="Computing..." />\
    <img class="interrupting" src="interrupting.gif" alt="interrupting.gif" title="Attempting to interrupt..." />\
    <a class="interrupt" href="#interrupt" title="Interrupt computation">interrupt</a>\
    <span class="interrupt_failed">\
      Interrupt Failed!  Click kill and restart --&gt;\
    </span>\
    <span class="kill">\
      <a href="#kill" title="Kill Worksheet">kill and restart</a>\
    </span>\
  </div>\
  <div class="inspect"></div>\
  <pre class="output"></pre>\
  <div class="stdin_input">\
    &gt;&gt;&gt; <input class="stdin" type="text" />\
  </div>\
</div>');
    cell.div.data('cell', cell);
    cell.input = cell.div.find('.input')[0];
    cell.output = cell.div.find('.output')[0];
    if (cell.initial_output !== undefined) {
        cell.output.innerHTML = cell.initial_output;
    }
};

CellHtml[CellType.TEXT] = function (cell) {
    cell.div = $('\
<div class="cell text">\
  <div class="save_cancel">\
    <button class="save">Save</button>\
    <button class="cancel">Cancel</button>\
    <button class="del">Delete</button>\
  </div>\
  <div class="input"></div>\
</div>');
    cell.div.append(cell.div.find('.save_cancel').clone());
    cell.div.data('cell', cell);
    cell.input = cell.div.find('.input')[0];
};

function strip_output(s) {
    s = s.replace(/&/g, '&amp;')
         .replace(/</g, '&lt;')
         .replace(/>/g, '&gt;');
    return s;
}

function Cell(opts) {
    /**
    An input cell.
    Public fields:
        div {jquery element} -- outer div that wraps this cell.
        input {dom element} -- div that wraps this cell's input.
	inspect {Inspect object} -- for introspection
    */

    opts = $.extend({
        id: -1,
        type: CellType.CODE
    }, opts);
    this.id = opts.id;
    this.type = opts.type;
    this.initial_input = (opts.input !== undefined)? opts.input : '';
    this.initial_output = (opts.output !== undefined)? opts.output : '';
}

Cell.load = function (obj) {
    var c = new Cell(obj);
    return c;
};

Cell.prototype = {
    ui: function (node) {
        CellHtml[this.type](this);
        return this.div;
    },
    after_attached: function (not_new) {
	var data = {
	    cell: this,
	    ws: get_worksheet(this)
	};
        if (this.type === CellType.CODE) {
            this.editor = new CodeMirror(this.input, {
                parserfile: "parsepython.js",
                stylesheet: "codemirror/pythoncolors.css",
                path: "codemirror/",
                lineNumbers: false,
                textWrapping: false,
                indentUnit: 4,
                tabMode: "shift",
                parserConfig: {
                    strictErrors: false
                },
                width: "90%",
                height: "dynamic",
                minHeight: 25,
                initCallback: CellEvents.codemirror_initCallback,
                onChange: CellEvents.codemirror_onChange,
                content: this.initial_input,
                keydown: {
                    func: CellEvents.codemirror_keydown,
                    data: data
		}
            });
            $(this.editor.win)
	        .bind('focus', data, CellEvents.codemirror_focus)
	        .bind('blur', data, CellEvents.codemirror_blur)
	        .bind('keydown', data, CellEvents.codemirror_keydown_after);
	    this.div.find('input.stdin').bind('keydown', data,
					      CellEvents.stdin_keydown);
        } else if (this.type === CellType.TEXT) {
            if (not_new) {
                this.set_text_html(this.initial_input);
            } else {
                this.editor = CKEDITOR.replace(this.input, {
                    startupFocus: true
                });
                this.div.addClass('editing');
            }
        }
    },
    dump: function () {
        var r = {
            id: this.id,
            type: this.type
        };
        if (this.type === CellType.CODE) {
            r.input = this.editor.getCode();
            r.output = this.output.innerHTML;
            r.data = {};
        } else if (this.type === CellType.TEXT) {
            r.input = this.input.innerHTML;
        }
        return r;
    },
    set_text_html: function (html, without_eval) {
        // hack to get any script tags to get saved (.html evals and
        // removes them)
        this.input.innerHTML = html;
        if (!without_eval) {
            $('<div style="display:none"></div>').appendTo(this.div)
                .html(html).remove();
        }
    },

    append_output: function (m) {
        var lc = this.output.lastChild;
        if (lc && lc.className == m.type) {
            lc.innerHTML += strip_output(m.end_bytes);
        } else {
            var d = document.createElement('SPAN');
            d.className = m.type;
            d.innerHTML = strip_output(m.end_bytes);
            this.output.appendChild(d);
        }
    },
    clear_output: function () {
        this.output.innerHTML = '';
    },

    open_stdin: function () {
        this.div.removeClass('focus');
        var stdin = this.div.find('input.stdin').first();
        console.log(stdin);
        stdin.val('');
        stdin.focus();
    },

    wrap_line: function (lineno) {
        /** lineno is 1-indexed. */
        var br1 = this.editor.nthLine(lineno);
        var br2 = this.editor.nthLine(lineno + 1);
        var edoc = this.editor.win.document;
        var body = edoc.body;
        var n;
        if (br1 === false) {
            return false;
        }
        if (br1 === null) {
            /** first line. */
            n = body.firstChild;
        } else {
            n = br1.nextSibling;
        }
        var nodes = [];
        if (br2 !== false) {
            while (n && n !== br2) {
                nodes.push(n);
                n = n.nextSibling;
            }
        } else {
            // we're on the last line
            while (n) {
                nodes.push(n);
                n = n.nextSibling;
            }
        }
        if (!nodes.length) {
            return false;
        }
        /*var span = edoc.createElement('SPAN');
        body.insertBefore(span, nodes[0]);
        for (var i = 0; i < nodes.length; i += 1) {
            n = nodes[i];
            body.removeChild(n);
            span.appendChild(n);
        }
        return span;*/
    },
    get_line_info: function () {
	/** Returns null if there is no last word, a string otherwise. */
	var lineh_chari = this.editor.cursorPosition(true);
	var lineh = lineh_chari.line;
	var chari = lineh_chari.character;
	var line = this.editor.lineContent(lineh);
	var before = line.substring(0, chari);
	if ($.trim(before).length === 0) {
	    // just whitespace - indent.
	    return null;
	}
	var word = /[\w.?(]+$/.exec(before);
	if (word === null) {
	    // whitespace before the cursor - indent?
	    return null;
	}
	word = word[0];
	before = before.substring(0, before.length - word.length);
	return {
	    lineh: lineh,
	    before: before,
	    word: word,
	    after: line.substring(chari)
	};
    }
};
