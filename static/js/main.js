const menuToggle = document.querySelector('.menu-toggle');
const navigation = document.querySelector('#primary-navigation');

if (menuToggle && navigation) {
    const setMenuOpen = (isOpen) => {
        menuToggle.setAttribute('aria-expanded', String(isOpen));
        menuToggle.setAttribute(
            'aria-label',
            isOpen ? 'Close navigation menu' : 'Open navigation menu'
        );
        navigation.classList.toggle('is-open', isOpen);
    };

    menuToggle.addEventListener('click', () => {
        const isExpanded = menuToggle.getAttribute('aria-expanded') === 'true';
        setMenuOpen(!isExpanded);
    });

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && menuToggle.getAttribute('aria-expanded') === 'true') {
            setMenuOpen(false);
            menuToggle.focus();
        }
    });

    document.addEventListener('click', (event) => {
        if (
            menuToggle.getAttribute('aria-expanded') === 'true'
            && !navigation.contains(event.target)
            && !menuToggle.contains(event.target)
        ) {
            setMenuOpen(false);
        }
    });

    navigation.addEventListener('click', (event) => {
        if (event.target.closest('a')) {
            setMenuOpen(false);
        }
    });

    const desktopNavigation = window.matchMedia('(min-width: 761px)');
    desktopNavigation.addEventListener('change', () => setMenuOpen(false));
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
