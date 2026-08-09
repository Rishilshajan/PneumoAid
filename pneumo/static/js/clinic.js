document.addEventListener('DOMContentLoaded', function() {
    // Tab functionality
    const tabTriggers = document.querySelectorAll('.tabs-trigger');
    const tabContents = document.querySelectorAll('.tabs-content');
    
    tabTriggers.forEach(trigger => {
        trigger.addEventListener('click', () => {
            const value = trigger.dataset.value;
            
            // Update active tab
            tabTriggers.forEach(t => t.dataset.state = '');
            trigger.dataset.state = 'active';
            
            // Show corresponding content
            tabContents.forEach(content => {
                content.style.display = content.dataset.value === value ? 'block' : 'none';
            });
        });
    });

    // Auto-format blood pressure input
    document.querySelector('input[name="blood_pressure"]')?.addEventListener('input', function(e) {
        this.value = this.value.replace(/[^\d/]/g, '');
    });
});