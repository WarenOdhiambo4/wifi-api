document.addEventListener('DOMContentLoaded', () => {
    const urlParams = new URLSearchParams(window.location.search);
    // Router passes client MAC via URL parameter, e.g. ?mac=AA:BB:CC:DD:EE:FF
    const userMac = urlParams.get('mac') || 'AA:BB:CC:DD:EE:FF'; 
    document.getElementById('mac-display').textContent = userMac;

    let selectedPlan = '1H';
    const planButtons = document.querySelectorAll('.plan-btn');

    planButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            planButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            selectedPlan = btn.dataset.plan;
        });
    });

    const form = document.getElementById('payment-form');
    const statusMsg = document.getElementById('status-message');
    const payBtn = document.getElementById('pay-btn');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const phone = document.getElementById('phone').value;

        payBtn.disabled = true;
        statusMsg.style.color = '#38bdf8';
        statusMsg.textContent = 'Sending M-Pesa STK Push to your phone...';

        try {
            // Send real user data to AWS n8n production webhook
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
                statusMsg.style.color = '#4ade80';
                statusMsg.textContent = 'Please enter your M-Pesa PIN on your phone to activate internet.';
            } else {
                throw new Error('Failed to initiate payment.');
            }
        } catch (error) {
            statusMsg.style.color = '#f87171';
            statusMsg.textContent = 'Error connecting to payment server. Try again.';
            payBtn.disabled = false;
        }
    });
});