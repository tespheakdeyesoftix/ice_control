// Copyright (c) 2026, Tes Pheakdey and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Journal Entry", {
// 	refresh(frm) {

// 	},
// });
// Copyright (c) 2026, Tes Pheakdey and contributors
// For license information, please see license.txt

frappe.ui.form.on("Journal Entry", {
    refresh(frm) {
        on_refresh_or_load(frm);
    },
    onload: function(frm) {
        on_refresh_or_load(frm);
    },

    party_type(frm){
        override_party_child(frm, "party_type");
    },
    party(frm){
        override_party_child(frm, "party");
    },
});

///Account Entries Item
frappe.ui.form.on('Journal Entry Account', {
	form_render:function(frm, cdt,cdn){
        //
	},
    account_entries_add: function(frm, cdt, cdn) {
        const row = locals[cdt][cdn];

        // Set default values from parent
        frappe.model.set_value(cdt, cdn, 'party_type', frm.doc.party_type || '');
        frappe.model.set_value(cdt, cdn, 'party', frm.doc.party || '');

        // Optional: mark fields as read-only based on parent values
        const grid = frm.fields_dict.account_entries.grid;

        // Delay setting read-only to make sure row UI is ready
        setTimeout(() => {
            ['party_type', 'party'].forEach(fieldname => {
                grid.get_field(fieldname).df.read_only = false; // reset first
                if (frm.doc[fieldname]) {
                    grid.get_field(fieldname).df.read_only = true;
                }
            });
            frm.refresh_field('account_entries');
        }, 1000);
    },
    account_entries_remove: function(frm, cdt, cdn) {
        update_summary(frm)
    },
    //
    debit(frm, cdt, cdn){
        update_summary(frm)
    },
    credit(frm, cdt, cdn){
        update_summary(frm)
    }

});

///method on refresh or load
function on_refresh_or_load(frm){

    frm.set_query('party_type', function() {
        return {
            filters: {
                name: ['in', ['Customer', 'Vendor']]
            }
        };
    });

    ///child table query filter
    frm.fields_dict['account_entries'].grid.get_field('party_type').get_query = function(doc, cdt, cdn) {
        return {
            filters: {
                name: ['in', ['Customer', 'Vendor']]
            }
        };
    };
    frm.fields_dict['account_entries'].grid.get_field('account').get_query = function(doc, cdt, cdn) {
        return {
            filters: {
                is_group: 0
            }
        };
    };

    ///end child table query filter


    frm.fields_dict.account_entries.grid.update_docfield_property('party_type', 'read_only', !!frm.doc.party_type);

    frm.fields_dict.account_entries.grid.update_docfield_property('party', 'read_only', !!frm.doc.party);

}


///method override party type on journal entry account
function override_party_child(frm, action) {
    // Fields to update
    const fields = ["party_type", "party"];

    // Step 1: Make both fields editable (remove read-only)
    fields.forEach(fieldname => {
        frm.fields_dict.account_entries.grid.update_docfield_property(fieldname, 'read_only', false);
    });

    // Step 2: Loop through child rows and update values
    frm.doc.account_entries.forEach(function(row) {
        if (action === "party_type") {
            row.party_type = frm.doc.party_type;
            if (!frm.doc.party_type) {
                row.party = ""; // Clear party in child if party_type is empty
            }
        } else if (action === "party") {
            row.party = frm.doc.party;
        }
    });

    // Step 3: Reapply read-only status based on whether parent has party_type
    if(!!frm.doc.party_type){
        frm.fields_dict.account_entries.grid.update_docfield_property('party_type', 'read_only', true);
    }
    if(!!frm.doc.party){
        frm.fields_dict.account_entries.grid.update_docfield_property('party', 'read_only', true);
    }


    // Step 4: Refresh the child table to show changes
    frm.refresh_field("account_entries");
}


///method update summary
function update_summary(frm){
    if(frm.doc.account_entries == undefined){
        frm.set_value('account_entries', []);
    }
    let total_debit = 0;
    let total_credit = 0;
    frm.doc.account_entries.forEach(row => {
        total_debit += flt(row.debit);
        total_credit += flt(row.credit);
    });

    // Set values to parent fields (if any)
    frm.set_value('total_debit', total_debit);
    frm.set_value('total_credit', total_credit);
    frm.set_value('balance', (total_debit||0) - (total_credit||0));
}

