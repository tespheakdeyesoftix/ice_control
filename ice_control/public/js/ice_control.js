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

        frm.print_doc = function () {
       
            printDoc(frm)
        };
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


function printDoc(frm,report_name="") {
    let d = new frappe.ui.Dialog({
        title: __('Print Report') + " " + frm.doc.name,
        size: 'large', // 'small', 'large', 'extra-large'
        fields: [
            {
                fieldtype: 'HTML',
                fieldname: 'iframe_html',
                label: 'Iframe'
            }
        ]
    });

    d.fields_dict.iframe_html.$wrapper.html(`
                <iframe src="/embed/doctype-server-report?doctype=${frm.doctype}&docname=${frm.docname}&report_name=${report_name}" 
                        width="100%" 
                        height="${window.innerHeight - 150}px" 
                        frameborder="0"
                        style="border-radius: 8px;">
                </iframe>
            `);

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