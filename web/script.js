document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('routine-form');
    const generateBtn = document.getElementById('generate-btn');
    const loadingIndicator = document.getElementById('loading-indicator');

    const formattedOutputEl = document.getElementById('formatted-output');
    const promptOutputEl = document.getElementById('prompt-output');
    const rawOutputEl = document.getElementById('raw-output');

    if (form) {
        form.addEventListener('submit', async (event) => {
            event.preventDefault();
            
            // Show loading state
            generateBtn.disabled = true;
            loadingIndicator.classList.remove('hidden');
            formattedOutputEl.textContent = 'Generating...';
            promptOutputEl.textContent = '';
            rawOutputEl.textContent = '';

            const formData = new FormData(form);
            const data = {};
            formData.forEach((value, key) => {
                data[key] = value;
            });

            try {
                // Use the vLLM endpoint by default
                const response = await fetch('/api/infer', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(data),
                });

                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
                }

                const result = await response.json();

                // Populate the output fields
                formattedOutputEl.textContent = result.formatted_summary || 'No formatted summary returned.';
                promptOutputEl.textContent = result.prompt || 'No prompt was returned.';
                rawOutputEl.textContent = result.response || 'No raw response returned.';

            } catch (error) {
                console.error('Error generating routine:', error);
                formattedOutputEl.textContent = `An error occurred: ${error.message}`;
            } finally {
                // Hide loading state
                generateBtn.disabled = false;
                loadingIndicator.classList.add('hidden');
            }
        });
    }
});
