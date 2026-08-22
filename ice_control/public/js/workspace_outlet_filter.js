frappe.provide('frappe.workspace');

frappe.workspace.OutletSidebarFilter = class OutletSidebarFilter {
    constructor() {
        // Outlet info comes from boot (instant, no API call)
        this.outlet = frappe.boot.employee_outlet;
        this.outlet_type = frappe.boot.employee_outlet_type; // 'block_ice', 'tube_ice', null

        this.init();
    }

    init() {
        // Skip for Administrator
        if (frappe.session.user === 'Administrator') return;

        if (!this.outlet) {
            console.warn('[OutletFilter] No outlet found for user:', frappe.session.user);
            return;
        }

        console.log('[OutletFilter] Outlet:', this.outlet, '| Type:', this.outlet_type);
        this.applyFilter();
    }

    applyFilter() {
        // Workspace renders dynamically, so we watch for it
        const observer = new MutationObserver((mutations, obs) => {
            const sidebar = document.querySelector('.layout-side-section');
            if (sidebar && sidebar.querySelectorAll('.standard-sidebar-item').length > 0) {
                this.filterItems();
            }
        });

        observer.observe(document.body, { childList: true, subtree: true });

        // Run once immediately too
        setTimeout(() => this.filterItems(), 600);
    }

    filterItems() {
        const items = document.querySelectorAll(
            '.layout-side-section .standard-sidebar-item, ' +
            '.layout-side-section .sidebar-item-container'
        );

        if (items.length === 0) return;

        items.forEach(item => {
            const labelEl = item.querySelector('.sidebar-item-label') || item.querySelector('a');
            if (!labelEl) return;

            const label = labelEl.innerText.trim();
            let shouldHide = false;

            // ==========================================
            // ADD YOUR RULES HERE
            // ==========================================

            // Example 1: If employee is BLOCK ICE, hide TUBE ICE items
            if (this.outlet_type === 'block_ice') {
                // Put Khmer labels that ONLY Tube Ice should see
                const tubeIceOnly = [
                    // 'បញ្ជីទិញទឹកកក',   // <-- uncomment and change
                    // 'របាយការណ៍ទឹកកកអនាម័យ' // <-- add your labels
                ];
                if (tubeIceOnly.some(t => label.includes(t))) {
                    shouldHide = true;
                }
            }

            // Example 2: If employee is TUBE ICE, hide BLOCK ICE items
            if (this.outlet_type === 'tube_ice') {
                // Put Khmer labels that ONLY Block Ice should see
                const blockIceOnly = [
                    // 'បញ្ជីទិញអង្ករ',   // <-- uncomment and change
                    // 'របាយការណ៍ទឹកកកដើម'  // <-- add your labels
                ];
                if (blockIceOnly.some(t => label.includes(t))) {
                    shouldHide = true;
                }
            }

            // Example 3: Hide by exact outlet name
            // if (this.outlet === 'ទឹកកកដើម' && label === 'Some Item') {
            //     shouldHide = true;
            // }

            if (shouldHide) {
                item.style.display = 'none';
                console.log('[OutletFilter] Hidden:', label);
            }
        });
    }
};

// Run when Workspace page loads
$(document).on('page-change', function() {
    if (frappe.get_route()[0] === 'Workspaces') {
        setTimeout(() => {
            new frappe.workspace.OutletSidebarFilter();
        }, 300);
    }
});
