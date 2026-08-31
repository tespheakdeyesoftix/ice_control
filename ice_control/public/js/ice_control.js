if (frappe.session.user !== "Administrator" && frappe.ui.SidebarHeader) {
	const original_switcher_items =
		frappe.ui.SidebarHeader.prototype.switcher_items;

	const original_menu_items =
		frappe.ui.SidebarHeader.prototype.menu_items;

	frappe.ui.SidebarHeader.prototype.switcher_items = function () {
		const app = this.sidebar.get_sidebar_app();

		if (app?.app_name === "ice_control") {
			return [];
		}

		return original_switcher_items.call(this);
	};

	frappe.ui.SidebarHeader.prototype.menu_items = function () {
		const items = original_menu_items.call(this);
		const app = this.sidebar.get_sidebar_app();

		if (app?.app_name === "ice_control") {
			return items.filter((item) => item.name !== "edit-sidebar");
		}

		return items;
	};
}

frappe.ui.form.on("*", {
    onload: function(frm) {
        if (!frm.is_new()) {
            $(`[id="page-${frm.doctype}"] .nav-item button`).click(function(){
                
                render_html_template(frm,$(this).attr("id"));
            })
            
        }
    },
    refresh(frm) {
        // reset tabLoaded state
        window.loadTab = {}
        // Keep Frappe's standard print handler as the default. Only replace it
        // when this DocType has an enabled document report configured.
        if (!frm.__standard_print_doc) {
            frm.__standard_print_doc = frm.print_doc;
        }
        frm.print_doc = frm.__standard_print_doc;

        getDoctypeReports(frm.doctype).then(function (reports) {
            const reportPath = reports.length ? reports[0].report_url : "";
            if (reportPath) {
                frm.print_doc = function () {
                    printDoc(frm, reportPath);
                };
            }
        });

        cleanFormSidebar();
        hideMenus();
       
       
        let tabID = null
        
        if($(`[id="page-${frm.doctype}"] .nav-link.active`).length>0){
            tabID = $(".nav-link.active").attr("id")
        }

        render_html_template(frm,tabID);

        render_custom_sidebar(frm);
        
    }
});


function printDoc(frm,report_path="") {

    openReportViewerDialog(frm.doctype, frm.docname, report_path);
}

function getDoctypeReports(doctype) {
    return frappe.call({
        method: "ice_control.api.bold_reports.get_doctype_reports",
        args: { doctype: doctype }
    }).then(function (response) {
        return response.message || [];
    });
}

async function printDoctypeReport(doctype, docName) {
    if (!doctype || !docName) {
        frappe.msgprint(__("A document type and document name are required to print the report."));
        return;
    }

    try {
        const reports = await getDoctypeReports(doctype);
        const reportPath = reports.length ? reports[0].report_url : "";

        if (!reportPath) {
            frappe.msgprint(__("No document report is configured for {0}.", [doctype]));
            return;
        }

        openReportViewerDialog(doctype, docName, reportPath);
    } catch (error) {
        console.error("Unable to load the document report", error);
        frappe.msgprint(__("Unable to load the document report for {0}.", [doctype]));
    }
}

window.printDoctypeReport = printDoctypeReport;

function openReportViewerDialog(doctype, docName, reportPath) {

    const viewerUrl = new URL(
        "/assets/ice_control/report_server_viewer.html",
        window.location.origin
    );
    viewerUrl.searchParams.set("doctype", doctype);
    viewerUrl.searchParams.set("doc_name", docName);
    viewerUrl.searchParams.set("report_path", reportPath);

    let d = new frappe.ui.Dialog({
        title: __('Print Report') + " " + docName,
        size: 'large', // 'small', 'large', 'extra-large'
        fields: [
            {
                fieldtype: 'HTML',
                fieldname: 'iframe_html',
                label: 'Iframe'
            }
        ]
    });
  
    const iframe = $("<iframe>", {
        src: viewerUrl.toString(),
        width: "100%",
        height: `${window.innerHeight - 150}px`,
        frameborder: 0,
        title: __("Report Viewer")
    }).css("border-radius", "8px");

    d.fields_dict.iframe_html.$wrapper.empty().append(iframe);

    d.show();
    d.$wrapper.find('.modal-dialog').css({
        "width": "90%",
        "max-width": "90%",

    });
}

function render_html_template(frm,tabID){
                if (frm.doctype==="DocType") return;
                
                let html_fields = []
                if(tabID){
                     
                     if (window.loadTab["_" + frm.doc.name + tabID] ) return;
                
                const tabContentID= $("#" + tabID).attr("aria-controls");
                const tabContentEl= $("#" + tabContentID)
                window.loadTab["_" + frm.doc.name + tabID] = true

                html_fields = tabContentEl.find('.frappe-control[data-fieldtype="HTML"]')
                    .map(function () {
                        return $(this).data('fieldname');
                    })
                    .get();
                }else {
                    html_fields = $(`[id="page-${frm.doctype}"]`).find('.frappe-control[data-fieldtype="HTML"]')
                    .map(function () {
                        return $(this).data('fieldname');
                    })
                    .get();
                   
                }
                
                
                if(html_fields.length==0) return;

                frappe.dom.freeze(__("Loading..."));

                frappe.call("ice_control.setting.doctype.html_template.html_template.get_html_template",{
                    fields:html_fields,
                    doc:frm.doc
                }).then(r=>{
                    html_fields.forEach(f => {
                        if (r.message.hasOwnProperty(f)){
                            frm.fields_dict[f].$wrapper.html(r.message[f]);
                        }
                    });
                    frappe.dom.unfreeze()
                }).catch(err=>{
                     frappe.dom.unfreeze()
                })

}

//render side bar

function render_custom_sidebar(frm){
    if(!frm.is_new()){
         
        frappe.call("ice_control.setting.doctype.html_template.html_template.get_custom_sidebar_template",{
        doc:frm.doc
    }).then(r=>{
        if(r.message){
            frm.sidebar.sidebar.append(r.message);
        }
    })
    }
    
}

//clean form sidebar
function cleanFormSidebar(){
      setTimeout(() => {
            $('.form-sidebar .sidebar-section.form-shared').remove();
            $('.form-sidebar .sidebar-section.form-assignments').remove();
            $('.form-sidebar .sidebar-section .avatar-group').parent().parent().remove();
        }, 100);
}




function hideMenus(menus=["Email","Show Link","Copy to Clipboard","Customize","Edit DocType","Jump to field","Rename","Undo","Redo"]){
    if(frappe.session.user=="Administrator") return
      setTimeout(() => {
            // Find and hide the Email dropdown item
            menus.forEach(m=>{
  $(`.dropdown-item .menu-item-label:contains(${__(m)})`)
                .closest('li')
                .remove();
            })
          
             

        }, 500);
}
