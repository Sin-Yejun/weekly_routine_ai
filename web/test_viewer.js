document.addEventListener('DOMContentLoaded', () => {
    // --- DOM Elements ---
    const genderFilter = document.getElementById('gender-filter');
    const levelFilter = document.getElementById('level-filter');
    const freqFilter = document.getElementById('freq-filter');
    const splitFilter = document.getElementById('split-filter');
    const durationFilter = document.getElementById('duration-filter');
    const intensityFilter = document.getElementById('intensity-filter');
    const routineDisplay = document.getElementById('routine-display');
    const calculateWeightsBtn = document.getElementById('calculate-weights-btn');

    // --- Experience Inputs ---
    const experienceRadios = document.querySelectorAll('input[name="experience"]');
    const detailsBackSquat = document.getElementById('details-back-squat');
    const detailsBenchPress = document.getElementById('details-bench-press');

    let allTestCases = [];
    const kNameToExerciseDetailsMap = new Map();
    let M_ratio_weight = {};
    let F_ratio_weight = {};
    let isWeightsCalculated = false; // Flag to track if weights are currently displayed

    // --- Functions ---

    const splitLabels = {
        '2': '분할 (상체 / 하체)',
        '3': '분할 (밀기 / 당기기 / 하체)',
        '4': '분할 (가슴 / 등 / 하체 / 어깨)',
        '5': '분할 (가슴 / 등 / 하체 / 어깨 / 팔+복근)'
    };

    const updateSplitOptions = () => {
        const selectedFreq = freqFilter.value;
        const splitLabel = splitLabels[selectedFreq];
        const previouslySelectedSplit = splitFilter.value;

        splitFilter.innerHTML = ''; // Clear current options

        const splitOption = document.createElement('option');
        splitOption.value = 'SPLIT';
        splitOption.textContent = splitLabel;
        splitFilter.appendChild(splitOption);

        const fbOption = document.createElement('option');
        fbOption.value = 'FB';
        fbOption.textContent = '무분할 (Full Body)';
        splitFilter.appendChild(fbOption);

        if (previouslySelectedSplit === 'SPLIT' || previouslySelectedSplit === 'FB') {
            splitFilter.value = previouslySelectedSplit;
        }
    };

    const loadData = async () => {
        try {
            const [testCasesResponse, catalogResponse, ratiosResponse] = await Promise.all([
                fetch('test_cases.json'),
                fetch('/data/02_processed/processed_query_result_200.json'),
                fetch('/api/ratios')
            ]);

            if (!testCasesResponse.ok) throw new Error(`Failed to load test_cases.json: ${testCasesResponse.statusText}`);
            if (!catalogResponse.ok) throw new Error(`Failed to load exercise catalog: ${catalogResponse.statusText}`);
            if (!ratiosResponse.ok) throw new Error(`Failed to load ratios: ${ratiosResponse.statusText}`);

            allTestCases = await testCasesResponse.json();
            const exerciseCatalog = await catalogResponse.json();
            const ratios = await ratiosResponse.json();

            M_ratio_weight = ratios.M_ratio_weight;
            F_ratio_weight = ratios.F_ratio_weight;

            exerciseCatalog.forEach(exercise => {
                if (exercise.kName) {
                    kNameToExerciseDetailsMap.set(exercise.kName, exercise);
                }
            });

            console.log(`${allTestCases.length} test cases loaded.`);
            console.log(`${kNameToExerciseDetailsMap.size} exercises mapped.`);
            console.log(`Weight ratios loaded.`);
        } catch (error) {
            console.error("Could not load data:", error);
            routineDisplay.innerHTML = `<p style="color: #ff5555;">Error: Could not load necessary data files. Please check console for errors.</p>`;
        }
    };

    const getRepsArray = (level, mgNum) => {
        if (mgNum <= 2) {
            switch (level) {
                case 'Beginner': return [20, 20, 15, 15];
                case 'Novice': return [20, 20, 15, 15, 15];
                default: return [20, 20, 15, 15, 12, 12];
            }
        } else {
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

    const updateRoutineDisplay = () => {
        isWeightsCalculated = false; // Reset the flag whenever the routine is changed
        const selectedGender = genderFilter.value;
        const selectedLevel = levelFilter.value;
        const selectedFreq = parseInt(freqFilter.value, 10);
        const selectedSplit = splitFilter.value;
        const selectedDuration = parseInt(durationFilter.value, 10);

        const foundCase = allTestCases.find(c => 
            c.gender === selectedGender &&
            c.level === selectedLevel &&
            c.freq === selectedFreq &&
            c.split_id === selectedSplit
        );

        if (foundCase && foundCase.routine) {
            if (foundCase.routine.error) {
                 routineDisplay.innerHTML = `<p style="color: #ffcc00;">Routine generation failed for this case: ${foundCase.routine.error}</p>`;
            } else {
                let routineToDisplay = JSON.parse(JSON.stringify(foundCase.routine));
                Object.values(routineToDisplay).forEach(exercises => {
                    if (selectedDuration === 45) {
                        if (exercises.length > 1) exercises.pop();
                    } else if (selectedDuration === 30) {
                        if (exercises.length > 1) exercises.pop();
                        if (exercises.length > 1) exercises.pop();
                    }
                });

                let html = '';
                for (const [day, exercises] of Object.entries(routineToDisplay)) {
                    html += `<div class="day-header">${day} (운동 수: ${exercises.length})</div>`;
                    html += `<ul>`;
                    exercises.forEach(kName => {
                        const bName = kNameToExerciseDetailsMap.get(kName)?.bName || 'N/A';
                        html += `<li data-kname="${kName}">${bName} - ${kName}</li>`;
                    });
                    html += `</ul>`;
                }
                routineDisplay.innerHTML = html;
            }
        } else {
            routineDisplay.innerHTML = '<p>No matching routine found for the selected criteria.</p>';
        }
    };

    const renderCalculatedWeights = () => {
        const selectedExperience = document.querySelector('input[name="experience"]:checked').value;
        const level = levelFilter.value;
        const gender = genderFilter.value;
        const intensity = intensityFilter.value;

        let base1RM = 0;
        let baseExerciseName = 'Back Squat'; // Default for 'unknown' case

        if (selectedExperience === 'unknown') {
            let levelTo1RM;
            if (gender === 'M') {
                levelTo1RM = { "Beginner": 20, "Novice": 40, "Intermediate": 60, "Advanced": 80, "Elite": 100 };
                base1RM = levelTo1RM[level] || 60; // Default for Male
            } else { // 'F'
                levelTo1RM = { "Beginner": 20, "Novice": 35, "Intermediate": 50, "Advanced": 65, "Elite": 80 };
                base1RM = levelTo1RM[level] || 50; // Default for Female
            }
        } else {
            let weightInput, repsInput;
            if (selectedExperience === 'back-squat') {
                weightInput = document.getElementById('exp-weight-bs');
                repsInput = document.getElementById('exp-reps-bs');
                baseExerciseName = 'Back Squat';
            } else { // bench-press
                weightInput = document.getElementById('exp-weight-bp');
                repsInput = document.getElementById('exp-reps-bp');
                baseExerciseName = 'Barbell Bench Press';
            }

            const weight = parseFloat(weightInput.value);
            const reps = parseInt(repsInput.value, 10);

            if (isNaN(weight) || isNaN(reps) || reps <= 0) {
                alert('운동 경험(백스쿼트 또는 벤치프레스)을 선택하고 무게, 반복횟수를 올바르게 입력해주세요.');
                return;
            }

            if (reps === 1) {
                base1RM = weight; // Use weight directly as 1RM
            } else {
                base1RM = weight * (1 + reps / 30); // Epley formula
            }
        }

        const ratios = (gender === 'M') ? M_ratio_weight : F_ratio_weight;
        const baseRatio = ratios[baseExerciseName] || 1;
        const squat1RM = (base1RM / baseRatio); // This is the normalized 1RM (equivalent to squat 1RM)

        // Clear previous sets and line breaks
        document.querySelectorAll('#routine-display li').forEach(item => {
            let child = item.lastElementChild;
            while (child && (child.tagName === 'SPAN' && child.classList.contains('exercise-sets') || child.tagName === 'BR')) {
                item.removeChild(child);
                child = item.lastElementChild;
            }
        });

        // Find all exercise list items and calculate/append sets
        document.querySelectorAll('#routine-display li').forEach(item => {
            const kName = item.dataset.kname;
            if (!kName) return;

            const exerciseDetails = kNameToExerciseDetailsMap.get(kName);
            if (!exerciseDetails) return;

            const exerciseRatio = ratios[exerciseDetails.eName];
            let estimated1RM = 0;

            if (exerciseRatio) {
                estimated1RM = squat1RM * exerciseRatio;
                if (intensity === 'Low') estimated1RM *= 0.9;
                if (intensity === 'High') estimated1RM *= 1.1;
            }

            const repsArray = getRepsArray(level, exerciseDetails.MG_num || 0);
            const setStrings = calculateSetStrings(exerciseDetails, estimated1RM, repsArray, level);
            
            const setsSpan = document.createElement('span');
            setsSpan.className = 'exercise-sets';
            setsSpan.textContent = setStrings.join(' / ');
            
            item.appendChild(document.createElement('br'));
            item.appendChild(setsSpan);
        });

        isWeightsCalculated = true; // Set the flag after successful calculation
    };

    // --- Initial Setup & Event Listeners ---

    // Filters that reset the entire routine
    [genderFilter, levelFilter, splitFilter].forEach(filter => {
        filter.addEventListener('change', updateRoutineDisplay);
    });

    freqFilter.addEventListener('change', () => {
        updateSplitOptions();
        updateRoutineDisplay();
    });

    // Duration filter: Shortens routine, but keeps weights if they were calculated
    durationFilter.addEventListener('change', () => {
        const wereWeightsCalculated = isWeightsCalculated;
        updateRoutineDisplay(); 
        if (wereWeightsCalculated) {
            renderCalculatedWeights();
        }
    });

    // Intensity filter: Only recalculates weights if they are already displayed
    intensityFilter.addEventListener('change', () => {
        if (isWeightsCalculated) {
            renderCalculatedWeights();
        }
    });

    // Load data and set initial view
    loadData().then(() => {
        updateSplitOptions();
        updateRoutineDisplay();
    });

    // --- Experience Radio Logic ---
    const updateExperienceDetails = () => {
        const selectedValue = document.querySelector('input[name="experience"]:checked').value;
        if (selectedValue === 'back-squat') {
            detailsBackSquat.classList.remove('hidden');
            detailsBenchPress.classList.add('hidden');
        } else if (selectedValue === 'bench-press') {
            detailsBackSquat.classList.add('hidden');
            detailsBenchPress.classList.remove('hidden');
        } else {
            detailsBackSquat.classList.add('hidden');
            detailsBenchPress.classList.add('hidden');
        }
    };

    experienceRadios.forEach(radio => {
        radio.addEventListener('change', updateExperienceDetails);
    });
    updateExperienceDetails(); // Initial call

    // --- Weight Calculation Button ---
    calculateWeightsBtn.addEventListener('click', renderCalculatedWeights);
});