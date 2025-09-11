document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('routine-form');
    const generatePromptBtn = document.getElementById('generate-prompt-btn');
    
    // Sections and Buttons
    const promptOutputSection = document.getElementById('prompt-output-section');
    const promptDisplay = document.getElementById('prompt-display');
    const generateVllmBtn = document.getElementById('generate-vllm-btn');
    const generateOpenaiBtn = document.getElementById('generate-openai-btn');

    // Output elements
    const rawOutputEl = document.getElementById('raw-output');

    // Step 1: Generate Prompt
    if (form) {
        form.addEventListener('submit', async (event) => {
            event.preventDefault();
            
            setLoadingState(true, 'prompt');
            clearOutputs();
            promptOutputSection.classList.add('hidden');

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
                promptDisplay.value = result.prompt;
                promptOutputSection.classList.remove('hidden');

            } catch (error) {
                console.error('Error generating prompt:', error);
                rawOutputEl.textContent = `An error occurred: ${error.message}`;
            } finally {
                setLoadingState(false, 'prompt');
            }
        });
    }

    // Step 2: Generate Routine (VLLM or OpenAI)
    generateVllmBtn.addEventListener('click', () => handleRoutineGeneration('/api/infer'));
    generateOpenaiBtn.addEventListener('click', () => handleRoutineGeneration('/api/generate-openai'));

    async function handleRoutineGeneration(apiEndpoint) {
        const prompt = promptDisplay.value;
        if (!prompt) {
            alert("Prompt is empty!");
            return;
        }

        const formData = new FormData(form);
        const data = {};
        formData.forEach((value, key) => { data[key] = value; });
        data.prompt = prompt;

        setLoadingState(true, 'routine');
        rawOutputEl.textContent = 'Generating...';

        try {
            const response = await fetch(apiEndpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
            }

            const result = await response.json();

            let output = "";
            if (result.formatted_summary) {
                output += "--- Formatted Summary ---\n" + result.formatted_summary + "\n\n";
            }
            if (result.response) {
                output += "--- Raw Model Output ---" + result.response;
            }
            rawOutputEl.textContent = output || 'No response returned.';

        } catch (error) {
            console.error('Error generating routine:', error);
            rawOutputEl.textContent = `An error occurred: ${error.message}`;
        } finally {
            setLoadingState(false, 'routine');
        }
    }

    function setLoadingState(isLoading, type) {
        if (type === 'prompt') {
            generatePromptBtn.disabled = isLoading;
            generatePromptBtn.textContent = isLoading ? 'Generating...' : 'Generate Prompt';
        } else if (type === 'routine') {
            generateVllmBtn.disabled = isLoading;
            generateOpenaiBtn.disabled = isLoading;
        }
    }

    function clearOutputs() {
        rawOutputEl.textContent = 'The raw JSON from the model will appear here.';
        promptDisplay.value = '';
    }
});