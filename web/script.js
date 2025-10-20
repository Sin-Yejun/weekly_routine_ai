document.addEventListener('DOMContentLoaded', async () => {
    const form = document.getElementById('routine-form');
    const freqSelect = document.getElementById('freq');
    const splitTypeSelect = document.getElementById('split-type');
    const sortToggle = document.getElementById('sort-toggle');

    let M_ratio_weight = {};
    let F_ratio_weight = {};

    try {
        const response = await fetch('/api/ratios');
        const ratios = await response.json();
        M_ratio_weight = ratios.M_ratio_weight;
        F_ratio_weight = ratios.F_ratio_weight;
    } catch (error) {
        console.error('Error fetching weight ratios:', error);
        alert('Could not load necessary data. Please reload the page.');
    }

    const splitConfigs = {
        '2': [{ id: 'SPLIT', name: '분할 (Upper/Lower)' }, { id: 'FB', name: '무분할 (Full Body)' }],
        '3': [{ id: 'SPLIT', name: '분할 (Push/Pull/Legs)' }, { id: 'FB', name: '무분할 (Full Body)' }],
        '4': [{ id: 'SPLIT', name: '분할 (4-Day Split)' }, { id: 'FB', name: '무분할 (Full Body)' }],
        '5': [{ id: 'SPLIT', name: '분할 (5-Day Split)' }, { id: 'FB', name: '무분할 (Full Body)' }]
    };

    let currentRoutineData = null;
    let currentRawRoutineData = null;
    let currentOutputElement = null;

    const updateSplitOptions = (frequency) => {
        splitTypeSelect.innerHTML = '';
        const options = splitConfigs[frequency] || [];
        options.forEach(option => {
            const optionEl = document.createElement('option');
            optionEl.value = option.id;
            optionEl.textContent = option.name;
            splitTypeSelect.appendChild(optionEl);
        });
    };

    if (freqSelect) {
        freqSelect.addEventListener('change', (event) => updateSplitOptions(event.target.value));
        updateSplitOptions(freqSelect.value);
    }

    const generateVllmBtn = document.getElementById('generate-vllm-btn');
    const generateOpenAiBtn = document.getElementById('generate-openai-btn');
    const loadingIndicator = document.getElementById('loading-indicator');
    const rawOutputEl = document.getElementById('raw-output');
    const formattedOutputEl = document.getElementById('formatted-output');

    const showLoading = (isLoading) => {
        loadingIndicator.classList.toggle('hidden', !isLoading);
        generateVllmBtn.disabled = isLoading;
        generateOpenAiBtn.disabled = isLoading;
    };

    const handleInference = async (apiEndpoint, outputElement) => {
        showLoading(true);
        outputElement.textContent = 'Generating...';
        currentOutputElement = outputElement; // Store which output is being used

        const formData = new FormData(form);
        const userConfig = {};
        formData.forEach((value, key) => {
            if (key === 'tools') {
                if (!userConfig[key]) userConfig[key] = [];
                userConfig[key].push(value);
            } else {
                userConfig[key] = value;
            }
        });

        userConfig.prevent_weekly_duplicates = document.getElementById('prevent-duplicates-toggle').checked;
        userConfig.prevent_category_duplicates = document.getElementById('prevent-category-duplicates-toggle').checked;

        try {
            const response = await fetch(apiEndpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(userConfig),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            document.getElementById('prompt-display').value = result.prompt || 'No prompt was returned.';
            currentRoutineData = result.routine;
            currentRawRoutineData = result.raw_routine;
            renderRoutine(); // Initial render

        } catch (error) {
            console.error(`Error generating routine via ${apiEndpoint}:`, error);
            outputElement.textContent = `An error occurred: ${error.message}`;
            currentRoutineData = null;
            currentRawRoutineData = null;
        } finally {
            showLoading(false);
        }
    };

    const getSortKey = (exercise) => {
        const bnamePriorityMap = {
            'CHEST': 1, 'BACK': 1, 'LEG': 1, 'SHOULDER': 2, 'ARM': 3, 'ABS': 4, 'ETC': 5
        };
        const bName = (exercise.bName || 'ETC').toUpperCase();
        const priority = bnamePriorityMap[bName] || 99;
        const isMain = exercise.main_ex ? 0 : 1; // Main exercises first
        const mgNum = -parseInt(exercise.MG_num || 0);
        const musclePointSum = -parseInt(exercise.musle_point_sum || 0);
        return [priority, isMain, mgNum, musclePointSum];
    };

    const renderRoutine = () => {
        if (!currentRoutineData || !currentOutputElement) return;

        const isSorted = sortToggle.checked;
        let routineToRender = JSON.parse(JSON.stringify(currentRoutineData)); // Deep copy

        if (isSorted) {
            routineToRender.days.forEach(day => {
                day.sort((a, b) => {
                    const keyA = getSortKey(a);
                    const keyB = getSortKey(b);
                    for (let i = 0; i < keyA.length; i++) {
                        if (keyA[i] < keyB[i]) return -1;
                        if (keyA[i] > keyB[i]) return 1;
                    }
                    return 0;
                });
            });
        }

        const backSquat1RM = parseFloat(document.getElementById('back-squat-1rm').value);
        const gender = document.getElementById('gender').value;
        const level = document.getElementById('level').value;

        calculateAndRenderText(routineToRender, backSquat1RM, gender, level, currentOutputElement, currentRawRoutineData);
    };

    const calculateAndRenderText = (routineData, backSquat1RM, gender, level, outputElement, rawRoutineData) => {
        const levelSets = {
            "Beginner": [15, 12, 10, 8],
            "Novice": [15, 12, 10, 9, 8],
            "Intermediate": [15, 12, 10, 10, 8, 8],
            "Advanced": [15, 12, 10, 10, 8, 8],
            "Elite": [15, 12, 10, 10, 8, 8]
        };

        const ratios = (gender === 'M') ? M_ratio_weight : F_ratio_weight;
        let htmlOutput = '';

        if (!routineData.days || routineData.days.length === 0) {
            outputElement.innerHTML = 'No routine generated.';
            return;
        }

        const getCharWidth = (char) => (char.match(/[\uac00-\ud7a3]/) ? 2 : 1);
        const getStringWidth = (str) => [...str].reduce((acc, char) => acc + getCharWidth(char), 0);

        routineData.days.forEach((day, dayIndex) => {
            htmlOutput += `<span class="day-header">## Day ${dayIndex + 1} (운동 수: ${day.length})</span>\n`;
            
            const dayWithDisplayNames = day.map(ex => ({
                ...ex,
                displayBName: ex.main_ex ? `${ex.bName} (main)` : ex.bName
            }));

            const maxBNameWidth = Math.max(...dayWithDisplayNames.map(ex => getStringWidth(ex.displayBName)));

            dayWithDisplayNames.forEach(exercise => {
                const { eName, displayBName, kName, eInfoType, tool_en } = exercise;
                const bNamePadding = ' '.repeat(maxBNameWidth - getStringWidth(displayBName) + 2);

                const exerciseRatio = ratios[eName];
                let oneRmDisplay = '';
                let estimated1RM = 0;

                if (exerciseRatio) {
                    estimated1RM = backSquat1RM * exerciseRatio;
                    oneRmDisplay = ` (1RM - ${Math.round(estimated1RM)}) ${exerciseRatio.toFixed(4)}`;
                }

                htmlOutput += `<span class="exercise-bname">${displayBName}</span>${bNamePadding}<span class="exercise-kname">${kName}</span>${oneRmDisplay}\n`;

                const repsArray = levelSets[level] || levelSets['Intermediate'];
                
                                if (eInfoType === 2) {
                
                                    if (exerciseRatio) {
                
                                        const customReps = Math.round(estimated1RM);
                
                                        const numSets = repsArray.length;
                
                                        const setStrings = Array(numSets).fill(`${customReps}회`);
                
                                        htmlOutput += `<span class="exercise-sets">${setStrings.join(' / ')}</span>\n\n`;
                
                                    } else {
                
                                        htmlOutput += '<span class="exercise-sets">Calculation not available.</span>\n\n';
                
                                    }
                
                                } else {
                    if (exerciseRatio) {
                        const setStrings = repsArray.map((reps, index) => {
                            let weight;
                            if (index === 0) { // Set 1
                                weight = estimated1RM * 0.4;
                            } else if (index === 1) { // Set 2
                                weight = estimated1RM * 0.6;
                            } else { // Working sets
                                weight = estimated1RM / (1 + reps / 30);
                            }

                            let roundedWeight;
                            const tool = (tool_en || 'etc').toLowerCase();
                            if (tool === 'dumbbell') {
                                roundedWeight = Math.round(weight / 2) * 2;
                            } else if (tool === 'barbell' || tool === 'machine') {
                                roundedWeight = Math.round(weight / 5) * 5;
                            } else {
                                roundedWeight = Math.round(weight / 2.5) * 2.5;
                            }
                            return `${roundedWeight}kg ${reps}회`;
                        });
                        htmlOutput += `<span class="exercise-sets">${setStrings.join(' / ')}</span>\n\n`;
                    } else {
                        htmlOutput += '<span class="exercise-sets">Weight calculation not available.</span>\n\n';
                    }
                }
            });
        });

        if (rawRoutineData) {
            htmlOutput += `\n\n<span class="day-header">--- Raw Model Output ---</span>\n`;
            htmlOutput += JSON.stringify(rawRoutineData, null, 2);
        }

        outputElement.innerHTML = htmlOutput;
    };

    sortToggle.addEventListener('change', renderRoutine);

    if (generateVllmBtn) {
        generateVllmBtn.addEventListener('click', () => handleInference('/api/infer', rawOutputEl));
    }

    if (generateOpenAiBtn) {
        generateOpenAiBtn.addEventListener('click', () => handleInference('/api/generate-openai', formattedOutputEl));
    }
});