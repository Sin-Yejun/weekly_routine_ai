document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('routine-form');
    const generatePromptBtn = document.getElementById('generate-prompt-btn');
    const generateVllmBtn = document.getElementById('generate-vllm-btn');
    const generateOpenAiBtn = document.getElementById('generate-openai-btn');
    const loadingIndicator = document.getElementById('loading-indicator');

    const promptOutputEl = document.getElementById('prompt-output'); // Now a textarea
    const rawOutputEl = document.getElementById('raw-output');
    const formattedOutputEl = document.getElementById('formatted-output');

    const showLoading = (isLoading) => {
        loadingIndicator.classList.toggle('hidden', !isLoading);
        generatePromptBtn.disabled = isLoading;
        generateVllmBtn.disabled = isLoading;
        generateOpenAiBtn.disabled = isLoading;
    };

    // 1. Generate Prompt Button
    if (generatePromptBtn) {
        generatePromptBtn.addEventListener('click', async () => {
            showLoading(true);
            promptOutputEl.value = 'Generating prompt...';
            formattedOutputEl.textContent = 'Your generated routine will appear here.';
            rawOutputEl.textContent = 'The raw JSON from the model will appear here.';

            const formData = new FormData(form);
            const data = {};
            formData.forEach((value, key) => { data[key] = value; });
            formData.forEach((value, key) => { data[key] = value; });

            try {
                const response = await fetch('/api/generate-prompt', {
                const response = await fetch('/api/generate-prompt', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data),
                });
                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
                }
                const result = await response.json();
                promptOutputEl.value = result.prompt || 'Failed to generate prompt.';
            } catch (error) {
                console.error('Error generating prompt:', error);
                promptOutputEl.value = `An error occurred while generating the prompt: ${error.message}`;
            } finally {
                showLoading(false);
            }
        });
    }

    // 2. Inference Buttons (vLLM and OpenAI)
    const handleInference = async (endpoint) => {
        showLoading(true);
        formattedOutputEl.textContent = 'Generating...';
        rawOutputEl.textContent = '';

        const formData = new FormData(form);
        const userConfig = {};
        formData.forEach((value, key) => { userConfig[key] = value; });
        
        const prompt = promptOutputEl.value;
        if (!prompt || prompt.startsWith('The prompt sent')) {
            rawOutputEl.textContent = 'Please generate a prompt first.';
            showLoading(false);
            return;
        }

        const payload = {
            ...userConfig, // Send user config for temp, max_tokens, etc.
            prompt: prompt  // Send the (potentially edited) prompt
        };

        try {
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            formattedOutputEl.textContent = result.formatted_summary || 'No formatted summary returned.';
            rawOutputEl.textContent = result.response || 'No raw response returned.';

        } catch (error) {
            console.error('Error generating routine:', error);
            formattedOutputEl.textContent = `An error occurred: ${error.message}`;
        } finally {
            showLoading(false);
        }
    };

    if (generateVllmBtn) {
        generateVllmBtn.addEventListener('click', () => handleInference('/api/infer'));
    }

    if (generateOpenAiBtn) {
        generateOpenAiBtn.addEventListener('click', () => handleInference('/api/generate-openai'));
    }
});