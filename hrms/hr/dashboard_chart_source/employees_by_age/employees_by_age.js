frappe.provide("frappe.dashboards.chart_sources");

frappe.dashboards.chart_sources["Employees by Age"] = {
	method: "hrms.hr.dashboard_chart_source.employees_by_age.employees_by_age.get_data",
};
