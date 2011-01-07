var Kb = {
    tab: function (event) {
	return event.which === 9 && !event.shiftKey;
    },
    enter: function (event) {
	return event.which === 13 && !event.shiftKey;
    },
    shift: function (event) {
	return event.which === 16;
    },
    left: function (event) {
	return event.which === 37;
    },
    up: function (event) {
	return event.which === 38;
    },
    right: function (event) {
	return event.which === 39;
    },
    down: function (event) {
	return event.which === 40;
    },
    bkspace: function (event) {
	return event.which === 8;
    },

    evaluate: function (event) {
	return event.which === 13 && event.shiftKey;
    },
    inspect: function (event) {
	return event.which === 9 && !event.shiftKey;
    },
    stdin_EOF: function (event) {
	return event.which === 68 && event.ctrlKey;
    }
};