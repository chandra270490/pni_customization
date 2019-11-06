frappe.ui.form.on('Sales Order', {
	refresh: function(frm) {
		cur_frm.cscript.add_item_dialog("Sales Order Item")	
	}
});

frappe.ui.form.on('Sales Invoice', {
	refresh: function(frm) {
		cur_frm.cscript.add_item_dialog("Sales Invoice Item")	
	}
});

frappe.ui.form.on('Purchase Order', {
	refresh: function(frm) {
		cur_frm.cscript.add_item_dialog("Purchase Order Item")	
	}
});

frappe.ui.form.on('Purchase Invoice', {
	refresh: function(frm) {
		cur_frm.cscript.add_item_dialog("Purchase Invoice Item")	
	}
});

cur_frm.cscript.add_item_dialog = function(item_table) {
	cur_frm.add_custom_button(__("Add Item by Attribute"), function() {
		prompt_for_item_template("items", "Item Varient Selection", true, function (values) {
			get_attribute_values("items", "Add Attribute Values", values, function(values, item){
				prompt_attribute_values("items", "Add Attribute Values", values, item, function(values, item) {
					frappe.call({
						method: "pni_customization.utils.get_item",
						args: { 
							values: values,
							item: item
						},
						callback: (response) => {
							show_alert('This Item Found ' + response.message.name, 5);
							var d = frappe.model.add_child(cur_frm.doc, item_table, "items");
							d.item_code = response.message.name;
							d.qty = 1;
							d.delivery_date = cur_frm.doc.delivery_date;
							d.item_name = response.message.item_name;
							d.description = response.message.description;
							d.uom = response.message.stock_uom;
							debugger;
							refresh_field("items");
						}
					})
				})
			})
		});
	}).addClass('btn-primary');
}
var prompt_for_item_template = function(table, title, qty_required, callback) {
	frappe.prompt(
		[
			{
				'fieldname': 'item_varient', 
				'fieldtype': 'Link', 
				'options': 'Item', 
				'label': 'Item',
				get_query: () => {		
					return {
						filters: {
							has_variants: true
						}
					};
				},
			},
		],
		function(values){
			callback(values);
		},
		__(title),
		__('Add Item')
	)
}

var get_attribute_values = function(table, title, Rdata, callback_for_get_prompt) {
	frappe.call({
		method: "pni_customization.utils.get_item_data",
		args: { 
			item: Rdata.item_varient
		},
		callback: (response) => {
			callback_for_get_prompt(response, Rdata.item_varient);
		}
	});
}

var prompt_attribute_values = function(table, title, response, item, callback) {
	var data = [];
	$.each(response.message.attribute_data || [], function(i, row) {
		if( row.numeric_values == false) {
			data.push(
				{
					'fieldname': i, 
					'fieldtype': 'Select', 
					'label': i,
					'options' : row.values
				}
			)
		} else {
			data.push(
				{
					'fieldname': i, 
					'fieldtype': 'Float', 
					'label': i,
				}
			)
		}
	})
	frappe.prompt(
		data,
		function(values){
			callback(values, item);
		},
		'Item Varient Selection For ' + response.message.item,
		'Add Item'
	)	
}