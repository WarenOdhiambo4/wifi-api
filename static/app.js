document.addEventListener('DOMContentLoaded', () => {
    // 1. EXTRACT MAC ADDRESS FROM URL PARAMS
    const urlParams = new URLSearchParams(window.location.search);
    const userMac = urlParams.get('mac') || 'AA:BB:CC:DD:EE:FF';
    document.getElementById('mac-display').textContent = userMac;

    // 2. HERO IMAGE SLIDER ANIMATION SEQUENCE
    const sliderWrapper = document.querySelector('.slider-wrapper');
    
    // Step A: Image 2 comes from right and meets Image 1
    setTimeout(() => {
        sliderWrapper.classList.add('meet');
    }, 500);

    // Step B: Image 2 disappears leaving Image 1 to take full width
    setTimeout(() => {
        sliderWrapper.classList.remove('meet');
        sliderWrapper.classList.add('full');
    }, 3000);

    // Step C: Regular 3-second cycle toggle
    setInterval(() => {
        sliderWrapper.classList.toggle('meet');
    }, 3000);

    // 3. PLAN SELECTION LOGIC
    let selectedPlan = '1H';
    const planNameDisplay = document.getElementById('selected-plan-name');
    const selectBtns = document.querySelectorAll('.select-plan-btn');

    selectBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            selectedPlan = btn.dataset.plan;
            const price = btn.dataset.price;
            const planTitle = btn.parentElement.querySelector('h3').textContent;
            
            planNameDisplay.textContent = `${planTitle} (KES ${price})`;
            
            // Scroll down to checkout form smoothly
            document.getElementById('payment-form').scrollIntoView({ behavior: 'smooth' });
        });
    });

    // 4. FORM SUBMISSION TO N8N PRODUCTION WEBHOOK
    const form = document.getElementById('payment-form');
    const statusMsg = document.getElementById('status-message');
    const payBtn = document.getElementById('pay-btn');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const phone = document.getElementById('phone').value;

        payBtn.disabled = true;
        statusMsg.style.color = '#cc3333';
        statusMsg.textContent = 'Sending M-Pesa STK Push prompt to your phone...';

        try {
            const response = await fetch('https://n8n.kabisakabisa.store/webhook/customer-select-plan', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    plan_id: selectedPlan,
                    phone: phone,
                    mac_address: userMac
                })
            });

            if (response.ok) {
                statusMsg.style.color = '#16a34a';
                statusMsg.textContent = 'STK Push sent! Enter your M-Pesa PIN on your phone to unlock internet access.';
            } else {
                throw new Error('Failed to initiate STK Push');
            }
        } catch (error) {
            statusMsg.style.color = '#cc3333';
            statusMsg.textContent = 'Error connecting to payment gateway. Please try again.';
            payBtn.disabled = false;
        }
    });
});