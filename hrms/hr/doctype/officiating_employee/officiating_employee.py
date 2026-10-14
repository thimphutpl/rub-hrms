# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import getdate, nowdate
from frappe.utils.data import add_days

class OfficiatingEmployee(Document):
	def validate(self):
		self.set_roles()
		if self.employee == self.officiating_employee:
			frappe.throw("Both Employee and Officiating Employee can not be same person")
		#em_list = frappe.db.sql("select employee, employee_name from tabEmployee where status = 'Active' and reports_to = \'" + str(self.employee) + "\'", as_dict=True)
		#self.set('items', [])

		#for d in em_list:
		#	row = self.append('items', {})
		#	row.update(d)
	def set_roles(self):
		if not self.employee or not self.officiating_employee:
			return

		employee_user = frappe.db.get_value(
			"Employee",
			self.employee,
			"user_id"
		)

		officiating_user = frappe.db.get_value(
			"Employee",
			self.officiating_employee,
			"user_id"
		)

		if not employee_user or not officiating_user:
			self.set("roles", [])
			return

		employee_roles = frappe.get_roles(employee_user)
		officiating_roles = set(frappe.get_roles(officiating_user))
		

		self.set("roles", [])

		for role in employee_roles:
			
		
			if role not in officiating_roles:
				
				self.append("roles", {
					"role": role
				})
	def on_submit(self):
		user = frappe.get_doc("User", frappe.db.get_value("Employee", self.officiating_employee, "user_id"))
		user.flags.ignore_permissions = True

		#if "Approver" not in user.get("user_roles"):
		roles = [i.role for i in user.roles]

		# if "Leave Approver" not in roles:
		# 	user.add_roles("Leave Approver")
		# 	self.db_set("already", 0)
		# else:
		# 	self.db_set("already", 1)
		
		# if len(self.roles) > 0:
		# 	for a in self.roles:
		# 		if str(a.role) not in roles:
		# 			user.add_roles(str(a.role))
		for a in self.roles:
			role = a.role

			if role and role not in roles:
				user.add_roles(role)
				self.db_set("already", 0)
			else:
				self.db_set("already", 1)

		#emp = frappe.get_doc("Employee", self.officiate)
		#emp.db_set("reports_to", frappe.db.get_value("Employee", self.employee, "reports_to"))
		#emp.db_set("approver_name", frappe.db.get_value("Employee", self.employee, "approver_name"))
	# @frappe.whitelist()
	# def get_roles(self):
	# 	if self.employee and not frappe.db.get_value("Employee",self.employee,"user_id"):
	# 		frappe.throw("No User found for Employee {}".format(self.employee))
	# 	if self.officiating_employee and not frappe.db.get_value("Employee",self.officiating_employee,"user_id"):
	# 		frappe.throw("No User found for Employee {}".format(self.officiating_employee))
	# 	roles = frappe.get_roles(frappe.db.get_value("Employee",self.employee,"user_id"))
	# 	o_roles = frappe.get_roles(frappe.db.get_value("Employee",self.officiating_employee,"user_id")) 
	# 	if roles:
	# 		self.set("roles",[])
	# 		for a in roles:
	# 			if a not in o_roles:
	# 				row = self.append("roles",{})
	# 				a = {'role':a}
	# 				row.update(a)
	# 	return frappe.get_value("Employee", self.officiating_employee, "employee_name")
	@frappe.whitelist()
	def get_roles(self):
		if not self.employee:
			frappe.throw("Please select Employee to be offiicated")
		if not self.officiating_employee:
			frappe.throw("Please select officiating Employee")
			
		roles = frappe.get_roles(frappe.db.get_value("Employee",self.employee,"user_id"))
		o_roles = frappe.get_roles(frappe.db.get_value("Employee",self.officiating_employee,"user_id")) 
		if roles:
			self.set("roles",[])
			for a in roles:
				if a not in o_roles:
					row = self.append("roles",{})
					a = {'role':a}
					row.update(a)


	@frappe.whitelist()
	def revoke_perm(self):
		if self.revoked:
			frappe.throw("Already Revoked")
		if getdate(self.to_date) > getdate(nowdate()):
			self.db_set("to_date", nowdate())
		self.db_set("revoked", 1)
		if len(self.roles) > 0:
			user = frappe.get_doc("User", frappe.db.get_value("Employee", self.officiating_employee, "user_id"))
			user.flags.ignore_permissions = True
			for a in self.roles:
				user.remove_roles(str(a.role))
		frappe.msgprint("Permissions Revoked")

def check_off_exp():
	off = frappe.db.sql("""select name from `tabOfficiating Employee` 
		where docstatus = 1 and to_date = %(today)s""", {"today": add_days(nowdate(), -1)}, as_dict=True)
	for a in off:
		print(str(a))
		doc = frappe.get_doc("Officiating Employee", a)
		doc.revoke_perm()

