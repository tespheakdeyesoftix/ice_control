// Copyright (c) 2025, Tes Pheakdey and contributors
// For license information, please see license.txt

frappe.ui.form.on("Customer", {
    onload: function(frm) {
        if (frm.is_new()) {
            frm.add_child('product_prices', {});
            frm.refresh_field('product_prices');
        }else {

        }


    },
    refresh(frm){
        window.loadCustomerCalenar = false;
        frm.dashboard.clear_headline();
        addCustomButton(frm);
        setIndicator(frm)

        if(window.location.hash == "#tab_customer_calendar")  {
            renderCalender(frm)
        }
        $("#customer-tab_customer_calendar-tab").click(function(){
            renderCalender(frm)
        })

    },



});


function setIndicator(frm) {
    if (frm.is_new()) return;
    frappe.call({
        method: 'ice_control.api.customer.get_customer_dashboard_data',
        args: {
            customer: frm.doc.name
        },
        callback: function (r) {
            if (!r.message) return;
            data = r.message.account_recivable
            // example: r.message.total_quantity
              frm.dashboard.add_indicator(
                __("Opening: {0}", [fmt_money(data.opening || 0)]),
                "blue"
            );

            frm.dashboard.add_indicator(
                __("Debit Amount: {0}", [fmt_money(data.debit_amount || 0)]),
                "blue"
            );

            frm.dashboard.add_indicator(
                __("Payment Amount: {0}", [fmt_money(data.payment_amount || 0)]),
                "green"
            );

            frm.dashboard.add_indicator(
                __("Write Off Amount: {0}", [fmt_money(data.write_off_amount || 0)]),
                "red"
            );
            frm.dashboard.add_indicator(
                __("Balance: {0}", [fmt_money(data.balance)]),
                "green"
            );
        }
    });
}



function addCustomButton(frm){
    frm.add_custom_button(__('Sale Invoices List'), function() {
            frappe.msgprint('view sale invoice list');

    }, __('View'));

    frm.add_custom_button(__('Sale Payment List'), function() {
            frappe.msgprint('view sale invoice list');

    }, __('View'));


    frm.add_custom_button(__('Return Product'), async function() {
            const result = await frappe.borrow_product.onBulkReturnProduct({customer:frm.doc.name});
            if(result){
                frm.refresh();
            }
    }, 'Actions');
}




function renderCalender(frm) {
    if (!window.loadCustomerCalenar){
 frappe.require("calendar.bundle.js", () => {
            render_calendar(frm);
            window.loadCustomerCalenar = true;
        });
    }




}


function render_calendar(frm) {

    const wrapper = frm.fields_dict.html_calendar.$wrapper;
    wrapper.empty();

    const calEl = document.createElement('div');
    calEl.style.minHeight = '500px';
    wrapper.append(calEl);


    const calendar = new frappe.FullCalendar(calEl, {

        plugins: frappe.FullCalendar.Plugins,

        initialView: 'dayGridMonth',

        // initialDate: today,

        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,timeGridWeek,timeGridDay'
        },

        dayMaxEvents: 5,
        nowIndicator: true,
        editable: false,
        selectable: false,

		height: "auto",

	events: function(fetchInfo, successCallback, failureCallback) {

            frappe.call({
                method: "ice_control.customer_management.doctype.customer.customer.get_customer_calendar_events",
                args: {
                    start: fetchInfo.startStr,
                    end: fetchInfo.endStr,
                    customer: frm.doc.name
                },

                callback: function(r) {
                    successCallback(r.message || []);
                },

                error: function(err) {
                    failureCallback(err);
                    frappe.msgprint({
                        title: __("Error"),
                        message: __("Failed to load customer calendar"),
                        indicator: "red"
                    });
                }
            });
        },

		eventContent: function(arg) {

            const event = arg.event;
            const props = event.extendedProps;
            let html = "";
            // SALE
            if (props.doctype === "Sale") {
                html = `
                    <div style="padding: 2px 4px;">
                        <div>
                            <b>Sale</b>
                        </div>
                        <div>
                            <b>${event.title}</b>
                        </div>
                        <div style="font-size: 11px;">
                            Total:
                            ${format_currency(props.total_amount || 0)}
                        </div>

                    </div>
                `;
            }
            // SALE PAYMENT
            else if (props.doctype === "Sale Payment") {
                html = `
                    <div style="padding: 2px 4px;">
                        <div>
                            <b>Sale Payment</b>
                        </div>
                        <div>
                            <b>${event.title}</b>
                        </div>

                        <div style="font-size: 11px;">
                            Paid:
                            ${format_currency(props.payment_amount || 0)}
                        </div>
                    </div>
                `;
            }
            return {
                html: html
            };
        },

		eventClick: function(info) {

            info.jsEvent.preventDefault();
            const event = info.event;
            const props = event.extendedProps;
            // Open Sale / Sale Payment
            frappe.set_route(
                "Form",
                props.doctype,
                event.id
            );
        }
    });
    calendar.render();
	frm.customer_calendar = calendar;
}
