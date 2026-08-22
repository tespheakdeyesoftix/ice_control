// Copyright (c) 2026, Tes Pheakdey and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Block Ice Produce", {
// 	refresh(frm) {

// 	},
// });

// Copyright (c) 2025, Tes Pheakdey and contributors
// For license information, please see license.txt

frappe.ui.form.on("Block Ice Produce", {
	refresh(frm) {
        renderBlockGrid(frm)
	},

});

function renderBlockGrid(frm){
    if(!frm.is_new()){
        frm.doc.produce_quantity.forEach(r=>{
            const el = document.querySelector("#" +  r.block_grid_number)
            if (el){
                generateGrid(frm,r )
            }
        })
    }


    var produce_table = $('[data-fieldname="produce_quantity"]');
    produce_table.find('.grid-footer').remove();
}



function generateGrid(frm,produce_row) {
    const el_id = produce_row.block_grid_number
    const rows = produce_row.row;
    const  cols = produce_row.column;
    const  data = JSON.parse(produce_row.produce_data)
    const container = document.getElementById(el_id);
    container.innerHTML = "";

    let table = document.createElement("table");
    table.classList.add("block-ice-produce-grid")
    table.style.userSelect = "none";
    table.style.width = "100%";

    let thead = document.createElement("thead");
    let headRow = document.createElement("tr");
    let corner = document.createElement("th");
    corner.style.width = "30px";
    headRow.appendChild(corner);

    function colToLetter(num) {
        let str = "";
        while (num > 0) {
            let rem = (num-1)%26;
            str = String.fromCharCode(65+rem)+str;
            num = Math.floor((num-1)/26);
        }
        return str;
    }

    for (let c=1; c<=cols; c++){
        let th = document.createElement("th");
        th.textContent = colToLetter(c);
        th.dataset.col = c;
        th.style.padding="4px";
        th.style.cursor="pointer";
        headRow.appendChild(th);
    }
    thead.appendChild(headRow);
    table.appendChild(thead);

    let tbody = document.createElement("tbody");
    for (let r=0;r<rows;r++){
        let tr = document.createElement("tr");
        let rowHeader = document.createElement("th");
        rowHeader.textContent = r+1;
        rowHeader.dataset.row = r;
        rowHeader.style.padding="4px";
        rowHeader.style.cursor="pointer";
        tr.appendChild(rowHeader);

        for(let c=0;c<cols;c++){
            let td=document.createElement("td");
            td.textContent = data[r]?.[c] ?? 0;
            if(Number(td.textContent)!=0){
                td.classList.add("has-value")
                if(Number(td.textContent)<0){
                    console.log(Number(td.textContent))
                    td.classList.add("defected")
                }
            }else {
                td.classList.remove("has-value")
                td.classList.remove("defected")
            }
            td.dataset.row = r;
            td.dataset.col = c;
            td.style.height="40px";
            td.style.textAlign="center";
            td.style.cursor="pointer";
            tr.appendChild(td);
        }
        tbody.appendChild(tr);
    }
    table.appendChild(tbody);
    container.appendChild(table);

    // --- selection
    let isMouseDown = false;
    let startCell = null;

    function clearSelection() { table.querySelectorAll("td").forEach(td=>{
        td.classList.remove("selected");
       highlightValue();
    }); }
    function highlightValue() {
        table.querySelectorAll("td").forEach(td=>{
            // td.classList.remove("selected")
            if(Number(td.textContent)!=0){
                td.classList.add("has-value")
                if(Number(td.textContent)<0){
                    console.log(Number(td.textContent))
                    td.classList.add("defected")
                }
            }else {
                td.classList.remove("has-value")
                td.classList.remove("defected")
            }
        });
    }
    function getSelectedCells() { return Array.from(table.querySelectorAll("td.selected")); }
    function setCellValue(cells,value){ cells.forEach(td=>td.textContent=value); highlightValue();}
    function getTotalSum(){
        let sum=0;
        for(let r=0;r<rows;r++){
            for(let c=0;c<cols;c++){
                let td = tbody.querySelector(`td[data-row='${r}'][data-col='${c}']`);
                if(Number(td.textContent||0)>=0) sum += Number(td.textContent||0);
            }
        }
        return sum;
    }

    function getTotalDefected(){
        let sum=0;
        for(let r=0;r<rows;r++){
            for(let c=0;c<cols;c++){
                let td = tbody.querySelector(`td[data-row='${r}'][data-col='${c}']`);
                if(Number(td.textContent||0)<0) sum += Number(td.textContent||0);
            }
        }
        return Math.abs( sum);
    }

    function getData(){
        let res=[];
        for(let r=0;r<rows;r++){
            let rowArr=[];
            for(let c=0;c<cols;c++){
                let td = tbody.querySelector(`td[data-row='${r}'][data-col='${c}']`);
                rowArr.push(Number(td.textContent));
            }
            res.push(rowArr);
        }
        return res;
    }

    // --- mouse events
    tbody.querySelectorAll("td").forEach(td=>{
        td.addEventListener("mousedown",(e)=>{
            if(e.ctrlKey){ td.classList.toggle("selected"); }
            else { clearSelection(); td.classList.add("selected"); startCell=td; isMouseDown=true;}
        });
        td.addEventListener("mouseenter",(e)=>{
            if(isMouseDown && startCell){
                clearSelection();
                let r1=Number(startCell.dataset.row), c1=Number(startCell.dataset.col);
                let r2=Number(td.dataset.row), c2=Number(td.dataset.col);
                let rr1=Math.min(r1,r2), rr2=Math.max(r1,r2);
                let cc1=Math.min(c1,c2), cc2=Math.max(c1,c2);
                for(let r=rr1;r<=rr2;r++){
                    for(let c=cc1;c<=cc2;c++){
                        tbody.querySelector(`td[data-row='${r}'][data-col='${c}']`).classList.add("selected");
                    }
                }
            }
        });
    });
    table.addEventListener("mouseup",()=>{ isMouseDown=false; startCell=null; });

    // --- row/column header click
    tbody.querySelectorAll("th").forEach(th=>{
        th.addEventListener("click",(e)=>{
            let r=th.dataset.row;
            let rowCells = tbody.querySelectorAll(`td[data-row='${r}']`);
            if(e.ctrlKey){ rowCells.forEach(td=>td.classList.toggle("selected")); }
            else { clearSelection(); rowCells.forEach(td=>td.classList.add("selected")); }
        });
    });
    thead.querySelectorAll("th[data-col]").forEach(th=>{
        th.addEventListener("click",(e)=>{
            let c=th.dataset.col-1;
            let colCells = tbody.querySelectorAll(`td[data-col='${c}']`);
            if(e.ctrlKey){ colCells.forEach(td=>td.classList.toggle("selected")); }
            else { clearSelection(); colCells.forEach(td=>td.classList.add("selected")); }
        });
    });

    // --- buttons
    const btnContainer=document.createElement("div");
    btnContainer.style.marginTop="10px";
    let btnClear=document.createElement("button");
    btnClear.classList.add("btn", "btn-warning");
    btnClear.textContent=__("Clear Value");
    btnClear.onclick=()=>{setCellValue(getSelectedCells(),0);
    produce_row.total_produce_quantity = getTotalSum()
    produce_row.produce_data = JSON.stringify(getData())
    frm.refresh_field("produce_quantity")
        frm.dirty();
    };

    let btnAssign1=document.createElement("button");
    btnAssign1.textContent=__("Produce QTY 1");
        btnAssign1.style.marginLeft="10px";
        btnAssign1.classList.add("btn", "btn-default");
        btnAssign1.onclick=()=>{
        setCellValue(getSelectedCells(),1);
            produce_row.total_produce_quantity = getTotalSum()
            produce_row.defected_quantity = getTotalDefected()
            produce_row.produce_data = JSON.stringify(getData())

            frm.refresh_field("produce_quantity")
            frm.dirty();
        };

    let btnAssign2=document.createElement("button");
        btnAssign2.classList.add("btn", "btn-default");
        btnAssign2.textContent=__("Produce QTY 2"); btnAssign2.style.marginLeft="10px"; btnAssign2.onclick=()=>{
        setCellValue(getSelectedCells(),2);
        produce_row.total_produce_quantity = getTotalSum()
        produce_row.defected_quantity = getTotalDefected()
        produce_row.produce_data = JSON.stringify(getData())
        frm.refresh_field("produce_quantity")
        frm.dirty();

    };

    let btnAssignDefected=document.createElement("button");
         btnAssignDefected.textContent=__("Defected QTY");
         btnAssignDefected.style.marginLeft="10px";
         btnAssignDefected.classList.add("btn", "btn-danger");
        btnAssignDefected.onclick=()=>{
        setCellValue(getSelectedCells(),-1);
        produce_row.total_produce_quantity = getTotalSum()
        produce_row.defected_quantity = getTotalDefected()
        produce_row.produce_data = JSON.stringify(getData())
        frm.refresh_field("produce_quantity")
        frm.dirty();

    };


    let buttons =[btnClear,btnAssign1];

    if(produce_row.total_produce_per_day>1){

        buttons.push(btnAssign2);
    }
        buttons.push(btnAssignDefected);

    if(frm.doc.docstatus==0) buttons.forEach(b=>btnContainer.appendChild(b));

    container.appendChild(btnContainer);

    return { setCellValue,getTotalSum,getData }; // return API per grid
}


