# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from hrms.hr.utils import validate_active_employee
from frappe.utils import (
	add_days,
	ceil,
	cint,
	cstr,
	date_diff,
	floor,
	flt,
	formatdate,
	get_first_day,
	get_last_day,
	get_link_to_form,
	getdate,
	money_in_words,
	rounded,
	nowdate
)
# from erpnext.custom_workflow import validate_workflow_states, notify_workflow_states

class TravelAuthorization(Document):
	def validate(self):

		validate_active_employee(self.employee)
		
		self.validate_travel_dates()
		self.validate_travel_last_day()
		self.validate_exchange_rate()
		self.set_status()
		self.make_travel_advance()
		self.validate_estimated_amount()
		#validate_workflow_states(self)

	def on_update(self):
		self.check_date_overlap()
		self.validate_duplicate_entry()

	def on_submit(self):
		if self.advance_amount: 
			self.post_journal_entry()

	def on_cancel(self):
		self.set_status(update=True)

	def set_status(self, update=False):
		status_map = {0: "Draft", 1: "Submitted", 2: "Cancelled"}
		status = status_map.get(self.docstatus, "Unknown")

		if update:
			self.db_set("status", status)
		else:
			self.status = status

	def validate_estimated_amount(self):
		if flt(self.advance_amount) > flt(self.estimated_amount):
			frappe.throw("your estimate amount is less than advance amount ")

	def post_journal_entry(self):
		advance_account = frappe.db.get_value("Company", self.company, "travel_advance_account")
		bank_account = frappe.db.get_value("Branch", self.branch, "expense_bank_account")
		#frappe.throw(advance_account)

		if not advance_account:
			frappe.throw(
				"Travel Advance Account is not set for {}. Please configure it in the Company.".format(
					frappe.get_desk_link("Company", self.company)
				),
				title="Missing Travel Advance Account"
			)

		if not bank_account:
			frappe.throw(
				"Default Expense Bank Account is not set for {}. Please configure it in the Branch.".format(
					frappe.get_desk_link("Branch", self.branch)
				),
				title="Missing Expense Bank Account"
			)

		# Posting Journal Entry
		accounts = []
		accounts.append({
			"account": advance_account,
			"debit": flt(self.advance_amount),
			"debit_in_account_currency": flt(self.advance_amount),
			"cost_center": self.cost_center,
			"party_check": 1,
			"party_type": "Employee",
			"party": self.employee,
			"is_advance": "Yes",
			"reference_type": "Travel Authorization",
			"reference_name": self.name,
		})

		accounts.append({
			"account": bank_account,
			"credit": flt(self.advance_amount),
			"credit_in_account_currency": flt(self.advance_amount),
			"cost_center": self.cost_center,
		})

		je = frappe.new_doc("Journal Entry")
		
		voucher_type = "Bank Entry"
		naming_series = "Bank Payment Voucher"
		
		je.update({
				"doctype": "Journal Entry",
				"voucher_type": voucher_type,
				"naming_series": naming_series,
				"title": "Travel Advance - "+self.employee,
				"user_remark": "Travek Advance - "+self.employee,
				"posting_date": nowdate(),
				"company": self.company,
				"accounts": accounts,
				"branch": self.branch
		})

		if self.advance_amount:
			je.save(ignore_permissions = True)
			# self.db_set("journal_entry", je.name)
			# self.db_set("journal_entry_status", "Forwarded to accounts for processing payment on {0}".format(now_datetime().strftime('%Y-%m-%d %H:%M:%S')))
			# frappe.msgprint(_('{} posted to accounts').format(frappe.get_desk_link(je.doctype,je.name)))

	def validate_travel_dates(self):
		for item in self.get("items", []):
			if cint(item.halt):
				self._validate_halt_entry(item)
			else:
				self._validate_travel_entry(item)

	def _validate_halt_entry(self, item):
		if not item.halt_at:
			frappe.throw(
				_("Row#{}: <b>Halt at</b> is mandatory.").format(item.idx),
				title="Missing Halt Information"
			)
		if not item.to_date:
			frappe.throw(
				_("Row#{0}: <b>Till Date</b> is mandatory.").format(item.idx),
				title="Invalid Date"
			)
		if item.to_date < item.from_date:
			frappe.throw(
				_("Row#{0}: <b>Till Date</b> cannot be earlier than <b>From Date</b>.").format(item.idx),
				title="Invalid Date"
			)

	def _validate_travel_entry(self, item):
		if not (item.travel_from and item.travel_to):
			frappe.throw(
				_("Row#{0}: <b>Travel From</b> and <b>Travel To</b> are mandatory.").format(item.idx),
				title="Missing Travel Information"
			)
		item.to_date = item.from_date  # Ensuring `to_date` is set for non-halt cases

	def check_date_overlap(self):
		overlap_query = """
			SELECT t1.idx, t2.idx AS overlap_idx
			FROM `tabTravel Authorization Item` t1
			JOIN `tabTravel Authorization Item` t2
			ON t1.parent = t2.parent
			AND t1.name != t2.name
			AND t1.from_date <= t2.to_date
			AND t1.to_date >= t2.from_date
			WHERE t1.parent = %s
		"""

		overlaps = frappe.db.sql(overlap_query, (self.name,), as_dict=True)
		if overlaps:
			first_overlap = overlaps[0]
			frappe.throw(
				_("Row#{}: Dates are overlapping with dates in Row#{}").format(
					first_overlap["idx"], first_overlap["overlap_idx"]
				),
				title="Date Overlap Detected"
			)

	def validate_duplicate_entry(self):
		duplicate_query = """
			SELECT 
				t3.idx, 
				t1.name AS authorization_name, 
				t2.from_date, 
				t2.to_date 
			FROM `tabTravel Authorization` t1
			JOIN `tabTravel Authorization Item` t2 ON t2.parent = t1.name
			JOIN `tabTravel Authorization Item` t3 ON t3.parent = %s
			WHERE 
				t1.employee = %s
				AND t1.docstatus != 2
				AND t1.workflow_state != 'Rejected'
				AND t1.name != %s
				AND t2.from_date <= t3.to_date
				AND t2.to_date >= t3.from_date
		"""

		overlaps = frappe.db.sql(duplicate_query, (self.name, self.employee, self.name), as_dict=True)

		if overlaps:
			t = overlaps[0]
			frappe.throw(
				_("Row #{}: This request overlaps with {} ({} to {}).").format(
					t.idx, 
					frappe.get_desk_link("Travel Authorization", t.authorization_name), 
					t.from_date, 
					t.to_date
				),
				title=_("Duplicate Travel Entry")
			)

	def validate_travel_last_day(self):
		items = self.get("items", [])
		if len(items) > 1:
			for item in items:
				item.is_last_day = 0
			items[-1].is_last_day = 1

	def validate_exchange_rate(self):
		if not self.exchange_rate and self.travel_type != 'Domestic':
			frappe.throw(_("Exchange Rate cannot be zero."), title="Missing Exchange Rate")

	@frappe.whitelist()
	def has_travel_claim(self) -> dict[str, bool]:
		ta = frappe.qb.DocType("Travel Claim")

		travel_claim = (
			frappe.qb.from_(ta)
			.select(ta.name)
			.where(
				(ta.docstatus < 2)
				& (ta.travel_authorization == self.name)
			)
		).run(as_dict=True)

		return {
			"has_travel_claim": bool(travel_claim)
		}


	#@frappe.whitelist()
	def make_travel_advance(self):
		"""
		Creates a Travel Advance document linked to the given Travel Authorization.
		"""
		#frappe.throw(self.employee)
		
		#doc = frappe.get_doc(dt, dn)
		no_of_days=0
		# #frappe.throw(str(doc.items[0].country))
		for d in self.items:
			#frappe.msgprint("hi")
			if d.is_last_day==1:
				no_of_day=0
			else:
				
				no_of_day=date_diff(d.to_date, d.from_date) + 1
			no_of_days+=no_of_day


		
		if self.items:
			from_date = self.items[0].from_date
			to_date = self.items[-1].from_date if len(self.items) > 1 else from_date

		employee_grade = frappe.db.get_value("Employee", self.employee, "grade")
		return_day_dsa = frappe.db.get_single_value("HR Settings", "return_day_dsa")
		dsa = frappe.db.get_value("Employee Grade", employee_grade, "dsa")
		#frappe.throw(str(no_of_day))

		if self.travel_type=="International":
			country=frappe.get_doc("DSA Out Country", self.items[0].country)
			if not country:
				frappe.throw("country in not set in DSA OUT Countery")
			grade=False
			for dsa_int in country.country_dsa_detail:
			
				if dsa_int.grade==employee_grade:
							
					dsa = flt(dsa_int.dsa) * self.exchange_rate
					grade=True
					break

			if grade==False:
				frappe.throw("DSa is not net grade")
		
		
		
		self.estimated_amount = flt(dsa) * flt(no_of_days) + (flt(return_day_dsa) /100 * flt(dsa))
		#frappe.throw(str(self.estimated_amount))
		#adv.travel_authorization = doc.name

		#return estimated_amount