# -*- coding: utf-8 -*-
# Copyright (c) 2020, Jigar Tarpara and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime, time_diff_in_hours,flt

class Slitting(Document):
	def validate(self):
		# self.validate_reel_size()
		if self.scrap_weight_approved:
			if not self.approved_by:
				self.approved_by =  frappe.session.user
		else:
			self.approved_by = ""
		if self.all_weight_approved:
			if not self.all_weight_approved_by:
				self.all_weight_approved_by =  frappe.session.user
		else:
			self.all_weight_approved_by = ""
		self.manage_reel()
		if self.end_dt and self.start_dt:
			hours = time_diff_in_hours(self.end_dt, self.start_dt)
			frappe.db.set(self, 'operation_hours', hours)

	def onload(self):
		paper_blank_setting = frappe.get_doc("Paper Blank Settings","Paper Blank Settings")
		self.set_onload("scrapitemgroup", paper_blank_setting.slitting_scrap)

	def validate_reel_weight(self):
		"""
			calculate contain total weight out
			calculate_intial contain total weight in
		"""
		calculate = {}
		calculate_intial = {}
		for row in self.slitting_table:
			weight = calculate.get(row.reel_in, 0)
			calculate.update({row.reel_in:(weight + row.weight_out)})
			calculate_intial.update({row.reel_in: row.weight})
		
		all_reel_in_weight, all_reel_out_weight, scrap = 0,0,0
		
		for data in calculate_intial:
			all_reel_in_weight += calculate_intial[data]
			all_reel_out_weight += calculate[data]
		 
		for data in self.slitting_scrap:
			scrap += data.qty
		threshold = float(float(all_reel_in_weight) *  0.01)

		if threshold < scrap:
			if not self.scrap_weight_approved :
				frappe.throw("Need Approval Scrap is greater then threshold " + str(threshold))
		if all_reel_in_weight > (float(all_reel_out_weight) + float(scrap) + float(threshold)):
			if not self.all_weight_approved:
				frappe.throw("[All] Need Approval Scrap is greater then threshold " + str(threshold))
	def validate_reel_size(self):
		calculate = {}
		calculate_intial = {}
		for row in self.slitting_table:
			size = calculate.get(row.reel_in, 0)
			calculate.update({row.reel_in:(size + row.size_out)})
			calculate_intial.update({row.reel_in: row.size})
		for data in calculate_intial:
			if calculate[data] != calculate_intial[data]:
				frappe.throw("Reel size didn't match to out put")

	def manage_reel(self):
		# setting = frappe.get_doc("PNI Settings","PNI Settings")
		for data in self.slitting_table:
			reel_in = frappe.get_doc("Reel",data.reel_in)
			if data.type != "Bottom Reel":
				if not data.reel_out:
					doc = frappe.get_doc({
						"doctype": "Reel",
						"status": "Draft",
						"process_prefix": "SL",
						"posting_date": self.date
					})
					doc.insert()
					data.reel_out = doc.name
				else:
					doc = frappe.get_doc("Reel",data.reel_out)
				
				doc.custom_id = data.custom_id
				doc.supplier_reel_id = reel_in.supplier_reel_id
				doc.item = data.item_out if not data.half_reel else reel_in.item
				doc.printed_item = reel_in.printed_item
				doc.warehouse = self.fg_warehouse if not data.half_reel else self.src_warehouse
				doc.type = data.type if data.type else reel_in.type
				doc.brand = reel_in.brand
				doc.blank_weight = reel_in.blank_weight
				doc.coated_reel =  reel_in.coated_reel
				doc.printed_reel = reel_in.printed_reel
				doc.printed_weight = reel_in.printed_weight
				doc.coated_weight = reel_in.coated_weight
				doc.weight = data.weight_out
				doc.type = data.type if data.type else reel_in.type
				if data.half_reel:
					doc.item = reel_in.item
					doc.warehouse = self.src_warehouse
				doc.save()
	
	def manage_reel_tracking(self):
		for data in self.slitting_table:
			doc = frappe.get_doc({
				"doctype": "Reel Tracking",
				"status": "Draft",
				"reel": data.reel_in,
				"reel_process": "Slitting",
				"date": frappe.utils.nowdate(),
				"time": frappe.utils.nowtime(),
				"out_reel": data.reel_out,
				"status": "Slitting Submit",
				"process_reference": self.name,
				"note": "" if not data.half_reel else "Half UnSlitted Reel"
			})
			doc.insert(ignore_permissions=True)
	
	def cancel_reel_tracking(self):
		for data in self.slitting_table:
			doc = frappe.get_doc({
				"doctype": "Reel Tracking",
				"status": "Draft",
				"reel": data.reel_in,
				"reel_process": "Slitting",
				"date": frappe.utils.nowdate(),
				"time": frappe.utils.nowtime(),
				"out_reel": data.reel_out,
				"status": "Slitting Cancel",
				"process_reference": self.name,
				"note" : "" if not data.half_reel else "Half UnSlitted Reel"
			})
			doc.insert(ignore_permissions=True)

	def on_submit(self):
		self.validate_reel_weight()
		# if (not self.end_dt) or (not self.end_dt):
		# 	frappe.throw("Please Select Operation Start and End Time")
		for item in self.slitting_table:
			if (not item.reel_in) :
				frappe.throw("Reel is Compulsory")
			if item.type != "Bottom Reel" and not item.reel_out:
				frappe.throw("Reel is Compulsory")
		for data in self.slitting_table:
			if not data.weight_out:
				frappe.throw("Weight Can't be empty")
			reel_in = frappe.get_doc("Reel",data.reel_in)
			reel_in.status = "Consume"
			reel_in.save()
			if data.type != "Bottom Reel":
				reel_out = frappe.get_doc("Reel",data.reel_out)
				reel_out.status = "In Stock"
				reel_out.save()
				reel_out.submit()
		self.manage_reel_tracking()
		frappe.db.set(self, 'status', 'Pending For Stock Entry')
	
	def on_cancel(self):
		stock_entry = frappe.db.sql("""select name from `tabStock Entry`
			where pni_reference = %s and docstatus = 1""", self.name)
		if stock_entry:
			frappe.throw(_("Cannot cancel because submitted Stock Entry \
			{0} exists").format(stock_entry[0][0]))
		frappe.db.set(self, 'status', 'Cancelled')
		for data in self.slitting_table:
			reel_in = frappe.get_doc("Reel",data.reel_in)
			reel_in.status = "In Stock"
			reel_in.save()
			if data.type != "Bottom Reel":
				reel_out = frappe.get_doc("Reel",data.reel_out)
				reel_out.cancel()
		self.cancel_reel_tracking()
	def complete_entry(self):
		self.status = "Completed"
		self.save()
		return "Success"
	def manufacture_entry(self):
		return self.make_stock_entry()
	
	def make_stock_entry(self):
		stock_entry = frappe.new_doc("Stock Entry")
		stock_entry.pni_reference_type = "Slitting"
		stock_entry.pni_reference = self.name
		stock_entry.pni_shift = self.shift_time
		stock_entry.posting_date = self.date
		stock_entry.set_posting_time = True
		
		stock_entry.stock_entry_type = "Manufacture"
		stock_entry = self.set_se_items_finish(stock_entry)

		return stock_entry.as_dict()
	
	def get_valuation_rate(self, item):
		""" Get weighted average of valuation rate from all warehouses """

		total_qty, total_value, valuation_rate = 0.0, 0.0, 0.0
		for d in frappe.db.sql("""select actual_qty, stock_value from `tabBin`
			where item_code=%s""", item, as_dict=1):
				total_qty += flt(d.actual_qty)
				total_value += flt(d.stock_value)

		if total_qty:
			valuation_rate =  total_value / total_qty

		if valuation_rate <= 0:
			last_valuation_rate = frappe.db.sql("""select valuation_rate
				from `tabStock Ledger Entry`
				where item_code = %s and valuation_rate > 0
				order by posting_date desc, posting_time desc, creation desc limit 1""", item)

			valuation_rate = flt(last_valuation_rate[0][0]) if last_valuation_rate else 0

		if not valuation_rate:
			valuation_rate = frappe.db.get_value("Item", item, "valuation_rate")

		return flt(valuation_rate)
	
	def set_se_items_finish(self, se):
		se.from_warehouse = self.src_warehouse
		se.to_warehouse = self.fg_warehouse

		raw_material_cost = 0
		operating_cost = 0
		reelin = []
		for item in self.slitting_table:
			if item.reel_in not in reelin:
				se = self.set_se_items(se, item, se.from_warehouse, None, False, reel_in= True)
				reelin.append(item.reel_in)
				raw_material_cost += self.get_valuation_rate(item.item) * float(item.weight)
		
		production_cost = raw_material_cost + operating_cost
		
		#calc total_qty and total_sale_value
		qty_of_total_production = 0
		total_sale_value = 0
		for item in self.slitting_table:
			if item.weight_out > 0:
				qty_of_total_production = float(qty_of_total_production) + item.weight_out

		#add Stock Entry Items for produced goods and scrap
		for item in self.slitting_table:
			warehouse = se.to_warehouse if not item.half_reel else se.from_warehouse
			if item.type == "Bottom Reel" and item.finish_good_warehouse:
				warehouse = item.finish_good_warehouse
			se = self.set_se_items(se, item, None, warehouse, True, qty_of_total_production,
			total_sale_value, production_cost, reel_out = True)

		for item in self.slitting_scrap:
			se = self.set_se_items(se, item, None, self.scrap_warehouse, False, scrap_item = True)

		return se
	
	def set_se_items(self, se, item, s_wh, t_wh, calc_basic_rate=False, 
		qty_of_total_production=None, total_sale_value=None, production_cost=None, 
		reel_in = False, reel_out = False, scrap_item = False):
		# if item.quantity > 0:
		item_from_reel = {}
		class Empty:
			pass  
		if reel_in:
			item_from_reel = frappe.get_doc("Reel",item.reel_in)
		if reel_out:
			if item.type != "Bottom Reel":
				item_from_reel = frappe.get_doc("Reel",item.reel_out)
			else:
				item_from_reel = Empty()
				item_from_reel.item = item.item_out
				item_from_reel.weight = item.weight_out
		if scrap_item:
			item_from_reel = Empty()
			item_from_reel.item = item.item
			item_from_reel.weight = item.qty

		expense_account, cost_center = frappe.db.get_values("Company", self.company, \
			["default_expense_account", "cost_center"])[0]
		item_name, stock_uom, description = frappe.db.get_values("Item", item_from_reel.item, \
			["item_name", "stock_uom", "description"])[0]

		item_expense_account, item_cost_center = frappe.db.get_value("Item Default", {
			'parent': item_from_reel.item, 
			'company': self.company},\
			["expense_account", "buying_cost_center"])

		if not expense_account and not item_expense_account:
			frappe.throw(
				_("Please update default Default Cost of Goods Sold Account for company {0}").format(self.company))

		if not cost_center and not item_cost_center:
			frappe.throw(_("Please update default Cost Center for company {0}").format(self.company))

		se_item = se.append("items")
		se_item.item_code = item_from_reel.item
		se_item.qty = item_from_reel.weight
		se_item.s_warehouse = s_wh
		se_item.t_warehouse = t_wh
		se_item.item_name = item_name
		se_item.description = description
		se_item.uom = stock_uom
		se_item.stock_uom = stock_uom

		se_item.expense_account = item_expense_account or expense_account
		se_item.cost_center = item_cost_center or cost_center

		# in stock uom
		se_item.transfer_qty = item_from_reel.weight
		se_item.conversion_factor = 1.00

		item_details = se.run_method( "get_item_details",args = (frappe._dict(
			{
				"item_code": item_from_reel.item, 
				"company": self.company, 
				"uom": stock_uom, 
				's_warehouse': s_wh})), for_update=True)

		for f in ("uom", "stock_uom", "description", "item_name", "expense_account",
		"cost_center", "conversion_factor"):
			se_item.set(f, item_details.get(f))

		if calc_basic_rate:
			print(production_cost)
			print(qty_of_total_production)
			se_item.basic_rate = production_cost/qty_of_total_production
			# if self.costing_method == "Physical Measurement":
			# 	se_item.basic_rate = production_cost/qty_of_total_production
			# elif self.costing_method == "Relative Sales Value":
			# 	sale_value_of_pdt = frappe.db.get_value("Item Price", {
			# 		"item_code":item_from_reel.item}, "price_list_rate")
			# 	se_item.basic_rate=(float(sale_value_of_pdt)*float(production_cost))/float(total_sale_value)
		if scrap_item:
			se_item.basic_rate = self.get_valuation_rate(item_from_reel.item)
		return se
	
	def get_out_item(self, reel_in, size):
		reel =  frappe.get_doc("Reel",reel_in)
		reel.item
		# stock_entry = frappe.db.sql("""select name from `tabStock Entry`
		# 	# where pni_reference = %s and docstatus = 1""", self.name)
		

