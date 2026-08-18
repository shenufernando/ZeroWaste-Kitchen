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


// Include the cuisine_type when sending the JS fetch request
const payload = {
    ingredients: selectedIngredients,
    meal_type: document.getElementById('mealType').value,
    cuisine_type: document.getElementById('cuisineType').value,
    max_time: document.getElementById('maxTime').value
};

// Use this to display the YouTube video in the Recipe Card Display section:
if (recipe.youtube_query) {
    const videoSearchUrl = `https://www.youtube.com/embed?listType=search&list=${encodeURIComponent(recipe.youtube_query)}`;
    html += `
        <div class="mt-4">
            <h6 class="fw-bold"><i class="bi bi-youtube text-danger me-2"></i>Watch Video Guide:</h6>
            <div class="ratio ratio-16x9 rounded shadow-sm overflow-hidden mt-2">
                <iframe src="${videoSearchUrl}" title="Recipe Video" allowfullscreen></iframe>
            </div>
        </div>
    `;
}