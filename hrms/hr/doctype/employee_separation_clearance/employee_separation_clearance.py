# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from erpnext.custom_workflow import validate_workflow_states, notify_workflow_states
from hrms.hr.hr_custom_function import get_officiating_employee


class EmployeeSeparationClearance(Document):
	def validate(self):
		self.check_duplicates()
		self.set_approvers()
		self.workflow_action()

	def on_submit(self):
		self.check_signatures()
		self.update_reference()
		# self.send_notification()


	def workflow_action(self):  
		action = frappe.request.form.get('action')
		
		if action == "Save":
			self.verifyUpdate()           
			if self.supervisor_clearance + self.hr_clearance + self.fad_clearance  + self.tdg_clearance + self.edg_clearance + self.td_clearance + self.smli_clearance + self.ped_clearance + self.pmb_clearance == 9:
				self.verifyUpdate()
				self.verifyUpdate()
		
		if action == "Reapply":
			em = frappe.db.sql("Select user_id from `tabEmployee` where name='{}'".format(self.employee), as_dict=True)
			if frappe.session.user != em[0].user_id:
				frappe.throw("You cannot apply for another employee.")
			self.reApply()

	def verifyUpdate(self):
		user = frappe.session.user
		
		if user == self.hr:
			self.hr_clearance = 1
		if user == self.fad:
			self.fad_clearance = 1
		if user == self.tdg:
			self.tdg_clearance = 1
		if user == self.edg:
			self.edg_clearance = 1
		if user == self.td:
			self.td_clearance = 1
		if user == self.smli:
			self.smli_clearance = 1
		if user == self.supervisor:
			self.supervisor_clearance = 1
		if user == self.ped:
			self.ped_clearance = 1
		if user == self.pmb:
			self.pmb_clearance = 1  

	def reApply(self):
		self.hr_clearance = 0
		self.fad_clearance = 0
		self.tdg_clearance = 0
		self.edg_clearance = 0
		self.td_clearance = 0
		self.smli_clearance = 0
		self.supervisor_clearance = 0
		self.ped_clearance = 0
		self.pmb_clearance = 0

		self.hr_remarks = ""
		self.fad_remarks = ""
		self.tdg_remarks = ""
		self.edg_remarks = ""
		self.td_remarks = ""
		self.smli_remarks = ""
		self.supervisor_remarks = ""
		self.ped_remarks = ""
		self.pmb_remarks = ""
		

	def on_cancel(self):
		self.update_reference()
			
	def check_signatures(self):
		if self.supervisor_clearance == 0:
			frappe.throw("Supervisor has not granted clearance.")
		if self.hr_clearance == 0:
			frappe.throw("HR & Admin Division has not granted clearance.")
		if self.fad_clearance == 0:
			frappe.throw("Finance & Accounts Division has not granted clearance.")
		if self.tdg_clearance == 0:
			frappe.throw("Tata Division General Manager has not granted clearance.")
		if self.edg_clearance == 0:
			frappe.throw("Eicher Division General Manager has not granted clearance.")
		if self.td_clearance == 0:
			frappe.throw("Toyota Division has not granted clearance.")
		if self.smli_clearance == 0:
			frappe.throw("SMLI & Home Division Manager has not granted clearance.")
		if self.ped_clearance == 0:
			frappe.throw("Petroleum Division has not granted clearance.")
		if self.pmb_clearance == 0:
			frappe.throw("Planning Monitoring & Business Development has not granted clearance.")
		

	def update_reference(self):
		id = frappe.get_doc("Employee Separation",self.employee_separation_id)
		id.clearance_acquired = 1 if self.docstatus == 1 else 0
		id.save()

	def check_duplicates(self):
		duplicates = frappe.db.sql("""
			select name from `tabEmployee Separation Clearance` where employee_separation_id = '{0}'  and name != '{1}' and docstatus != 2
				""".format(self.employee_separation_id,self.name))
		if duplicates:
			frappe.throw("There is already a pending Separation Clearance created for the Employee Separation '{}'".format(self.employee_separation_id))
	
	def get_receipients(self):
		receipients = []
		if self.supervisor:
			receipients.append(self.supervisor)
		if self.hr:
			receipients.append(self.hr)
		if self.fad:
			receipients.append(self.fad)
		if self.tdg:
			receipients.append(self.tdg)
		if self.edg:
			receipients.append(self.edg)
		if self.td:
			receipients.append(self.td)
		if self.smli:
			receipients.append(self.smli)
		if self.ped:
			receipients.append(self.ped)
		if self.pmb:
			receipients.append(self.pmb)
		return receipients

	@frappe.whitelist()
	def set_approvers(self):
		#----------------------------Supervisor------------------------|
		if not frappe.db.get_value("Employee",self.employee, "reports_to"):
			frappe.throw("Reports To for employee {} is not set".format(self.employee))
		supervisor_officiate = get_officiating_employee(frappe.db.get_value("Employee",self.employee, "reports_to"))
		if supervisor_officiate:
			self.supervisor = frappe.db.get_value("Employee",supervisor_officiate[0].officiate,"user_id")
		else:
			self.supervisor = frappe.db.get_value("Employee",frappe.db.get_value("Employee",self.employee, "reports_to"),"user_id")

		#--------------------------- HR & Admin Division --------------------------|
		if not frappe.db.get_single_value("HR Settings", "hr_division"):
			frappe.throw("HR & Admin Division clearance approver is not set in HR Settings")
		hr_officiate = get_officiating_employee(frappe.db.get_single_value("HR Settings", "hr_division"))
		if hr_officiate:
			self.hr = frappe.db.get_value("Employee",hr_officiate[0].officiate,"user_id")
		else:
			self.hr = frappe.db.get_value("Employee",frappe.db.get_single_value("HR Settings", "hr_division"),"user_id")
   
		#--------------------------- Accounts & Finance --------------------------|
		if not frappe.db.get_single_value("HR Settings", "accounts_finance"):
			frappe.throw("Accounts & Finance clearance approver is not set in HR Settings")
		fad_officiate = get_officiating_employee(frappe.db.get_single_value("HR Settings", "accounts_finance"))
		if fad_officiate:
			self.fad = frappe.db.get_value("Employee",fad_officiate[0].officiate,"user_id")
		else:
			self.fad = frappe.db.get_value("Employee",frappe.db.get_single_value("HR Settings", "accounts_finance"),"user_id")

		#--------------------------- Tata Division General Manager --------------------------|
		if not frappe.db.get_single_value("HR Settings", "tata_division_general_manager"):
			frappe.throw("Tata Division General Manager clearance approver is not set in HR Settings")
		tdg_officiate = get_officiating_employee(frappe.db.get_single_value("HR Settings", "tata_division_general_manager"))
		if tdg_officiate:
			self.tdg = frappe.db.get_value("Employee",tdg_officiate[0].officiate,"user_id")
		else:
			self.tdg = frappe.db.get_value("Employee",frappe.db.get_single_value("HR Settings", "tata_division_general_manager"),"user_id")

		#--------------------------- Eicher Division General Manager --------------------------|
		if not frappe.db.get_single_value("HR Settings", "eicher_division_general_manager"):
			frappe.throw("Eicher Division General Manager clearance approver is not set in HR Settings")
		edg_officiate = get_officiating_employee(frappe.db.get_single_value("HR Settings", "eicher_division_general_manager"))
		if edg_officiate:
			self.edg = frappe.db.get_value("Employee",edg_officiate[0].officiate,"user_id")
		else:
			self.edg = frappe.db.get_value("Employee",frappe.db.get_single_value("HR Settings", "eicher_division_general_manager"),"user_id")

		#--------------------------- Petroleum Division Manager --------------------------|
		if not frappe.db.get_single_value("HR Settings", "petroleum_division"):
			frappe.throw("Petroleum Division Manager clearance approver is not set in HR Settings")
		ped_officiate = get_officiating_employee(frappe.db.get_single_value("HR Settings", "petroleum_division"))
		if ped_officiate:
			self.ped = frappe.db.get_value("Employee",ped_officiate[0].officiate,"user_id")
		else:
			self.ped = frappe.db.get_value("Employee",frappe.db.get_single_value("HR Settings", "petroleum_division"),"user_id")

		#--------------------------- SMLI & Home Division Manager --------------------------|
		if not frappe.db.get_single_value("HR Settings", "home_division"):
			frappe.throw("Petroleum Division Manager clearance approver is not set in HR Settings")
		smli_officiate = get_officiating_employee(frappe.db.get_single_value("HR Settings", "home_division"))
		if smli_officiate:
			self.smli = frappe.db.get_value("Employee",smli_officiate[0].officiate,"user_id")
		else:
			self.smli = frappe.db.get_value("Employee",frappe.db.get_single_value("HR Settings", "home_division"),"user_id")
   
		#--------------------------- Toyota Division Manager --------------------------|
		if not frappe.db.get_single_value("HR Settings", "toyota_division_manager"):
			frappe.throw("Petroleum Division Manager clearance approver is not set in HR Settings")
		td_officiate = get_officiating_employee(frappe.db.get_single_value("HR Settings", "toyota_division_manager"))
		if td_officiate:
			self.td = frappe.db.get_value("Employee",td_officiate[0].officiate,"user_id")
		else:
			self.td = frappe.db.get_value("Employee",frappe.db.get_single_value("HR Settings", "toyota_division_manager"),"user_id")
   
		#--------------------------- Planning Monitoring & Business Development --------------------------|
		if not frappe.db.get_single_value("HR Settings", "planning_monitoring"):
			frappe.throw("Petroleum Division Manager clearance approver is not set in HR Settings")
		pmb_officiate = get_officiating_employee(frappe.db.get_single_value("HR Settings", "planning_monitoring"))
		if pmb_officiate:
			self.pmb = frappe.db.get_value("Employee",pmb_officiate[0].officiate,"user_id")
		else:
			self.pmb = frappe.db.get_value("Employee",frappe.db.get_single_value("HR Settings", "planning_monitoring"),"user_id")

		self.db_set("approvers_set", 1)

# Following code added by SHIV on 2020/09/21
def get_permission_query_conditions(user):
	if not user: user = frappe.session.user
	user_roles = frappe.get_roles(user)

	if user == "Administrator":
		return
	if "HR User" in user_roles or "HR Manager" in user_roles:
		return

	return """(
		`tabEmployee Separation Clearance`.owner = '{user}'
		or
		exists(select 1
				from `tabEmployee`
				where `tabEmployee`.name = `tabEmployee Separation Clearance`.employee
				and `tabEmployee`.user_id = '{user}')
		or
		(`tabEmployee Separation Clearance`.supervisor = '{user}' and `tabEmployee Separation Clearance`.docstatus = 0)
		or
		(`tabEmployee Separation Clearance`.hr = '{user}' and `tabEmployee Separation Clearance`.docstatus = 0)
		or
		(`tabEmployee Separation Clearance`.fad = '{user}' and `tabEmployee Separation Clearance`.docstatus = 0)
		or
		(`tabEmployee Separation Clearance`.tdg = '{user}' and `tabEmployee Separation Clearance`.docstatus = 0)
		or
		(`tabEmployee Separation Clearance`.edg = '{user}' and `tabEmployee Separation Clearance`.docstatus = 0)
		or
		(`tabEmployee Separation Clearance`.td = '{user}' and `tabEmployee Separation Clearance`.docstatus = 0)
		or
		(`tabEmployee Separation Clearance`.smli = '{user}' and `tabEmployee Separation Clearance`.docstatus = 0)
		or
		(`tabEmployee Separation Clearance`.ped = '{user}' and `tabEmployee Separation Clearance`.docstatus = 0)
		or
		(`tabEmployee Separation Clearance`.pmb = '{user}' and `tabEmployee Separation Clearance`.docstatus = 0)

	)""".format(user=user)
