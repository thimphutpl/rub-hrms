# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.model.naming import set_name_by_naming_series, make_autoname
from frappe.utils import add_years, cint, get_link_to_form, getdate

from erpnext.setup.doctype.employee.employee import Employee
from datetime import datetime



class EmployeeMaster(Employee):
	# def autoname(self):
	# 	if self.old_id:
	# 		self.employee = self.name = self.old_id
	# 		return

	# 	if not self.date_of_joining:
	# 		frappe.throw(
	# 			_("Date of Joining is required to generate a new Employee ID.")
	# 		)

	# 	try:
	# 		date_val = frappe.utils.getdate(self.date_of_joining)
	# 		joining_date = date_val.strftime("%Y-%m-%d")

	# 		fiscal_year = frappe.db.get_value(
	# 			"Fiscal Year",
	# 			{
	# 				"year_start_date": ["<=", joining_date],
	# 				"year_end_date": [">=", joining_date],
	# 			},
	# 			["name", "year_start_date"],
	# 			order_by="year_start_date desc",
	# 		)

	# 		if not fiscal_year:
	# 			frappe.throw(
	# 				_("No Fiscal Year found for Date of Joining {0}.").format(
	# 					joining_date
	# 				)
	# 			)

	# 		fiscal_start_date = frappe.utils.getdate(fiscal_year[1])

	# 		fiscal_year_code = fiscal_start_date.strftime("%y")
	# 		month_code = date_val.strftime("%m")

	# 		prefix = f"RUB{fiscal_year_code}{month_code}"

	# 		# Find the highest existing serial for this FY + month
	# 		last_serial = frappe.db.sql(
	# 			"""
	# 			SELECT MAX(
	# 				CAST(SUBSTRING(name, %s) AS UNSIGNED)
	# 			)
	# 			FROM `tabEmployee`
	# 			WHERE name LIKE %s
	# 			""",
	# 			(
	# 				len(prefix) + 1,
	# 				f"{prefix}%",
	# 			),
	# 		)[0][0]

	# 		if last_serial is None:
	# 			serial_number = 1
	# 		else:
	# 			serial_number = int(last_serial) + 1

	# 		# 001, 002, ... 999, 1000, 1001...
	# 		serial_number = str(serial_number).zfill(3)

	# 		new_name = f"{prefix}{serial_number}"

	# 		self.employee = self.name = new_name

	# 	except Exception:
	# 		frappe.log_error(
	# 			title="Employee ID Generation Error",
	# 			message=frappe.get_traceback(),
	# 		)

	# 		frappe.throw(
	# 			_("Unable to generate Employee ID.")
	# 		)
	def autoname(self):
		if self.old_id:
			self.employee = self.name = self.old_id
			return

		if not self.date_of_joining:
			frappe.throw(
				_("Date of Joining is required to generate a new Employee ID.")
			)

		try:
			date_val = frappe.utils.getdate(self.date_of_joining)
			joining_date = date_val.strftime("%Y-%m-%d")

			# Get fiscal year for the joining date
			fiscal_year = frappe.db.get_value(
				"Fiscal Year",
				{
					"year_start_date": ["<=", joining_date],
					"year_end_date": [">=", joining_date],
				},
				"year_start_date",  # Just get the field value directly
				order_by="year_start_date desc",
			)

			if not fiscal_year:
				frappe.throw(
					_("No Fiscal Year found for Date of Joining {0}.").format(
						joining_date
					)
				)

			# fiscal_year is already the date object, no need to index
			fiscal_start_date = frappe.utils.getdate(fiscal_year)
			
			# Get last 2 digits of fiscal year
			year_code = fiscal_start_date.strftime("%y")
			
			# Get 2-digit month from joining date
			month_code = date_val.strftime("%m")
			
			# Build prefix
			year_prefix = f"RUB{year_code}"
			prefix = f"{year_prefix}{month_code}"
			
			# Find highest serial
			last_serial = frappe.db.sql(
				"""
				SELECT MAX(
					CAST(SUBSTRING(name, %s) AS UNSIGNED)
				)
				FROM `tabEmployee`
				WHERE name LIKE %s
				AND LENGTH(name) = %s
				""",
				(
					len(prefix) + 1,
					f"{prefix}%",
					len(prefix) + 3,
				),
			)[0][0]

			serial_number = 0 if last_serial is None else int(last_serial) + 1
			serial_number = str(serial_number).zfill(3)

			new_name = f"{prefix}{serial_number}"
			
			self.employee = self.name = new_name

		except Exception as e:
			frappe.log_error(
				title="Employee ID Generation Error",
				message=frappe.get_traceback(),
			)
			frappe.throw(
				_("Unable to generate Employee ID. Error: {0}").format(str(e))
			)


def validate_onboarding_process(doc, method=None):
	"""Validates Employee Creation for linked Employee Onboarding"""
	if not doc.job_applicant:
		return

	employee_onboarding = frappe.get_all(
		"Employee Onboarding",
		filters={
			"job_applicant": doc.job_applicant,
			"docstatus": 1,
			"boarding_status": ("!=", "Completed"),
		},
	)
	if employee_onboarding:
		onboarding = frappe.get_doc("Employee Onboarding", employee_onboarding[0].name)
		onboarding.validate_employee_creation()
		onboarding.db_set("employee", doc.name)


def publish_update(doc, method=None):
	import hrms

	hrms.refetch_resource("hrms:employee", doc.user_id)


def update_job_applicant_and_offer(doc, method=None):
	"""Updates Job Applicant and Job Offer status as 'Accepted' and submits them"""
	if not doc.job_applicant:
		return

	applicant_status_before_change = frappe.db.get_value("Job Applicant", doc.job_applicant, "status")
	if applicant_status_before_change != "Accepted":
		frappe.db.set_value("Job Applicant", doc.job_applicant, "status", "Accepted")
		frappe.msgprint(
			_("Updated the status of linked Job Applicant {0} to {1}").format(
				get_link_to_form("Job Applicant", doc.job_applicant), frappe.bold(_("Accepted"))
			)
		)
	offer_status_before_change = frappe.db.get_value(
		"Job Offer", {"job_applicant": doc.job_applicant, "docstatus": ["!=", 2]}, "status"
	)
	if offer_status_before_change and offer_status_before_change != "Accepted":
		job_offer = frappe.get_last_doc("Job Offer", filters={"job_applicant": doc.job_applicant})
		job_offer.status = "Accepted"
		job_offer.flags.ignore_mandatory = True
		job_offer.flags.ignore_permissions = True
		job_offer.save()

		msg = _("Updated the status of Job Offer {0} for the linked Job Applicant {1} to {2}").format(
			get_link_to_form("Job Offer", job_offer.name),
			frappe.bold(doc.job_applicant),
			frappe.bold(_("Accepted")),
		)
		if job_offer.docstatus == 0:
			msg += "<br>" + _("You may add additional details, if any, and submit the offer.")

		frappe.msgprint(msg)


def update_approver_role(doc, method=None):
	"""Adds relevant approver role for the user linked to Employee"""
	if doc.leave_approver:
		user = frappe.get_doc("User", doc.leave_approver)
		user.flags.ignore_permissions = True
		user.add_roles("Leave Approver")

	if doc.expense_approver:
		user = frappe.get_doc("User", doc.expense_approver)
		user.flags.ignore_permissions = True
		user.add_roles("Expense Approver")


def update_employee_transfer(doc, method=None):
	"""Unsets Employee ID in Employee Transfer if doc is deleted"""
	if frappe.db.exists("Employee Transfer", {"new_employee_id": doc.name, "docstatus": 1}):
		emp_transfer = frappe.get_doc("Employee Transfer", {"new_employee_id": doc.name, "docstatus": 1})
		emp_transfer.db_set("new_employee_id", "")


@frappe.whitelist()
def get_timeline_data(doctype, name):
	"""Return timeline for attendance"""
	from frappe.desk.notifications import get_open_count

	out = {}

	open_count = get_open_count(doctype, name)
	out["count"] = open_count["count"]

	timeline_data = dict(
		frappe.db.sql(
			"""
			select unix_timestamp(attendance_date), count(*)
			from `tabAttendance` where employee=%s
			and attendance_date > date_sub(curdate(), interval 1 year)
			and status in ('Present', 'Half Day')
			group by attendance_date""",
			name,
		)
	)

	out["timeline_data"] = timeline_data
	return out


@frappe.whitelist()
def get_retirement_date(date_of_birth=None):
	if date_of_birth:
		try:
			retirement_age = cint(frappe.db.get_single_value("HR Settings", "retirement_age") or 60)
			dt = add_years(getdate(date_of_birth), retirement_age)
			return dt.strftime("%Y-%m-%d")
		except ValueError:
			# invalid date
			return
