document.addEventListener('DOMContentLoaded', () => {
  // --- UI Elements ---
  const userHistorySelect = document.getElementById('user-history-select');
  const historyDisplay    = document.getElementById('history-display');
  const bNameFilter       = document.getElementById('b-name-filter');
  const tIdFilter         = document.getElementById('t-id-filter');
  const catalogDisplay    = document.getElementById('catalog-display');
  const generateBtn       = document.getElementById('generate-btn');
  const promptOutput      = document.getElementById('prompt-output');

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
    // Body Part 목록
    const bNames = [...new Set(
      exercises.map(ex => (ex.b_name ?? ex.bName ?? 'Unknown'))
    )].sort((a, b) => a.localeCompare(b));

    bNameFilter.innerHTML = '';
    const optAllB = document.createElement('option');
    optAllB.value = 'all';
    optAllB.textContent = 'All Body Parts';
    bNameFilter.appendChild(optAllB);
    bNames.forEach(name => {
      const opt = document.createElement('option');
      opt.value = String(name);
      opt.textContent = String(name);
      bNameFilter.appendChild(opt);
    });

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

    tIdFilter.innerHTML = '';
    const optAllT = document.createElement('option');
    optAllT.value = 'all';
    optAllT.textContent = 'All Tools';
    tIdFilter.appendChild(optAllT);
    tIds.forEach(id => {
      const opt = document.createElement('option');
      opt.value = id;
      opt.textContent = `Tool ID: ${id}`;
      tIdFilter.appendChild(opt);
    });
  }

  function displayExercises(exercises) {
    catalogDisplay.innerHTML = '';
    if (!exercises.length) {
      catalogDisplay.textContent = 'No exercises found for the selected filters.';
      return;
    }

    exercises.forEach((ex) => {
      const key   = ex._exKey ?? String(ex.e_text_id ?? ex.eTextId ?? ex.e_name ?? ex.eName);
      const name  = ex.e_name ?? ex.eName ?? '(no name)';
      const bname = ex.b_name ?? ex.bName ?? 'Unknown';
      const tool  = ex.t_id ?? ex.tId ?? '-';

      const item = document.createElement('div');
      item.className = 'catalog-item';

      const checkbox = document.createElement('input');
      checkbox.type = 'checkbox';
      checkbox.id = `ex-${key}`;
      checkbox.dataset.id = key;
      checkbox.checked = true;

      const label = document.createElement('label');
      label.htmlFor = checkbox.id;
      label.textContent = `${name} (${bname}, Tool: ${tool})`;

      item.appendChild(checkbox);
      item.appendChild(label);
      catalogDisplay.appendChild(item);
    });
  }

  function filterExercises() {
    const selectedBName = bNameFilter.value;
    const selectedTId   = tIdFilter.value;

    const filtered = allExercises.filter(ex => {
      const b = String(ex.b_name ?? ex.bName ?? 'Unknown');
      const t = String(ex.t_id ?? ex.tId ?? '');
      const okB = (selectedBName === 'all') || (b === selectedBName);
      const okT = (selectedTId === 'all') || (t === selectedTId);
      return okB && okT;
    });

    displayExercises(filtered);
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
      populateExerciseFilters(allExercises); // ✅ 이제 정의됨
      displayExercises(allExercises);
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

  bNameFilter.addEventListener('change', filterExercises);
  tIdFilter.addEventListener('change', filterExercises);

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
      return;
    }

    promptOutput.textContent = 'Generating prompt... Please wait.';
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
      })
      .catch(error => {
        promptOutput.textContent = `Error generating prompt: ${error.message}`;
        console.error('Error generating prompt:', error);
      })
      .finally(() => { generateBtn.disabled = false; });
  });
});
