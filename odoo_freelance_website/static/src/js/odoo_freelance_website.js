/** @odoo-module **/

document.addEventListener('DOMContentLoaded', () => {
    const forms = document.querySelectorAll('.ofw_form');
    forms.forEach((form) => {
        form.addEventListener('submit', () => {
            const button = form.querySelector('.ofw_submit');
            if (!button) {
                return;
            }
            button.classList.add('is-loading');
            button.setAttribute('disabled', 'disabled');
        });
    });
});
