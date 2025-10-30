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
    const hideWeightsBtn = document.getElementById('hide-weights-btn');

    // --- Experience Inputs ---
    const experienceRadios = document.querySelectorAll('input[name="experience"]');
    const detailsBackSquat = document.getElementById('details-back-squat');
    const detailsBenchPress = document.getElementById('details-bench-press');

    const otherExerciseSearch = document.getElementById('other-exercise-search');
    const expWeightOther      = document.getElementById('exp-weight-other');
    const expRepsOther        = document.getElementById('exp-reps-other');
    const expOtherExerciseRadio = document.getElementById('exp-other-exercise');
    const exerciseOptionsDatalist = document.getElementById('exercise-options');

    let allTestCases = [];
    const kNameToExerciseDetailsMap = new Map();
    let M_ratio_weight = {};
    let F_ratio_weight = {};
    let isWeightsCalculated = false;

    // --- Functions ---

    const splitLabels = {
        '2': '분할 (상체 / 하체)',
        '3': '분할 (밀기 / 당기기 / 하체)',
        '4': '분할 (하체 / 가슴 / 등 / 어깨)',
        '5': '분할 (하체 / 가슴 / 등 / 어깨 / 팔+복근)'
    };

     // Populate datalist for other exercises
    kNameToExerciseDetailsMap.forEach((value, key) => {
        const option = document.createElement('option');
        option.value = key; // Use kName for display and selection
        exerciseOptionsDatalist.appendChild(option);
    });

    const updateSplitOptions = () => {
        const selectedFreq = freqFilter.value;
        const splitLabel = splitLabels[selectedFreq];
        const previouslySelectedSplit = splitFilter.value;

        splitFilter.innerHTML = '';

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

    // New helper function to apply range and rounding
    const formatWeightRange = (baseWeight, reps, intensity, tool_en) => {
        const tool = (tool_en || 'etc').toLowerCase();
        
        // Calculate the base weight for the set (Normal intensity)
        let normalSetWeight = baseWeight;

        // Determine the intensity multiplier
        let intensityMultiplier = 1.0;
        if (intensity === 'Low') {
            intensityMultiplier = 0.9;
        } else if (intensity === 'High') {
            intensityMultiplier = 1.1;
        }

        // Calculate the effective weight based on intensity
        let effectiveWeight = normalSetWeight * intensityMultiplier;

        let roundedEffectiveWeight;
        // Apply rounding and Math.max to this effectiveWeight
        if (tool === 'dumbbell' || tool === 'kettlebell') {
            roundedEffectiveWeight = Math.round(effectiveWeight / 2) * 2;
        } else if (tool === 'barbell' || tool === 'machine' || tool === 'ezbar') {
            roundedEffectiveWeight = Math.round(effectiveWeight / 5) * 5;
        } else {
            roundedEffectiveWeight = Math.round(effectiveWeight / 2.5) * 2.5;
        }
        if (tool === 'barbell') roundedEffectiveWeight = Math.max(roundedEffectiveWeight, 20);
        else if (tool === 'dumbbell') roundedEffectiveWeight = Math.max(roundedEffectiveWeight, 2);
        else if (tool === 'machine') roundedEffectiveWeight = Math.max(roundedEffectiveWeight, 5);
        else if (tool === 'ezbar') roundedEffectiveWeight = Math.max(roundedEffectiveWeight, 10);
        else if (tool === 'kettlebell') roundedEffectiveWeight = Math.max(roundedEffectiveWeight, 4);
        else if (tool === 'etc') roundedEffectiveWeight = Math.max(roundedEffectiveWeight, 0);

        // Return the single rounded value
        return `${roundedEffectiveWeight}kg ${reps}회`;
    };

    const calculateSetStrings = (exercise, estimated1RM, repsArray, level, intensity) => {
        const { eName, eInfoType, tool_en } = exercise;
        const exerciseRatio = M_ratio_weight[eName] || F_ratio_weight[eName];
        const isAssistedMachine = eName === "Assisted Pull Up Machine" || eName === "Assisted Dip Machine";

        // --- Assisted Machine Logic ---
        if (isAssistedMachine && exerciseRatio) {
            if (level === 'Beginner' || level === 'Novice') {
                return repsArray.map((reps, index) => {
                    let baseWeight = estimated1RM;
                    if (index >= 2) {
                        baseWeight *= 0.8;
                    }
                    return formatWeightRange(baseWeight, reps, intensity, tool_en);
                });
            } else { // Intermediate, Advanced, Elite
                return repsArray.map(reps => {
                    let baseWeight;
                    if (reps >= 12) {
                        baseWeight = estimated1RM;
                    }
                    else if (reps >= 10) {
                        baseWeight = estimated1RM * 0.8;
                    }
                    else {
                        baseWeight = estimated1RM * 0.6;
                    }
                    return formatWeightRange(baseWeight, reps, intensity, tool_en);
                });
            }
        }
        // --- eInfoType === 2 Logic ---
        else if (eInfoType === 2) {
            if (exerciseRatio) {
                const customReps = Math.round(estimated1RM);
                const numSets = repsArray.length;
                // This case is for bodyweight/custom reps, no weight range needed here.
                return Array(numSets).fill(`${customReps}회`);
            } else {
                return ['Calculation not available.'];
            }
        }
        // --- Other Exercises Logic (Main Target) ---
        else {
            if (exerciseRatio) {
                return repsArray.map((reps, index) => {
                    let baseWeight;
                    if (index === 0) { // Set 1
                        baseWeight = estimated1RM * 0.4;
                    }
                    else if (index === 1) { // Set 2
                        baseWeight = estimated1RM * 0.6;
                    }
                    else { // Working sets
                        baseWeight = estimated1RM / (1 + reps / 30);
                    }
                    return formatWeightRange(baseWeight, reps, intensity, tool_en);
                });
            } else {
                return ['Calculation not available.'];
            }
        }
    };

    const updateRoutineDisplay = (selectedWeek = 'week1') => {
        const wereWeightsCalculated = isWeightsCalculated;

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

        // Update active tab
        document.querySelectorAll('.week-tab').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.week === selectedWeek);
        });

        if (foundCase && foundCase[selectedWeek]) {
            const routineForWeek = foundCase[selectedWeek];
            if (routineForWeek.error) {
                routineDisplay.innerHTML = `<p style="color: #ffcc00;">Routine generation failed for this week: ${routineForWeek.error}</p>`;
            } else {
                let routineToDisplay = JSON.parse(JSON.stringify(routineForWeek));
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

                // If weights were calculated before, re-render them for the new routine view
                if (wereWeightsCalculated) {
                    renderCalculatedWeights();
                } else if (isWeightsCalculated === false && wereWeightsCalculated === true) { // If weights were hidden, keep them hidden
                    document.querySelectorAll('#routine-display .exercise-sets').forEach(span => {
                        span.style.display = 'none';
                    });
                }
            }
        } else {
            routineDisplay.innerHTML = '<p>No matching routine found for the selected criteria for this week.</p>';
        }
    };

    const renderCalculatedWeights = () => {
        const selectedExperience = document.querySelector('input[name="experience"]:checked').value;
        const level = levelFilter.value;
        const gender = genderFilter.value;
        const intensity = intensityFilter.value;

        let base1RM = 0;
        let baseExerciseName = '';

        if (selectedExperience === 'unknown') {
            let levelTo1RM;
            if (gender === 'M') {
                levelTo1RM = { "Beginner": 20, "Novice": 40, "Intermediate": 60, "Advanced": 80, "Elite": 100 };
                base1RM = levelTo1RM[level] || 60;
            } else {
                levelTo1RM = { "Beginner": 20, "Novice": 35, "Intermediate": 50, "Advanced": 65, "Elite": 80 };
                base1RM = levelTo1RM[level] || 50;
            }
            baseExerciseName = 'Back Squat';
        } else {
            let weightInput, repsInput, selectedExerciseKName;
            if (selectedExperience === 'back-squat') {
                weightInput = document.getElementById('exp-weight-bs');
                repsInput = document.getElementById('exp-reps-bs');
                baseExerciseName = 'Back Squat';
            } else if (selectedExperience === 'bench-press') {
                weightInput = document.getElementById('exp-weight-bp');
                repsInput = document.getElementById('exp-reps-bp');
                baseExerciseName = 'Barbell Bench Press';
            } else if (selectedExperience === 'other-exercise') { // ADDED
                selectedExerciseKName = otherExerciseSearch.value; // ADDED
                weightInput = expWeightOther; // ADDED
                repsInput = expRepsOther; // ADDED

                const exerciseDetails = kNameToExerciseDetailsMap.get(selectedExerciseKName); // ADDED
                if (!exerciseDetails) { // ADDED
                    alert('선택한 운동을 찾을 수 없습니다. 정확한 운동 이름을 입력하거나 목록에서 선택해주세요.'); // ADDED
                    return; // ADDED
                }
                baseExerciseName = exerciseDetails.eName; // Use eName for ratio lookup // ADDED
            }

            const weight = parseFloat(weightInput.value);
            const reps = parseInt(repsInput.value, 10);

            if (isNaN(weight) || isNaN(reps) || reps <= 0) {
                alert('운동 경험(백스쿼트, 벤치프레스 또는 기타 운동)을 선택하고 무게, 반복횟수를 올바르게 입력해주세요.');
                return;
            }

            if (reps === 1) {
                base1RM = weight;
            } else {
                base1RM = weight * (1 + reps / 30);
            }
        }

        const ratios = (gender === 'M') ? M_ratio_weight : F_ratio_weight;
        const baseRatio = ratios[baseExerciseName] || 1;
        const squat1RM = (base1RM / baseRatio);

        document.querySelectorAll('#routine-display li').forEach(item => {
            let child = item.lastElementChild;
            while (child && (child.tagName === 'SPAN' && child.classList.contains('exercise-sets') || child.tagName === 'BR')) {
                item.removeChild(child);
                child = item.lastElementChild;
            }
        });

        document.querySelectorAll('#routine-display li').forEach(item => {
            const kName = item.dataset.kname;
            if (!kName) return;

            const exerciseDetails = kNameToExerciseDetailsMap.get(kName);
            if (!exerciseDetails) return;

            const exerciseRatio = ratios[exerciseDetails.eName];
            let estimated1RM = 0;

            if (exerciseRatio) {
                estimated1RM = squat1RM * exerciseRatio;
                // Intensity adjustment will now be handled in calculateSetStrings
            }

            const repsArray = getRepsArray(level, exerciseDetails.MG_num || 0);
            let setStrings = calculateSetStrings(exerciseDetails, estimated1RM, repsArray, level, intensity);

            if (exerciseDetails.eName === "Weighted Pull Up" || exerciseDetails.eName === "Weighted Chin Up") {
                if (setStrings.length > 0) {
                    setStrings.pop(); // Reduce sets by 1
                }
                setStrings = setStrings.map(s => {
                    if (s.includes('회')) {
                        return s.replace(/(\d+)(회)/, (match, reps, unit) => {
                            const newReps = Math.max(1, parseInt(reps) - 5);
                            return `${newReps}${unit}`;
                        });
                    }
                    return s;
                });
            }

            const setsSpan = document.createElement('span');
            setsSpan.className = 'exercise-sets';
            setsSpan.textContent = setStrings.join(' / ');

            item.appendChild(document.createElement('br'));
            item.appendChild(setsSpan);
        });

        isWeightsCalculated = true;
    };

    // Process embedded data
    allTestCases = allTestCasesData;
    const exerciseCatalog = exerciseCatalogData;
    M_ratio_weight = ratiosData.M_ratio_weight;
    F_ratio_weight = ratiosData.F_ratio_weight;

    exerciseCatalog.forEach(exercise => {
        if (exercise.kName) {
            kNameToExerciseDetailsMap.set(exercise.kName, exercise);
        }
    });

    // Populate datalist for other exercises (ADDED)
    kNameToExerciseDetailsMap.forEach((value, key) => {
        const option = document.createElement('option');
        option.value = key; // Use kName for display and selection
        exerciseOptionsDatalist.appendChild(option);
    });

    console.log(`${allTestCases.length} test cases loaded from embedded data.`);
    console.log(`${kNameToExerciseDetailsMap.size} exercises mapped from embedded data.`);
    console.log(`Weight ratios loaded from embedded data.`);

    // Filters that reset the entire routine
    [genderFilter, levelFilter, splitFilter].forEach(filter => {
        filter.addEventListener('change', () => {
            const selectedWeek = document.querySelector('.week-tab.active')?.dataset.week || 'week1';
            updateRoutineDisplay(selectedWeek);
        });
    });

    freqFilter.addEventListener('change', () => {
        updateSplitOptions();
        const selectedWeek = document.querySelector('.week-tab.active')?.dataset.week || 'week1';
        updateRoutineDisplay(selectedWeek);
    });

    // Duration filter: Shortens routine, but keeps weights if they were calculated
    durationFilter.addEventListener('change', () => {
        const wereWeightsCalculated = isWeightsCalculated;
        const selectedWeek = document.querySelector('.week-tab.active')?.dataset.week || 'week1';
        updateRoutineDisplay(selectedWeek);
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
    const updateExperienceDetails = () => {
    const selectedValue = document.querySelector('input[name="experience"]:checked').value;

    // 공통: other-exercise 관련 입력 기본 숨김
    otherExerciseSearch.classList.add('hidden');
    expWeightOther.classList.add('hidden');
    expRepsOther.classList.add('hidden');

    if (selectedValue === 'back-squat') {
        detailsBackSquat.classList.remove('hidden');
        detailsBenchPress.classList.add('hidden');
    } else if (selectedValue === 'bench-press') {
        detailsBackSquat.classList.add('hidden');
        detailsBenchPress.classList.remove('hidden');
    } else if (selectedValue === 'other-exercise') {
        detailsBackSquat.classList.add('hidden');
        detailsBenchPress.classList.add('hidden');
        // 실제로 존재하는 입력칸만 보여주기
        otherExerciseSearch.classList.remove('hidden');
        expWeightOther.classList.remove('hidden');
        expRepsOther.classList.remove('hidden');
    } else {
        // unknown
        detailsBackSquat.classList.add('hidden');
        detailsBenchPress.classList.add('hidden');
    }
    };

    // Set initial view
    updateSplitOptions();
    updateRoutineDisplay('week1'); // Load week1 by default

    // --- Week Tab Logic ---
    document.querySelectorAll('.week-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            const selectedWeek = tab.dataset.week;
            updateRoutineDisplay(selectedWeek);
        });
    });

    // --- Experience Radio Logic ---
    experienceRadios.forEach(radio => {
        radio.addEventListener('change', updateExperienceDetails);
    });

    updateExperienceDetails();

    // --- Weight Calculation Button ---
    calculateWeightsBtn.addEventListener('click', renderCalculatedWeights);

        hideWeightsBtn.addEventListener('click', () => {
            document.querySelectorAll('#routine-display .exercise-sets').forEach(span => {
                span.style.display = 'none';
            });
            isWeightsCalculated = false;
        });
    });