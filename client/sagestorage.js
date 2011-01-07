function SageLocalStorage(id) {
    if (!("localStorage" in window)) {
        alert("localStorage not supported in this browser - use chrome.");
        return {};
    }
    this.id = id;
    this.store = localStorage;
}

SageLocalStorage.prototype = {
    is_new: function () {
        return this.store.getItem(this.id) === null;
    },
    load: function () {
        return JSON.parse(this.store.getItem(this.id));
    },
    save: function (obj) {
        this.store.setItem(this.id, JSON.stringify(obj));
    },
};
