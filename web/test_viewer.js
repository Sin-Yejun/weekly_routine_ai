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
    const modal = document.getElementById('similar-exercises-modal');
    const modalCloseBtn = modal ? modal.querySelector('.close-btn') : null;
    const modalList = document.getElementById('similar-exercises-list');


    // --- Experience Inputs ---
    const experienceRadios = document.querySelectorAll('input[name="experience"]');
    const detailsBackSquat = document.getElementById('details-back-squat');
    const detailsBenchPress = document.getElementById('details-bench-press');

    const otherExerciseSearch = document.getElementById('other-exercise-search');
    const expWeightOther      = document.getElementById('exp-weight-other');
    const expRepsOther        = document.getElementById('exp-reps-other');
    const exerciseOptionsDatalist = document.getElementById('exercise-options');

    let allTestCases = [];
    const kNameToExerciseDetailsMap = new Map();
    const eNameToExerciseDetailsMap = new Map();
    let M_ratio_weight = {};
    let F_ratio_weight = {};
    let exerciseSimilarityMap = {};
    let similarToMainMap = {};
    let isOverview = false;
    const overviewToggle = document.getElementById('overview-toggle');
    const weekTabsEl = document.querySelector('.week-tabs');

    let currentDisplayedTestCase = null;
    let currentWeek = 'week1';
    let currentExerciseInfo = { day: null, index: -1 };


    // --- Functions ---

    const trimExercisesForDuration = (routineForWeek, selectedDuration) => {
        if (!routineForWeek) return {};
        const cloned = JSON.parse(JSON.stringify(routineForWeek));
        Object.values(cloned).forEach(exercises => {
            if (selectedDuration == 45) {
                if (exercises.length > 1) exercises.pop();
            } else if (selectedDuration == 30) {
                if (exercises.length > 1) exercises.pop();
                if (exercises.length > 1) exercises.pop();
            }
        });
        return cloned;
    };

    const renderWeekCardHTML = (weekKey, routineForWeek, selectedDuration) => {
      if (!routineForWeek || routineForWeek.error) {
        return `
          <div class="overview-card">
            <div class="week-title">${weekKey.toUpperCase()}</div>
            <p>${routineForWeek?.error ? ('생성 실패: ' + routineForWeek.error) : 'No data'}</p>
          </div>`;
      }
      const trimmed = trimExercisesForDuration(routineForWeek, selectedDuration);
      let html = `<div class="overview-card"><div class="week-title">${weekKey.toUpperCase()}</div>`;
      for (const [day, exercises] of Object.entries(trimmed)) {
          html += `<div class="day-header">${day} (운동 수: ${exercises.length})</div><ul>`;
          exercises.forEach((kName, index) => {
            const bName = kNameToExerciseDetailsMap.get(kName)?.bName || 'N/A';
            html += `<li class="exercise-item" data-kname="${kName}" data-day="${day}" data-index="${index}">${bName} - ${kName}</li>`;
          });
          html += `</ul>`;
        }
        html += `</div>`;
        return html;
    };

    const splitLabels = {
        '2': '분할 (상체 / 하체)',
        '3': '분할 (밀기 / 당기기 / 하체)',
        '4': '분할 (하체 / 가슴 / 등 / 어깨)',
        '5': '분할 (하체 / 가슴 / 등 / 어깨 / 팔+복근)'
    };

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

    const getRepsArray = (level, mgNum, gender) => {
        if (gender === 'F') {
            if (mgNum <= 2) { // Isolation
                switch (level) {
                    case 'Beginner': return [20, 20, 15];
                    case 'Novice': return [20, 20, 15, 15];
                    default: return [20, 20, 15, 15, 15];
                }
            } else { // Compound
                const femaleLevelSets = {
                    "Beginner": [15, 12, 10],
                    "Novice": [15, 12, 10, 8],
                    "Intermediate": [15, 12, 10, 9, 8],
                    "Advanced": [15, 12, 10, 9, 8],
                    "Elite": [15, 12, 10, 9, 8],
                };
                return femaleLevelSets[level] || femaleLevelSets['Intermediate'];
            }
        }

        // Existing logic for Male
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

    const formatWeightRange = (baseWeight, reps, intensity, tool_en, gender) => {
        const tool = (tool_en || 'etc').toLowerCase();
        
        let normalSetWeight = baseWeight;

        let intensityMultiplier = 1.0;
        if (gender === 'F') {
            if (intensity === 'Low') {
                intensityMultiplier = 0.8;
            } else if (intensity === 'Normal') {
                intensityMultiplier = 0.9;
            }
        } else {
            if (intensity === 'Low') {
                intensityMultiplier = 0.9;
            } else if (intensity === 'High') {
                intensityMultiplier = 1.1;
            }
        }

        let effectiveWeight = normalSetWeight * intensityMultiplier;

        let roundedEffectiveWeight;
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

        return `${roundedEffectiveWeight}kg ${reps}회`;
    };

    const calculateSetStrings = (exercise, estimated1RM, repsArray, level, intensity, gender) => {
        const { eName, eInfoType, tool_en } = exercise;
        const exerciseRatio = M_ratio_weight[eName] || F_ratio_weight[eName];
        const isAssistedMachine = eName === "Assisted Pull Up Machine" || eName === "Assisted Dip Machine";

        if (isAssistedMachine && exerciseRatio) {
            if (level === 'Beginner' || level === 'Novice') {
                return repsArray.map((reps, index) => {
                    let baseWeight = estimated1RM;
                    return formatWeightRange(baseWeight, reps, intensity, tool_en, gender);
                });
            } else {
                return repsArray.map(reps => {
                    let baseWeight;
                    if (reps >= 12) {
                        baseWeight = estimated1RM;
                    } else if (reps >= 10) {
                        baseWeight = estimated1RM * 0.8;
                    } else {
                        baseWeight = estimated1RM * 0.6;
                    }
                    return formatWeightRange(baseWeight, reps, intensity, tool_en, gender);
                });
            }
        }
        else if (eInfoType === 2) {
            if (exerciseRatio) {
                const customReps = Math.round(estimated1RM);
                const numSets = repsArray.length;
                return Array(numSets).fill(`${customReps}회`);
            } else {
                return ['Calculation not available.'];
            }
        }
        else {
            if (exerciseRatio) {
                return repsArray.map((reps, index) => {
                    let baseWeight;
                    if (index === 0) {
                        baseWeight = estimated1RM * 0.4;
                    }
                    else if (index === 1) {
                        baseWeight = estimated1RM * 0.6;
                    }
                    else {
                        baseWeight = estimated1RM / (1 + reps / 30);
                    }
                    return formatWeightRange(baseWeight, reps, intensity, tool_en);
                });
            } else {
                return ['Calculation not available.'];
            }
        }
    };

    const updateRoutineDisplay = (selectedWeek = 'week1', fromFilterChange = false) => {
      if (fromFilterChange) {
        const selectedGender = genderFilter.value;
        const selectedLevel = levelFilter.value;
        const selectedFreq = parseInt(freqFilter.value, 10);
        const selectedSplit = splitFilter.value;

        const foundCase = allTestCases.find(c =>
            c.gender === selectedGender &&
            c.level === selectedLevel &&
            c.freq === selectedFreq &&
            c.split_id === selectedSplit
        );
        currentDisplayedTestCase = foundCase ? JSON.parse(JSON.stringify(foundCase)) : null;
      }

      currentWeek = selectedWeek;

      document.querySelectorAll('.week-tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.week === currentWeek);
      });

      const selectedDuration = parseInt(durationFilter.value, 10);

      if (isOverview && currentDisplayedTestCase) {
        let gridHTML = `<div class="overview-scroll">`;
        ['week1', 'week2', 'week3', 'week4'].forEach(wk => {
          gridHTML += renderWeekCardHTML(wk, currentDisplayedTestCase[wk], selectedDuration);
        });
        gridHTML += `</div>`;
        routineDisplay.innerHTML = gridHTML;
      } else if (currentDisplayedTestCase && currentDisplayedTestCase[currentWeek]) {
        const routineForWeek = currentDisplayedTestCase[currentWeek];
        if (routineForWeek.error) {
          routineDisplay.innerHTML = `<p style="color:#ffcc00;">Routine generation failed for this week: ${routineForWeek.error}</p>`;
        } else {
          const trimmed = trimExercisesForDuration(routineForWeek, selectedDuration);
          let html = '';
          for (const [day, exercises] of Object.entries(trimmed)) {
            html += `<div class="day-header">${day} (운동 수: ${exercises.length})</div><ul>`;
            exercises.forEach((kName, index) => {
              const bName = kNameToExerciseDetailsMap.get(kName)?.bName || 'N/A';
              html += `<li class="exercise-item" data-kname="${kName}" data-day="${day}" data-index="${index}">${bName} - ${kName}</li>`;
            });
            html += `</ul>`;
          }
          routineDisplay.innerHTML = html;
        }
      } else {
        routineDisplay.innerHTML = '<p>No matching routine found for the selected criteria.</p>';
      }
      
      renderCalculatedWeights();
    };

    overviewToggle?.addEventListener('click', () => {
      isOverview = !isOverview;
      overviewToggle.classList.toggle('active', isOverview);
      overviewToggle.setAttribute('aria-pressed', String(isOverview));

      overviewToggle.textContent = isOverview ? '월 루틴 닫기' : '월 루틴 펼치기';

      weekTabsEl?.classList.toggle('hidden', isOverview);

      document.querySelector('.container')?.classList.toggle('overview-mode', isOverview);
      const currentWeek = document.querySelector('.week-tab.active')?.dataset.week || 'week1';
      updateRoutineDisplay(currentWeek);
    });

    const renderCalculatedWeights = () => {
        const expChecked = document.querySelector('input[name="experience"]:checked');
        if (!expChecked) return;
        const selectedExperience = expChecked.value;
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
            } else if (selectedExperience === 'other-exercise') {
                selectedExerciseKName = otherExerciseSearch.value;
                weightInput = expWeightOther;
                repsInput = expRepsOther;

                const exerciseDetails = kNameToExerciseDetailsMap.get(selectedExerciseKName);
                if (!exerciseDetails) {
                    return;
                }
                baseExerciseName = exerciseDetails.eName;
            }

            const weight = parseFloat(weightInput.value);
            const reps = parseInt(repsInput.value, 10);

            if (isNaN(weight) || isNaN(reps) || reps <= 0) {
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
            }

            const repsArray = getRepsArray(level, exerciseDetails.MG_num || 0, gender);
            let setStrings = calculateSetStrings(exerciseDetails, estimated1RM, repsArray, level, intensity, gender);

            if (exerciseDetails.eName === "Weighted Pull Up" || exerciseDetails.eName === "Weighted Chin Up") {
                if (setStrings.length > 0) {
                    setStrings.pop();
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
    };

    const handleExerciseClick = (event) => {
        if (!event.target.classList.contains('exercise-item')) return;

        const { kname, day, index } = event.target.dataset;
        const eName = kNameToExerciseDetailsMap.get(kname)?.eName;

        if (!eName) return;

        currentExerciseInfo = { day, index: parseInt(index) };

        modalList.innerHTML = 'Loading...';
        modal.style.display = 'flex';

        let similarExercisesEn = exerciseSimilarityMap[eName];

        if (!similarExercisesEn) {
            const mainExercises = similarToMainMap[eName];
            if (mainExercises) {
                similarExercisesEn = exerciseSimilarityMap[mainExercises[0]];
            }
        }

        if (!similarExercisesEn || similarExercisesEn.length === 0) {
            modalList.innerHTML = 'No similar exercises found.';
            return;
        }

        const similarExercisesKo = [];
        for (const en_name of similarExercisesEn) {
            const exerciseDetails = eNameToExerciseDetailsMap.get(en_name);
            if (exerciseDetails) {
                similarExercisesKo.push({
                    eName: en_name,
                    kName: exerciseDetails.kName || en_name,
                    bName: exerciseDetails.bName || "N/A"
                });
            }
        }

        modalList.innerHTML = similarExercisesKo.map(ex => 
            `<div class="similar-exercise-item" data-ename="${ex.eName}">${ex.bName} - ${ex.kName}</div>`
        ).join('');
    };

    const handleSimilarExerciseSelect = (event) => {
        if (!event.target.classList.contains('similar-exercise-item')) return;
        if (!currentDisplayedTestCase) return;

        const newEName = event.target.dataset.ename;
        const newExerciseDetails = eNameToExerciseDetailsMap.get(newEName);

        if (!newExerciseDetails) {
            alert('Could not find details for the selected exercise.');
            return;
        }

        const { day, index } = currentExerciseInfo;

        currentDisplayedTestCase[currentWeek][day][index] = newExerciseDetails.kName;

        modal.style.display = 'none';
        updateRoutineDisplay(currentWeek, false);
    };

    // Process embedded data
    allTestCases = allTestCasesData;
    const exerciseCatalog = exerciseCatalogData;
    M_ratio_weight = ratiosData.M_ratio_weight;
    F_ratio_weight = ratiosData.F_ratio_weight;
    
    if (typeof similar_exercises !== 'undefined') {
        similar_exercises.forEach(item => {
            exerciseSimilarityMap[item.main_exercise] = item.similar;
            item.similar.forEach(similar_exercise => {
                if (!similarToMainMap[similar_exercise]) {
                    similarToMainMap[similar_exercise] = [];
                }
                similarToMainMap[similar_exercise].push(item.main_exercise);
            });
        });
    }

    exerciseCatalog.forEach(exercise => {
        if (exercise.kName) kNameToExerciseDetailsMap.set(exercise.kName, exercise);
        if (exercise.eName) eNameToExerciseDetailsMap.set(exercise.eName, exercise);
    });

    kNameToExerciseDetailsMap.forEach((value, key) => {
        const option = document.createElement('option');
        option.value = key;
        exerciseOptionsDatalist.appendChild(option);
    });

    // --- Event Listeners ---

    [genderFilter, levelFilter, freqFilter, splitFilter, durationFilter, intensityFilter].forEach(filter => {
        filter.addEventListener('change', () => {
            const selectedWeek = document.querySelector('.week-tab.active')?.dataset.week || 'week1';
            updateRoutineDisplay(selectedWeek, true);
        });
    });

    const updateExperienceDetails = () => {
        const selectedValue = document.querySelector('input[name="experience"]:checked')?.value ?? 'unknown';

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
            otherExerciseSearch.classList.remove('hidden');
            expWeightOther.classList.remove('hidden');
            expRepsOther.classList.remove('hidden');
        } else {
            detailsBackSquat.classList.add('hidden');
            detailsBenchPress.classList.add('hidden');
        }
    };

    // Set initial view
    updateSplitOptions();
    updateRoutineDisplay('week1', true);

    // --- Week Tab Logic ---
    document.querySelectorAll('.week-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            const selectedWeek = tab.dataset.week;
            updateRoutineDisplay(selectedWeek, false);
        });
    });

    // --- Experience Radio Logic ---
    experienceRadios.forEach(radio => {
        radio.addEventListener('change', () => {
            updateExperienceDetails();
            renderCalculatedWeights();
        });
    });

    [ document.getElementById('exp-weight-bs'), document.getElementById('exp-reps-bs'),
      document.getElementById('exp-weight-bp'), document.getElementById('exp-reps-bp'),
      document.getElementById('exp-weight-other'), document.getElementById('exp-reps-other'),
      otherExerciseSearch
    ].forEach(input => {
        input.addEventListener('change', renderCalculatedWeights);
    });


    updateExperienceDetails();

    // --- Button Logic ---
    calculateWeightsBtn.addEventListener('click', renderCalculatedWeights);

    hideWeightsBtn.addEventListener('click', () => {
        document.querySelectorAll('#routine-display .exercise-sets, #routine-display br').forEach(el => {
            el.remove();
        });
    });

    // --- Modal Logic ---
    if (modal) {
        routineDisplay.addEventListener('click', handleExerciseClick);
        modalCloseBtn.addEventListener('click', () => modal.style.display = 'none');
        modal.addEventListener('click', (event) => {
            if (event.target === modal) {
                modal.style.display = 'none';
            }
        });
        modalList.addEventListener('click', handleSimilarExerciseSelect);
    }
});