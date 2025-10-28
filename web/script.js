document.addEventListener('DOMContentLoaded', async () => {
    // --- DOM 요소 가져오기 ---
    const form = document.getElementById('routine-form');
    const freqSelect = document.getElementById('freq');
    const splitTypeSelect = document.getElementById('split-type');
    const sortToggle = document.getElementById('sort-toggle');

    // --- 전역 변수 및 데이터 로드 ---
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

    // --- 함수 정의 ---
    const updateSplitOptions = (frequency) => {
        // 주당 운동 빈도에 따라 분할/무분할 옵션 업데이트
        splitTypeSelect.innerHTML = '';
        const options = splitConfigs[frequency] || [];
        options.forEach(option => {
            const optionEl = document.createElement('option');
            optionEl.value = option.id;
            optionEl.textContent = option.name;
            splitTypeSelect.appendChild(optionEl);
        });
    };

    // --- 이벤트 리스너 설정 ---
    if (freqSelect) {
        freqSelect.addEventListener('change', (event) => updateSplitOptions(event.target.value));
        updateSplitOptions(freqSelect.value); // 초기 옵션 설정
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

    const getUserConfig = () => {
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
        userConfig.weight = document.getElementById('weight').value;
        // Add default max_tokens and temperature as they are not exposed in the UI
        userConfig.max_tokens = 4096;
        userConfig.temperature = 1.0;
        return userConfig;
    };

    const handleInference = async (apiEndpoint, outputElement) => {
        // AI 모델 추론 처리
        showLoading(true);
        outputElement.textContent = 'Generating...';
        currentOutputElement = outputElement; // 현재 사용중인 출력 요소 저장

        const userConfig = getUserConfig();

        try {
            const response = await fetch(apiEndpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(userConfig),
            });

            if (!response.ok) {
                const errorData = await response.json();
                // FastAPI returns errors in 'detail' field
                throw new Error(errorData.detail || errorData.error || `HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            document.getElementById('prompt-display').value = result.prompt || 'No prompt was returned.';
            currentRoutineData = result.routine;
            currentRawRoutineData = result.raw_routine;
            renderRoutine(); // 초기 렌더링

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
        // 운동 정렬을 위한 키 생성
        const bnamePriorityMap = {
            'LEG': 1, 'CHEST': 2, 'BACK': 3, 'SHOULDER': 4, 'ARM': 5, 'ABS': 6, 'ETC': 7
        };
        const bName = (exercise.bName || 'ETC').toUpperCase();
                    const priority = bnamePriorityMap[bName] || 99;
                    const mgNum = -parseInt(exercise.MG_num || 0);
                    const musclePointSum = -parseInt(exercise.musle_point_sum || 0);
                    return [priority, mgNum, musclePointSum];    };

    const renderRoutine = () => {
        // 루틴 렌더링
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
        const intensity = document.getElementById('intensity').value;

        calculateAndRenderText(routineToRender, backSquat1RM, gender, level, intensity, currentOutputElement, currentRawRoutineData);
    };

    const getRepsArray = (level, mgNum) => {
        if (mgNum <= 2) {
            // New logic for isolation exercises
            switch (level) {
                case 'Beginner':
                    return [20, 20, 15, 15];
                case 'Novice':
                    return [20, 20, 15, 15, 15];
                default: // Intermediate, Advanced, Elite
                    return [20, 20, 15, 15, 12, 12];
            }
        } else {
            // Existing logic for compound exercises
            const levelSets = {
                "Beginner": [15, 12, 10, 8],
                "Novice": [15, 12, 10, 9, 8],
                "Intermediate": [15, 12, 10, 10, 8, 8],
                "Advanced": [15, 12, 10, 10, 8, 8],
                "Elite": [15, 12, 10, 10, 8, 8]
            };
            return levelSets[level] || levelSets['Intermediate'];
        }
    };

    const calculateSetStrings = (exercise, estimated1RM, repsArray, level) => {
        const { eName, eInfoType, tool_en } = exercise;
        const exerciseRatio = M_ratio_weight[eName] || F_ratio_weight[eName];
        const isAssistedMachine = eName === "Assisted Pull Up Machine" || eName === "Assisted Dip Machine";

        if (isAssistedMachine && exerciseRatio) {
            const setWeights = [];
            if (level === 'Beginner' || level === 'Novice') {
                let weight = estimated1RM;
                repsArray.forEach((reps, index) => {
                    if (index >= 2) {
                        weight *= 0.8;
                    }
                    setWeights.push(weight);
                });
            } else { // Intermediate, Advanced, Elite
                repsArray.forEach(reps => {
                    let weight;
                    if (reps >= 12) {
                        weight = estimated1RM;
                    } else if (reps >= 10) {
                        weight = estimated1RM * 0.8;
                    } else {
                        weight = estimated1RM * 0.6;
                    }
                    setWeights.push(weight);
                });
            }

            return setWeights.map((weight, index) => {
                const reps = repsArray[index];
                let roundedWeight = Math.round(weight / 5) * 5;
                roundedWeight = Math.max(roundedWeight, 5);
                return `${roundedWeight}kg ${reps}회`;
            });
        } else if (eInfoType === 2) {
            if (exerciseRatio) {
                const customReps = Math.round(estimated1RM);
                const numSets = repsArray.length;
                return Array(numSets).fill(`${customReps}회`);
            } else {
                return [
                    'Calculation not available.'
                ];
            }
        } else {
            if (exerciseRatio) {
                return repsArray.map((reps, index) => {
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
                    if (tool === 'dumbbell' || tool === 'kettlebell') {
                        roundedWeight = Math.round(weight / 2) * 2;
                    } else if (tool === 'barbell' || tool === 'machine' || tool === 'ezbar') {
                        roundedWeight = Math.round(weight / 5) * 5;
                    } else {
                        roundedWeight = Math.round(weight / 2.5) * 2.5;
                    }

                    if (tool === 'barbell') {
                        roundedWeight = Math.max(roundedWeight, 20);
                    } else if (tool === 'dumbbell') {
                        roundedWeight = Math.max(roundedWeight, 2);
                    } else if (tool === 'machine') {
                        roundedWeight = Math.max(roundedWeight, 5);
                    } else if (tool === 'ezbar') {
                        roundedWeight = Math.max(roundedWeight, 10);
                    } else if (tool === 'kettlebell') {
                        roundedWeight = Math.max(roundedWeight, 4);
                    } else if (tool === 'etc') {
                        roundedWeight = Math.max(roundedWeight, 2.5);
                    }

                    return `${roundedWeight}kg ${reps}회`;
                });
            } else {
                return [
                    'Calculation not available.'
                ];
            }
        }
    };

    const calculateAndRenderText = (routineData, backSquat1RM, gender, level, intensity, outputElement, rawRoutineData) => {
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
                const { eName, displayBName, kName, eInfoType, tool_en, MG_num } = exercise;
                const bNamePadding = ' '.repeat(maxBNameWidth - getStringWidth(displayBName) + 2);

                const exerciseRatio = ratios[eName];
                let oneRmDisplay = '';
                let estimated1RM = 0;

                if (exerciseRatio) {
                    estimated1RM = backSquat1RM * exerciseRatio;

                    // Apply intensity adjustment
                    if (intensity === 'Low') {
                        estimated1RM *= 0.9;
                    } else if (intensity === 'High') {
                        estimated1RM *= 1.1;
                    }

                    oneRmDisplay = ` (1RM - ${Math.round(estimated1RM)}) ${exerciseRatio.toFixed(4)}`;
                }

                htmlOutput += `<span class="exercise-bname">${displayBName}</span>${bNamePadding}<span class="exercise-kname">${kName}</span>${oneRmDisplay}\n`;

                const repsArray = getRepsArray(level, parseInt(MG_num) || 0);
                const setStrings = calculateSetStrings(exercise, estimated1RM, repsArray, level);
                htmlOutput += `<span class="exercise-sets">${setStrings.join(' / ')}</span>\n\n`;
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

    const viewTestCasesBtn = document.getElementById('view-test-cases-btn');
    if (viewTestCasesBtn) {
        viewTestCasesBtn.addEventListener('click', () => {
            window.location.href = 'test_viewer_static.html';
        });
    }
});