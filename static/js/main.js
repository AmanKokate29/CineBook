const menuToggle = document.querySelector('.menu-toggle');
const navigation = document.querySelector('#primary-navigation');

if (menuToggle && navigation) {
    menuToggle.addEventListener('click', () => {
        const isExpanded = menuToggle.getAttribute('aria-expanded') === 'true';
        menuToggle.setAttribute('aria-expanded', String(!isExpanded));
        navigation.classList.toggle('is-open', !isExpanded);
    });

    navigation.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && navigation.classList.contains('is-open')) {
            navigation.classList.remove('is-open');
            menuToggle.setAttribute('aria-expanded', 'false');
            menuToggle.focus();
        }
    });
}

const seatSelector = document.querySelector('[data-seat-selector]');

if (seatSelector) {
    const seatCheckboxes = Array.from(
        seatSelector.querySelectorAll('.seat-checkbox:not(:disabled)')
    );
    const selectedSeats = seatSelector.querySelector('[data-selected-seats]');
    const seatTotal = seatSelector.querySelector('[data-seat-total]');
    const unitPrice = Number(seatSelector.dataset.unitPrice);

    const updateSeatSummary = () => {
        const selected = seatCheckboxes.filter((checkbox) => checkbox.checked);
        const labels = selected.map((checkbox) => checkbox.dataset.seatLabel);
        const totalCents = Math.round(unitPrice * 100) * selected.length;

        selectedSeats.textContent = labels.length ? labels.join(', ') : 'None selected';
        seatTotal.textContent = (totalCents / 100).toFixed(2);
    };

    seatCheckboxes.forEach((checkbox) => {
        checkbox.addEventListener('change', updateSeatSummary);
    });

    updateSeatSummary();
}
