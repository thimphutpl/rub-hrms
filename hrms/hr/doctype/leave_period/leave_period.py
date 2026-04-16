# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

from hrms.hr.utils import validate_overlap


class LeavePeriod(Document):
	def validate(self):
		self.validate_dates()
		validate_overlap(self, self.from_date, self.to_date, self.company)

	def validate_dates(self):
		if getdate(self.from_date) >= getdate(self.to_date):
			frappe.throw(_("To date can not be equal or less than from date"))
	def after_insert(self):
		if not self.company:
			return

		self.create_child_leave_periods()

	# ==============================
	# MAIN LOGIC
	# ==============================
	def create_child_leave_periods(self):
		child_companies = self.get_all_child_companies(self.company)

		created = 0  # ✅ counter

		for company in child_companies:

			if company == self.company:
				continue

			if self.leave_period_exists(company):
				continue

			self.create_leave_period(company)
			created += 1   # ✅ increment

		# ✅ SHOW MESSAGE ONLY IF CREATED
		if created > 0:
			frappe.msgprint(
				_("Leave Period created for {0} child companie(s).").format(created),
				indicator="green"
			)

	# ==============================
	# CHECK DUPLICATE
	# ==============================
	def leave_period_exists(self, company):
		return frappe.db.exists("Leave Period", {
			"company": company,
			"from_date": self.from_date,
			"to_date": self.to_date
		})

	# ==============================
	# CREATE RECORD
	# ==============================
	def create_leave_period(self, company):
		doc = frappe.new_doc("Leave Period")

		doc.company = company
		doc.from_date = self.from_date
		doc.to_date = self.to_date
		doc.is_active = self.is_active
		doc.optional_holiday_list = self.optional_holiday_list

		doc.insert(ignore_permissions=True)

	# ==============================
	# GET ALL CHILD COMPANIES (RECURSIVE)
	# ==============================
	def get_all_child_companies(self, parent):
		children = frappe.get_all(
			"Company",
			filters={"parent_company": parent},
			pluck="name"
		)

		all_children = []

		for child in children:
			all_children.append(child)
			all_children.extend(self.get_all_child_companies(child))

		return all_children