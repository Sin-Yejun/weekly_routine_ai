document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('routine-form');
    const levelSelect = document.getElementById('level');
    const freqSelect = document.getElementById('freq');
    const splitTypeSelect = document.getElementById('split-type');
    const toolCheckboxes = document.querySelectorAll('#tools-filter input[name="tools"]');

    const splitConfigs = {
        '2': [
            { id: 'SPLIT', name: '분할 (Upper/Lower)' },
            { id: 'FB', name: '무분할 (Full Body)' }
        ],
        '3': [
            { id: 'SPLIT', name: '분할 (Push/Pull/Legs)' },
            { id: 'FB', name: '무분할 (Full Body)' }
        ],
        '4': [
            { id: 'SPLIT', name: '분할 (4-Day Split)' },
            { id: 'FB', name: '무분할 (Full Body)' }
        ],
        '5': [
            { id: 'SPLIT', name: '분할 (5-Day Split)' },
            { id: 'FB', name: '무분할 (Full Body)' }
        ]
    };

    const updateSplitOptions = (frequency) => {
        splitTypeSelect.innerHTML = ''; // Clear existing options
        const options = splitConfigs[frequency] || [];
        options.forEach(option => {
            const optionEl = document.createElement('option');
            optionEl.value = option.id;
            optionEl.textContent = option.name;
            splitTypeSelect.appendChild(optionEl);
        });
    };

    const updateToolSelection = (level) => {
        toolCheckboxes.forEach(checkbox => {
            if (level === 'Beginner') {
                checkbox.checked = checkbox.value !== 'Barbell';
            } else {
                checkbox.checked = true;
            }
        });
    };

    // Add event listener for frequency changes
    if (freqSelect) {
        freqSelect.addEventListener('change', (event) => {
            updateSplitOptions(event.target.value);
        });
    }

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
    if (freqSelect) {
        updateSplitOptions(freqSelect.value);
    }

    const generatePromptBtn = document.getElementById('generate-prompt-btn');
    const generateVllmBtn = document.getElementById('generate-vllm-btn');
    const generateOpenAiBtn = document.getElementById('generate-openai-btn');
    const generateDetailsBtn = document.getElementById('generate-details-btn');
    const loadingIndicator = document.getElementById('loading-indicator');
    const sortToggle = document.getElementById('sort-toggle');

    const promptOutputEl = document.getElementById('prompt-output');
    const rawOutputEl = document.getElementById('raw-output');
    const formattedOutputEl = document.getElementById('formatted-output');
    const detailsPromptContainer = document.getElementById('details-prompt-container');
    const detailsPromptOutputEl = document.getElementById('details-prompt-output');

    // Store for both outputs
    let vllmRoutines = { unsorted: '', sorted: '', initial_routine: null, model_used: '' };
    let openAiRoutines = { unsorted: '', sorted: '', initial_routine: null, model_used: '' };
    let currentInitialRoutine = { routine: null, model: '' }; // To store the routine and model for detail generation

    const showLoading = (isLoading) => {
        loadingIndicator.classList.toggle('hidden', !isLoading);
        generatePromptBtn.disabled = isLoading;
        generateVllmBtn.disabled = isLoading;
        generateOpenAiBtn.disabled = isLoading;
        if (generateDetailsBtn) {
            generateDetailsBtn.disabled = isLoading;
        }
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
            vllmRoutines = { unsorted: '', sorted: '', initial_routine: null, model_used: '' };
            openAiRoutines = { unsorted: '', sorted: '', initial_routine: null, model_used: '' };
            if (generateDetailsBtn) {
                generateDetailsBtn.classList.add('hidden');
            }
            if (detailsPromptContainer) {
                detailsPromptContainer.classList.add('hidden');
                detailsPromptOutputEl.value = 'The prompt for the details generation will appear here.';
            }
            currentInitialRoutine = { routine: null, model: '' };

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

            data.prevent_weekly_duplicates = document.getElementById('prevent-duplicates-toggle').checked;

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
        if (generateDetailsBtn) {
            generateDetailsBtn.classList.add('hidden');
        }
        if (detailsPromptContainer) {
            detailsPromptContainer.classList.add('hidden');
        }
        currentInitialRoutine = { routine: null, model: '' };

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

        userConfig.prevent_weekly_duplicates = document.getElementById('prevent-duplicates-toggle').checked;
        
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

            // Store the initial routine for detail generation
            if (result.result && result.result.days) {
                routineStorage.initial_routine = result.result;
                routineStorage.model_used = apiEndpoint.includes('infer') ? 'vllm' : 'openai';
                currentInitialRoutine = { routine: result.result, model: routineStorage.model_used }; // Update global reference
                if (generateDetailsBtn) {
                    generateDetailsBtn.classList.remove('hidden');
                }
                if (detailsPromptContainer) {
                    detailsPromptContainer.classList.remove('hidden');
                }

                // Automatically fetch and display details prompt
                detailsPromptOutputEl.value = 'Generating details prompt...';
                try {
                    const promptResponse = await fetch('/api/generate-details-prompt', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            user_config: userConfig,
                            initial_routine: currentInitialRoutine.routine
                        }),
                    });
                    if (!promptResponse.ok) {
                        const errorData = await promptResponse.json();
                        throw new Error(errorData.error || 'Failed to fetch details prompt');
                    }
                    const promptResult = await promptResponse.json();
                    detailsPromptOutputEl.value = promptResult.prompt || 'Failed to generate details prompt.';
                } catch (error) {
                    console.error('Error auto-generating details prompt:', error);
                    detailsPromptOutputEl.value = `An error occurred: ${error.message}`;
                }
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

    // 3. Generate Details Button
    if (generateDetailsBtn) {
        generateDetailsBtn.addEventListener('click', async () => {
            if (!currentInitialRoutine.routine) {
                alert('Please generate an initial routine first.');
                return;
            }

            showLoading(true);
            formattedOutputEl.textContent = 'Generating detailed routine...';

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

            try {
                const response = await fetch('/api/generate-details', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        user_config: userConfig,
                        initial_routine: currentInitialRoutine.routine,
                        model_used: currentInitialRoutine.model
                    }),
                });

                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
                }

                const result = await response.json();
                // Display raw JSON directly
                formattedOutputEl.textContent = JSON.stringify(result, null, 2);

            } catch (error) {
                console.error('Error generating detailed routine:', error);
                formattedOutputEl.textContent = `An error occurred: ${error.message}`;
            } finally {
                showLoading(false);
            }
        });
    }
});