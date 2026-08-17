document.addEventListener('DOMContentLoaded', function () {
    const searchInput = document.querySelector('input[placeholder="Search items..."]');
    if (searchInput) {
        searchInput.addEventListener('keyup', function () {
            const filter = searchInput.value.toLowerCase();
            const rows = document.querySelectorAll('tbody tr');

            rows.forEach(row => {
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(filter) ? '' : 'none';
            });
        });
    }
});