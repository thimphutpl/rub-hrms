// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Travel Adjustment", {
    setup: function (frm) {
        frm.set_query("employee", function () {
            return {
                filters: { status: "Active" }
            };
        });
    }
});

frappe.ui.form.on("Travel Adjustment Item", {
    from_date: function (frm, cdt, cdn) {
        let child = locals[cdt][cdn];
        if (child.from_date && !child.halt && child.from_date !== child.to_date) {
            frappe.model.set_value(cdt, cdn, "to_date", child.from_date);
        }
    },

    to_date: function (frm, cdt, cdn) {
        let child = locals[cdt][cdn];
        if (child.from_date && child.to_date < child.from_date) {
            frappe.msgprint({
                title: __("Validation Error"),
                message: __("To Date cannot be earlier than From Date"),
                indicator: "red"
            });
            frappe.model.set_value(cdt, cdn, "to_date", child.from_date);
        }
    }
});
