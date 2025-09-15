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
            formattedOutputEl.textContent = 'OpenAI 답변이 여기에 표시됩니다.';
            rawOutputEl.textContent = 'vllm의 답변이 여기에 표시됩니다.';

            const formData = new FormData(form);
            const data = {};
            formData.forEach((value, key) => { data[key] = value; });

            try {
                const response = await fetch('/api/generate-prompt', {
                    method: 'POST',
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
    const handleVllmInference = async () => {
        showLoading(true);
        rawOutputEl.textContent = 'Generating...';

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
            ...userConfig,
            prompt: prompt
        };

        try {
            const response = await fetch('/api/infer', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            let outputContent = 'No response returned.'; // Default value

            if (result.formatted_summary) {
                outputContent = "--- Formatted Output ---\n" + result.formatted_summary;
                if (result.response) {
                    outputContent += "\n\n--- Raw Model Output ---\n" + result.response;
                }
            } else if (result.response) {
                outputContent = "--- Raw Model Output ---\n" + result.response;
            }
            rawOutputEl.textContent = outputContent;

        } catch (error) {
            console.error('Error generating vLLM routine:', error);
            rawOutputEl.textContent = `An error occurred: ${error.message}`;
        } finally {
            showLoading(false);
        }
    };

    const handleOpenAiInference = async () => {
        showLoading(true);
        formattedOutputEl.textContent = 'Generating...';

        const formData = new FormData(form);
        const userConfig = {};
        formData.forEach((value, key) => { userConfig[key] = value; });
        
        const prompt = promptOutputEl.value;
        if (!prompt || prompt.startsWith('The prompt sent')) {
            formattedOutputEl.textContent = 'Please generate a prompt first.';
            showLoading(false);
            return;
        }

        const payload = {
            ...userConfig,
            prompt: prompt
        };

        try {
            const response = await fetch('/api/generate-openai', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            let outputContent = 'No response returned.'; // Default value

            if (result.formatted_summary) {
                outputContent = "--- Formatted Output ---\n" + result.formatted_summary;
                if (result.response) {
                    outputContent += "\n\n--- Raw Model Output ---\n" + result.response;
                }
            } else if (result.response) {
                outputContent = "--- Raw Model Output ---\n" + result.response;
            }
            
            formattedOutputEl.textContent = outputContent;

        } catch (error) {
            console.error('Error generating OpenAI routine:', error);
            formattedOutputEl.textContent = `An error occurred: ${error.message}`;
        } finally {
            showLoading(false);
        }
    };

    if (generateVllmBtn) {
        generateVllmBtn.addEventListener('click', handleVllmInference);
    }

    if (generateOpenAiBtn) {
        generateOpenAiBtn.addEventListener('click', handleOpenAiInference);
    }
});