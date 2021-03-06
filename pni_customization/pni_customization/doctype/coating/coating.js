// Copyright (c) 2020, Jigar Tarpara and contributors
// For license information, please see license.txt

frappe.ui.form.on('Coating', {
	refresh: function(frm) {
		if(!frm.doc.__islocal && frm.doc.status == 'Pending For Stock Entry'){
			var finish_btn = frm.add_custom_button(__('Create Manufacture Entry'), function(){
				process_production(frm);
			});
			finish_btn.addClass('btn-primary')
		}
		
		if(!cur_frm.doc.__islocal){
			frm.set_query("item", "coating_scrap", function () {
				return {
					filters: {"item_group": frm.doc.__onload.scrapitemgroup}
				}
			});
			frm.set_query("item_out", "coating_table", function () {
				return {
					filters: {"item_group": frm.doc.__onload.coated_item_group}
				}
			});
		}
	},
	setup: function (frm) {
		frm.set_query("work_station", function () {
			return {
				filters: {"paper_blank_machine_type": "Coating"}
			}
		});
		frm.set_query("reel_in", "coating_table", function () {
			return {
				filters: {"docstatus": 1, "status": "In Stock", "coated_reel": 0}
			}
		});
	},
	work_station: function(frm){
		if(frm.doc.work_station){
			frappe.call({
				"method": "frappe.client.get",
				args: {
					doctype: "Workstation",
					name: frm.doc.work_station
				},
				callback: function (data) {
					frappe.model.set_value(frm.doctype,frm.docname, "fg_warehouse", data.message.fg_warehouse);
					frappe.model.set_value(frm.doctype,frm.docname, "scrap_warehouse", data.message.scrap_warehouse);
					frappe.model.set_value(frm.doctype,frm.docname, "src_warehouse", data.message.src_warehouse);
				}
			});
		}
	},
});

var process_production = function (frm) {
	frappe.call({
		doc: frm.doc,
		method: "manufacture_entry",
		args:{
			"status": status
		},
		callback: function(r) {
			if (r.message){
				var doclist = frappe.model.sync(r.message);
				frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
			}
		}
	});
}
