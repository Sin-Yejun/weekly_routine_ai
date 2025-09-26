document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('routine-form');
    const levelSelect = document.getElementById('level');
    const toolCheckboxes = document.querySelectorAll('#tools-filter input[name="tools"]');

    const updateToolSelection = (level) => {
        toolCheckboxes.forEach(checkbox => {
            if (level === 'Beginner') {
                checkbox.checked = checkbox.value !== 'Barbell';
            } else{
                checkbox.checked = true;
            }
            // } else if (level === 'Novice') {
            //     checkbox.checked = true;
            // } else { // Intermediate, Advanced, Elite
            //     checkbox.checked = checkbox.value !== 'Bodyweight';
            // }
        });
    };

    // Add event listener for level changes
    if (levelSelect) {
        levelSelect.addEventListener('change', (event) => {
            updateToolSelection(event.target.value);
        });
    }

    // Set initial state on page load
    if (levelSelect) {
        updateToolSelection(levelSelect.value);
    }

    const generatePromptBtn = document.getElementById('generate-prompt-btn');
    const generateVllmBtn = document.getElementById('generate-vllm-btn');
    const generateOpenAiBtn = document.getElementById('generate-openai-btn');
    const loadingIndicator = document.getElementById('loading-indicator');
    const sortToggle = document.getElementById('sort-toggle');

    const promptOutputEl = document.getElementById('prompt-output');
    const rawOutputEl = document.getElementById('raw-output');
    const formattedOutputEl = document.getElementById('formatted-output');

    // Store for both outputs
    let vllmRoutines = { unsorted: '', sorted: '' };
    let openAiRoutines = { unsorted: '', sorted: '' };

    const showLoading = (isLoading) => {
        loadingIndicator.classList.toggle('hidden', !isLoading);
        generatePromptBtn.disabled = isLoading;
        generateVllmBtn.disabled = isLoading;
        generateOpenAiBtn.disabled = isLoading;
    };

    const updateOutput = (element, routines) => {
        const isSorted = sortToggle.checked;
        const content = isSorted ? routines.sorted : routines.unsorted;
        element.textContent = content || 'No content available.';
    };

    sortToggle.addEventListener('change', () => {
        updateOutput(rawOutputEl, vllmRoutines);
        updateOutput(formattedOutputEl, openAiRoutines);
    });

    // 1. Generate Prompt Button
    if (generatePromptBtn) {
        generatePromptBtn.addEventListener('click', async () => {
            showLoading(true);
            promptOutputEl.value = 'Generating prompt...';
            rawOutputEl.textContent = 'vllm의 답변이 여기에 표시됩니다.';
            formattedOutputEl.textContent = 'OpenAI 답변이 여기에 표시됩니다.';
            vllmRoutines = { unsorted: '', sorted: '' };
            openAiRoutines = { unsorted: '', sorted: '' };

            const formData = new FormData(form);
            const data = {};
            formData.forEach((value, key) => {
                if (key === 'tools') {
                    if (!data[key]) {
                        data[key] = [];
                    }
                    data[key].push(value);
                } else {
                    data[key] = value;
                }
            });

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

    // 2. Generic Inference Handler
    const handleInference = async (apiEndpoint, outputElement, routineStorage) => {
        showLoading(true);
        outputElement.textContent = 'Generating...';

        const formData = new FormData(form);
        const userConfig = {};
        formData.forEach((value, key) => {
            if (key === 'tools') {
                if (!userConfig[key]) {
                    userConfig[key] = [];
                }
                userConfig[key].push(value);
            } else {
                userConfig[key] = value;
            }
        });
        
        const prompt = promptOutputEl.value;
        if (!prompt || prompt.startsWith('The prompt sent')) {
            outputElement.textContent = 'Please generate a prompt first.';
            showLoading(false);
            return;
        }

        const payload = { ...userConfig, prompt };

        try {
            const response = await fetch(apiEndpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            
            if (result.formatted_summary && typeof result.formatted_summary === 'object') {
                routineStorage.unsorted = "--- Formatted Output ---\n" + result.formatted_summary.unsorted;
                routineStorage.sorted = "--- Formatted Output (Sorted) ---\n" + result.formatted_summary.sorted;
                
                if (result.response) {
                    const rawSuffix = "\n\n--- Raw Model Output ---\n" + result.response;
                    routineStorage.unsorted += rawSuffix;
                    routineStorage.sorted += rawSuffix;
                }
            } else {
                const fallbackContent = result.response ? "--- Raw Model Output ---\n" + result.response : 'No valid response returned.';
                routineStorage.unsorted = fallbackContent;
                routineStorage.sorted = fallbackContent;
            }
            
            updateOutput(outputElement, routineStorage);

        } catch (error) {
            console.error(`Error generating routine via ${apiEndpoint}:`, error);
            outputElement.textContent = `An error occurred: ${error.message}`;
        } finally {
            showLoading(false);
        }
    };

    if (generateVllmBtn) {
        generateVllmBtn.addEventListener('click', () => handleInference('/api/infer', rawOutputEl, vllmRoutines));
    }

    if (generateOpenAiBtn) {
        generateOpenAiBtn.addEventListener('click', () => handleInference('/api/generate-openai', formattedOutputEl, openAiRoutines));
    }
});