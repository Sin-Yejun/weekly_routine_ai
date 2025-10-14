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
    const preventCategoryDuplicatesToggle = document.getElementById('prevent-category-duplicates-toggle');
    const preventDuplicatesToggle = document.getElementById('prevent-duplicates-toggle'); // Existing toggle

    const promptOutputEl = document.getElementById('prompt-output');
    const rawOutputEl = document.getElementById('raw-output');
    const formattedOutputEl = document.getElementById('formatted-output');
    const detailsPromptContainer = document.getElementById('details-prompt-container');
    const detailsPromptOutputEl = document.getElementById('details-prompt-output');

    // Store for both outputs
    let vllmRoutines = { 
        unprocessed: { unsorted: '', sorted: '', initial_routine: null }, 
        processed: { unsorted: '', sorted: '', initial_routine: null },
        model_used: '' 
    };
    let openAiRoutines = { 
        unprocessed: { unsorted: '', sorted: '', initial_routine: null }, 
        processed: { unsorted: '', sorted: '', initial_routine: null },
        model_used: '' 
    };
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
        const useProcessed = preventCategoryDuplicatesToggle.checked;

        let content;
        let initialRoutine;

        if (useProcessed) {
            content = isSorted ? routines.processed.sorted : routines.processed.unsorted;
            initialRoutine = routines.processed.initial_routine;
        } else {
            content = isSorted ? routines.unprocessed.sorted : routines.unprocessed.unsorted;
            initialRoutine = routines.unprocessed.initial_routine;
        }
        
        element.textContent = content || 'No content available.';

        // Update currentInitialRoutine based on the displayed content
        if (element === rawOutputEl) { // Only update for vLLM output, as it's the primary source for details
            currentInitialRoutine = { routine: initialRoutine, model: routines.model_used };
            if (generateDetailsBtn) {
                if (currentInitialRoutine.routine) {
                    generateDetailsBtn.classList.remove('hidden');
                    if (detailsPromptContainer) {
                        detailsPromptContainer.classList.remove('hidden');
                    }
                } else {
                    generateDetailsBtn.classList.add('hidden');
                    if (detailsPromptContainer) {
                        detailsPromptContainer.classList.add('hidden');
                    }
                }
            }
        }
    };

    sortToggle.addEventListener('change', () => {
        updateOutput(rawOutputEl, vllmRoutines);
        updateOutput(formattedOutputEl, openAiRoutines);
    });

    preventCategoryDuplicatesToggle.addEventListener('change', () => {
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
            
            vllmRoutines = { 
                unprocessed: { unsorted: '', sorted: '', initial_routine: null }, 
                processed: { unsorted: '', sorted: '', initial_routine: null },
                model_used: '' 
            };
            openAiRoutines = { 
                unprocessed: { unsorted: '', sorted: '', initial_routine: null }, 
                processed: { unsorted: '', sorted: '', initial_routine: null },
                model_used: '' 
            };
            currentInitialRoutine = { routine: null, model: '' };

            if (generateDetailsBtn) {
                generateDetailsBtn.classList.add('hidden');
            }
            if (detailsPromptContainer) {
                detailsPromptContainer.classList.add('hidden');
                detailsPromptOutputEl.value = 'The prompt for the details generation will appear here.';
            }
            

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

            // The duplicate prevention logic is now handled on the backend for display toggling.
            // No need to send prevent_weekly_duplicates for prompt generation.

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

        // Send the state of the new toggle to the backend
        userConfig.prevent_weekly_duplicates = preventDuplicatesToggle.checked;
        userConfig.prevent_category_duplicates = preventCategoryDuplicatesToggle.checked;
        
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
            console.log('Backend response result:', result);
            
            // Store both unprocessed and processed routines
            if (result.formatted_summary && typeof result.formatted_summary === 'object') {
                // Unprocessed
                routineStorage.unprocessed.unsorted = "--- Formatted Output (Unprocessed) ---\n" + result.formatted_summary.unprocessed.unsorted;
                routineStorage.unprocessed.sorted = "--- Formatted Output (Unprocessed, Sorted) ---\n" + result.formatted_summary.unprocessed.sorted;
                routineStorage.unprocessed.initial_routine = result.formatted_summary.unprocessed.initial_routine;

                // Processed
                routineStorage.processed.unsorted = "--- Formatted Output (Processed) ---\n" + result.formatted_summary.processed.unsorted;
                routineStorage.processed.sorted = "--- Formatted Output (Processed, Sorted) ---\n" + result.formatted_summary.processed.sorted;
                routineStorage.processed.initial_routine = result.formatted_summary.processed.initial_routine;
                
                if (result.response) {
                    const rawSuffix = "\n\n--- Raw Model Output ---\n" + result.response;
                    routineStorage.unprocessed.unsorted += rawSuffix;
                    routineStorage.unprocessed.sorted += rawSuffix;
                    routineStorage.processed.unsorted += rawSuffix;
                    routineStorage.processed.sorted += rawSuffix;
                }
            } else {
                const fallbackContent = result.response ? "--- Raw Model Output ---\n" + result.response : 'No valid response returned.';
                routineStorage.unprocessed.unsorted = fallbackContent;
                routineStorage.unprocessed.sorted = fallbackContent;
                routineStorage.processed.unsorted = fallbackContent;
                routineStorage.processed.sorted = fallbackContent;
            }

            routineStorage.model_used = apiEndpoint.includes('infer') ? 'vllm' : 'openai';
            
            // Update currentInitialRoutine based on the processed version for detail generation
            currentInitialRoutine = { routine: routineStorage.processed.initial_routine, model: routineStorage.model_used }; 

            if (currentInitialRoutine.routine) {
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