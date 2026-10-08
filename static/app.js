document.addEventListener('DOMContentLoaded', () => {
    // 1. EXTRACT MAC ADDRESS FROM ROUTER URL PARAMETER
    const urlParams = new URLSearchParams(window.location.search);
    const userMac = urlParams.get('mac') || 'AA:BB:CC:DD:EE:FF';
    document.getElementById('mac-display').textContent = userMac;

    // 2. SMOOTH HERO BACKGROUND FADE CYCLE
    const slides = document.querySelectorAll('.slide');
    let currentSlide = 0;

    setInterval(() => {
        slides[currentSlide].classList.remove('active');
        currentSlide = (currentSlide + 1) % slides.length;
        slides[currentSlide].classList.add('active');
    }, 3500);

    // 3. PLAN SELECTION LOGIC
    let selectedPlan = '24H';
    const planNameDisplay = document.getElementById('selected-plan-name');
    const planCards = document.querySelectorAll('.plan-card');

    planCards.forEach(card => {
        const btn = card.querySelector('.select-plan-btn');
        
        btn.addEventListener('click', () => {
            planCards.forEach(c => c.classList.remove('active'));
            card.classList.add('active');
            
            selectedPlan = card.dataset.plan;
            const price = card.dataset.price;
            const title = card.dataset.title;
            
            planNameDisplay.textContent = `${title} — KES ${price}`;
            
            document.getElementById('checkout-section').scrollIntoView({ behavior: 'smooth' });
        });
    });

    // 4. M-PESA PAYMENT SUBMISSION TO N8N PRODUCTION WEBHOOK
    const form = document.getElementById('payment-form');
    const statusMsg = document.getElementById('status-message');
    const payBtn = document.getElementById('pay-btn');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const phoneInput = document.getElementById('phone').value.trim();

        payBtn.disabled = true;
        statusMsg.style.color = '#cc3333';
        statusMsg.textContent = 'Initiating M-Pesa STK Push prompt...';

        try {
            const response = await fetch('https://n8n.kabisakabisa.store/webhook-test/customer-select-plan', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    plan_id: selectedPlan,
                    phone: phoneInput,
                    mac_address: userMac
                })
            });

            if (response.ok) {
                statusMsg.style.color = '#16a34a';
                statusMsg.textContent = 'STK Push sent! Please enter your M-Pesa PIN on your phone to connect.';
            } else {
                throw new Error('STK Push failed');
            }
        } catch (error) {
            statusMsg.style.color = '#cc3333';
            statusMsg.textContent = 'Network error. Please verify your phone number and try again.';
            payBtn.disabled = false;
        }
    });
});