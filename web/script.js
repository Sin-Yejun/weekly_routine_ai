document.addEventListener('DOMContentLoaded', () => {
  // --- UI Elements ---
  const userHistorySelect = document.getElementById('user-history-select');
  const historyDisplay    = document.getElementById('history-display');
  const bNameFilterContainer = document.getElementById('b-name-filter-container');
  const tIdFilterContainer   = document.getElementById('t-id-filter-container');
  const catalogDisplay    = document.getElementById('catalog-display');
  const generateBtn       = document.getElementById('generate-btn');
  const promptOutput      = document.getElementById('prompt-output');
  const outputDisplay     = document.getElementById('output-display');

  // User Info Inputs
  const genderSelect   = document.getElementById('gender-select');
  const weightInput    = document.getElementById('weight-input');
  const levelSelect    = document.getElementById('level-select');
  const typeSelect     = document.getElementById('type-select');
  const frequencyInput = document.getElementById('frequency-input');

  // --- State ---
  let allExercises   = [];         // 전체 운동 목록
  let exerciseById   = new Map();  // key -> exercise 객체
  let currentHistory = [];         // 현재 유저의 전체 히스토리
  let selectedHistory = [];        // 체크된 히스토리만 모음
  let selectedCatalogExercises = new Set(); // 수동으로 선택된 카탈로그 운동

  // --- Constants ---
  const TOOL_ID_NAMES = {
    '1': '바벨',
    '2': '덤벨',
    '3': '머신',
    '4': '맨몸',
    '5': 'EZ',
    '6': '케틀벨',
    '7': '기타',
    '': '기타' // Default for unknown/empty tool IDs
  };

  // -------- Helpers --------
  // 운동 객체에 일관된 키를 부여하고 Map 구축
  function assignExerciseKeys(exercises) {
    exerciseById.clear();
    exercises.forEach((ex, i) => {
      if (!ex._exKey) {
        const eName   = ex.e_name ?? ex.eName ?? 'exercise';
        const rawId   = ex.e_text_id ?? ex.eTextId;
        ex._exKey     = String(rawId ?? `${eName}_${i}`); // 안정적 fallback
      }
      exerciseById.set(ex._exKey, ex);
    });
  }

  function populateExerciseFilters(exercises) {
    // Helper to create checkboxes
    const createCheckboxes = (container, items, type, map = null) => {
      container.innerHTML = ''; // Clear previous content

      // Create "All" checkbox
      const allCheckbox = document.createElement('input');
      allCheckbox.type = 'checkbox';
      allCheckbox.id = `${type}-all`;
      allCheckbox.dataset.value = 'all';
      allCheckbox.checked = true; // Default to all selected
      allCheckbox.className = 'filter-all-checkbox';

      const allLabel = document.createElement('label');
      allLabel.htmlFor = allCheckbox.id;
      allLabel.textContent = `All ${type === 'bname' ? 'Body Parts' : 'Tools'}`;
      allLabel.className = 'filter-all-label';

      const allDiv = document.createElement('div');
      allDiv.className = 'filter-option';
      allDiv.appendChild(allCheckbox);
      allDiv.appendChild(allLabel);
      container.appendChild(allDiv);

      allCheckbox.addEventListener('change', (event) => {
        container.querySelectorAll(`input[type="checkbox"]:not(.filter-all-checkbox)`).forEach(cb => {
          cb.checked = event.target.checked;
        });
        filterExercises();
      });

      items.forEach((item, index) => {
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.id = `${type}-${item.replace(/\s+/g, '-')}-${index}`; // Unique ID
        checkbox.dataset.value = item;
        checkbox.checked = true; // Default to all selected
        checkbox.className = 'filter-item-checkbox';

        const label = document.createElement('label');
        label.htmlFor = checkbox.id;
        label.textContent = map ? map[item] || item : item; // Use map for display if provided
        label.className = 'filter-item-label';

        const itemDiv = document.createElement('div');
        itemDiv.className = 'filter-option';
        itemDiv.appendChild(checkbox);
        itemDiv.appendChild(label);
        container.appendChild(itemDiv);

        checkbox.addEventListener('change', () => {
          // If any individual checkbox is unchecked, uncheck "All"
          if (!checkbox.checked) {
            allCheckbox.checked = false;
          } else {
            // If all individual checkboxes are checked, check "All"
            const allOthersChecked = Array.from(container.querySelectorAll(`input[type="checkbox"]:not(.filter-all-checkbox)`)).every(cb => cb.checked);
            if (allOthersChecked) {
              allCheckbox.checked = true;
            }
          }
          filterExercises();
        });
      });
    };

    // Body Part 목록
    const bNames = [...new Set(
      exercises.map(ex => (ex.b_name ?? ex.bName ?? 'Unknown'))
    )].sort((a, b) => a.localeCompare(b));
    createCheckboxes(bNameFilterContainer, bNames, 'bname');

    // Tool 목록
    const tIds = [...new Set(
      exercises.map(ex => (ex.t_id ?? ex.tId ?? ''))
    )].filter(v => v !== '').map(String);

    // 숫자-문자 섞여 있어도 보기 좋게 정렬
    tIds.sort((a, b) => {
      const na = Number(a), nb = Number(b);
      const aNum = !isNaN(na), bNum = !isNaN(nb);
      if (aNum && bNum) return na - nb;
      if (aNum) return -1;
      if (bNum) return 1;
      return a.localeCompare(b);
    });
    createCheckboxes(tIdFilterContainer, tIds, 'tid', TOOL_ID_NAMES);
  }

  function displayExercises(exercises) {
    // Clear existing items that are no longer in the filtered list
    const currentCatalogItems = new Set();
    catalogDisplay.querySelectorAll('.catalog-item').forEach(item => {
      const key = item.querySelector('input[type="checkbox"]').dataset.id;
      currentCatalogItems.add(key);
    });

    const filteredExerciseKeys = new Set(exercises.map(ex => ex._exKey));

    // Remove items that are no longer in the filtered list
    catalogDisplay.querySelectorAll('.catalog-item').forEach(item => {
      const key = item.querySelector('input[type="checkbox"]').dataset.id;
      if (!filteredExerciseKeys.has(key)) {
        item.remove();
      }
    });

    // Add or update items
    exercises.forEach((ex) => {
      const key   = ex._exKey ?? String(ex.e_text_id ?? ex.eTextId ?? ex.e_name ?? ex.eName);
      const name  = ex.e_name ?? ex.eName ?? '(no name)';
      const bname = ex.b_name ?? ex.bName ?? 'Unknown';
      const tool  = ex.t_id ?? ex.tId ?? ''; // Get raw tool ID

      let item = catalogDisplay.querySelector(`#ex-item-${key}`); // Check if item already exists
      let checkbox;
      let label;

      if (!item) {
        // Create new item if it doesn't exist
        item = document.createElement('div');
        item.className = 'catalog-item';
        item.id = `ex-item-${key}`; // Add an ID to the item div for easier lookup

        checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.id = `ex-${key}`;
        checkbox.dataset.id = key;

        label = document.createElement('label');
        label.htmlFor = checkbox.id;

        item.appendChild(checkbox);
        item.appendChild(label);
        catalogDisplay.appendChild(item);

        // Add event listener for manual selection
        checkbox.addEventListener('change', () => {
          if (checkbox.checked) {
            selectedCatalogExercises.add(key);
          } else {
            selectedCatalogExercises.delete(key);
          }
        });
      } else {
        checkbox = item.querySelector('input[type="checkbox"]');
        label = item.querySelector('label');
      }

      // Update content and checked state
      label.textContent = `${name} (${bname}, Tool: ${TOOL_ID_NAMES[tool] || tool})`;
      checkbox.checked = selectedCatalogExercises.has(key); // Use stored state
      checkbox.disabled = false; // Ensure it's enabled if it's in the filtered list
    });

    if (!exercises.length && catalogDisplay.children.length === 0) {
      catalogDisplay.textContent = 'No exercises found for the selected filters.';
    } else if (exercises.length > 0 && catalogDisplay.textContent === 'No exercises found for the selected filters.') {
      // Clear the "No exercises found" message if exercises are now present
      catalogDisplay.textContent = '';
    }
  }

  function filterExercises() {
    const selectedBNames = Array.from(bNameFilterContainer.querySelectorAll('input[type="checkbox"]'))
                                .filter(cb => cb.checked && cb.dataset.value !== 'all')
                                .map(cb => cb.dataset.value);
    const selectedTIds   = Array.from(tIdFilterContainer.querySelectorAll('input[type="checkbox"]'))
                                .filter(cb => cb.checked && cb.dataset.value !== 'all')
                                .map(cb => cb.dataset.value);

    const filtered = allExercises.filter(ex => {
      const b = String(ex.b_name ?? ex.bName ?? 'Unknown');
      const t = String(ex.t_id ?? ex.tId ?? '');

      const okB = selectedBNames.length === 0 || selectedBNames.includes(b);
      const okT = selectedTIds.length === 0 || selectedTIds.includes(t);

      return okB && okT;
    });

    // Update the display based on the filtered exercises
    displayExercises(filtered);

    // Now, iterate through all catalog items and disable/enable based on filter
    catalogDisplay.querySelectorAll('.catalog-item').forEach(item => {
      const checkbox = item.querySelector('input[type="checkbox"]');
      const key = checkbox.dataset.id;
      const ex = exerciseById.get(key); // Get the full exercise object

      if (ex) {
        const b = String(ex.b_name ?? ex.bName ?? 'Unknown');
        const t = String(ex.t_id ?? ex.tId ?? '');

        const matchesFilter = (selectedBNames.length === 0 || selectedBNames.includes(b)) &&
                              (selectedTIds.length === 0 || selectedTIds.includes(t));

        checkbox.disabled = !matchesFilter;
        // If it doesn't match the filter, uncheck it (but preserve manual check if filter is re-applied)
        if (!matchesFilter) {
          checkbox.checked = false;
          selectedCatalogExercises.delete(key); // Remove from selected set if it's filtered out
        } else {
          // If it matches the filter, restore its previous checked state
          checkbox.checked = selectedCatalogExercises.has(key);
        }
      }
    });

    // If no exercises match the filter, display the message
    if (filtered.length === 0) {
      catalogDisplay.textContent = 'No exercises found for the selected filters.';
    } else if (catalogDisplay.textContent === 'No exercises found for the selected filters.') {
      // Clear the "No exercises found" message if exercises are now present
      catalogDisplay.textContent = '';
    }
  }

  function displayHistory(history) {
    historyDisplay.innerHTML = '';
    currentHistory = Array.isArray(history) ? history : [];

    if (!currentHistory.length) {
      historyDisplay.textContent = 'No workout history found for this user.';
      selectedHistory = [];
      return;
    }

    // 기본값: 전체 선택
    selectedHistory = [...currentHistory];

    currentHistory.forEach((session, index) => {
      const item = document.createElement('div');
      item.className = 'history-item';

      const checkbox = document.createElement('input');
      checkbox.type = 'checkbox';
      checkbox.id = `hist-${index}`;
      checkbox.dataset.index = String(index);
      checkbox.checked = true;

      const summary = Array.isArray(session.session_data)
        ? session.session_data.map(s =>
            s.eName || s.e_name || s.eTextId || s.e_text_id || 'Unknown'
          ).join(', ')
        : 'No exercises';

      const label = document.createElement('label');
      label.htmlFor = checkbox.id;
      label.textContent =
        `Workout ${index + 1}: ${session.duration ? session.duration + 'min - ' : ''}${summary.substring(0, 50)}...`;

      item.appendChild(checkbox);
      item.appendChild(label);
      historyDisplay.appendChild(item);
    });

    const recomputeSelectedHistory = () => {
      selectedHistory = Array.from(
        historyDisplay.querySelectorAll('input[type="checkbox"]')
      )
        .filter(cb => cb.checked)
        .map(cb => currentHistory[Number(cb.dataset.index)]);
    };

    historyDisplay
      .querySelectorAll('input[type="checkbox"]')
      .forEach(cb => cb.addEventListener('change', recomputeSelectedHistory));
  }

  // -------- Initial Data Fetching --------
  // Users
  fetch('/api/users')
    .then(response => response.json())
    .then(users => {
      userHistorySelect.innerHTML = '<option value="">-- Select a User --</option>';
      users.forEach(user => {
        const option = document.createElement('option');
        option.value = user.id;
        option.textContent = `User ID: ${user.id}`;
        userHistorySelect.appendChild(option);
      });
    })
    .catch(error => {
      userHistorySelect.innerHTML = '<option value="">Error loading users</option>';
      console.error('Error fetching users:', error);
    });

  // Exercises
  fetch('/api/exercises')
    .then(response => response.json())
    .then(exercises => {
      allExercises = Array.isArray(exercises) ? exercises : [];
      assignExerciseKeys(allExercises);      // 키 부여 + Map 구성

      // Initialize selectedCatalogExercises with all exercises
      allExercises.forEach(ex => {
        selectedCatalogExercises.add(ex._exKey);
      });

      populateExerciseFilters(allExercises); // ✅ 이제 정의됨
      displayExercises(allExercises); // This will now use selectedCatalogExercises
    })
    .catch(error => {
      catalogDisplay.textContent = 'Error loading exercise catalog.';
      console.error('Error fetching exercises:', error);
    });

  // -------- Event Listeners --------
  userHistorySelect.addEventListener('change', () => {
    const selectedUserId = userHistorySelect.value;
    if (!selectedUserId) {
      historyDisplay.textContent = 'Select a user to see their workout history.';
      selectedHistory = [];
      return;
    }

    historyDisplay.textContent = 'Loading history...';
    fetch(`/api/users/${selectedUserId}/history`)
      .then(response => response.json())
      .then(history => displayHistory(history))
      .catch(error => {
        historyDisplay.textContent = 'Error loading history.';
        console.error('Error fetching history:', error);
      });
  });

  

  generateBtn.addEventListener('click', () => {
    // Gather User Info
    const userInfo = {
      gender: genderSelect.value,
      weight: parseFloat(weightInput.value),
      level: levelSelect.value,
      type: typeSelect.value,
      frequency: Math.min(7, Math.max(1, parseInt(frequencyInput.value, 10) || 3))
    };

    // Gather Selected Exercises from Catalog (Map으로 복구)
    const selectedExercises = Array.from(
      catalogDisplay.querySelectorAll('input[type="checkbox"]:checked')
    )
      .map(cb => exerciseById.get(cb.dataset.id))
      .filter(Boolean);

    if (selectedExercises.length === 0) {
      promptOutput.textContent = 'Please select at least one exercise from the catalog.';
      outputDisplay.textContent = ''; // Clear output display
      return;
    }

    promptOutput.textContent = 'Generating prompt...';
    outputDisplay.textContent = 'Building ideal output from history...';
    const modelOutputEl = document.getElementById('model-output');
    if (modelOutputEl) modelOutputEl.textContent = 'Calling model...';

    generateBtn.disabled = true;

    fetch('/api/generate-prompt', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        userInfo,
        workoutHistory: selectedHistory,
        exerciseCatalog: selectedExercises
      })
    })
      .then(response => {
        if (!response.ok) {
          return response.json().then(err => { throw new Error(err.error || 'Unknown error'); });
        }
        return response.json();
      })
      .then(data => {
        promptOutput.textContent = data.prompt;
        outputDisplay.textContent = data.output; // Display the ideal output

        return fetch('/api/infer', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            prompt: data.prompt,
            temperature: 0.0,
            max_tokens: 1024
          })
        })
        .then(r => {
          if (!r.ok) return r.json().then(err => { throw new Error(err.error || 'Model error'); });
          return r.json();
        })
        .then(model => {
          if (modelOutputEl) modelOutputEl.textContent = model.response;
        });
      })
      .catch(error => {
        const errorMessage = `Error: ${error.message}`;
        promptOutput.textContent = errorMessage;
        outputDisplay.textContent = errorMessage;
        if (modelOutputEl) modelOutputEl.textContent = errorMessage;
        console.error('Error generating prompt:', error);
      })
      .finally(() => { generateBtn.disabled = false; });
  });
});
