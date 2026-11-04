document.addEventListener('DOMContentLoaded', () => {
    const fileInput = document.getElementById('file-input');
    const btnUpload = document.getElementById('btn-upload');
    const uploadStatus = document.getElementById('upload-status');
    const progressSection = document.getElementById('progress-section');
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');
    const resultsSection = document.getElementById('results-section');
    const resultsBody = document.getElementById('results-body');
    const statsSection = document.getElementById('stats-section');
    const searchInput = document.getElementById('search-input');
    const filterSentiment = document.getElementById('filter-sentiment');
    const noResultsMsg = document.getElementById('no-results');
    const jsonInput = document.getElementById('json-input');
    const btnLoadJson = document.getElementById('btn-load-json');
    let allReviews = []; 
    let sortState = { column: null, asc: true };
    let currentSessionId = null; 
    let pieChartInstance = null;
    let barChartInstance = null;
    btnUpload.addEventListener('click', async () => {
        const files = fileInput.files;
        if (files.length === 0) {
            uploadStatus.textContent = 'Выберите хотя бы один файл.';
            uploadStatus.style.color = 'red';
            return;
        }
        btnUpload.disabled = true;
        uploadStatus.textContent = 'Загрузка файлов...';
        uploadStatus.style.color = 'black';
        const formData = new FormData();
        for (const file of files) formData.append('files', file);
        try {
            const uploadRes = await fetch('/api/upload', { method: 'POST', body: formData });
            if (!uploadRes.ok) throw new Error('Ошибка загрузки');
            const uploadData = await uploadRes.json();
            const sessionId = uploadData.session.id;
            uploadStatus.textContent = `Загружено файлов: ${uploadData.files.length}. Запуск анализа...`;
            await fetch(`/api/analyze/${sessionId}`, { method: 'POST' });
            progressSection.classList.remove('hidden');
            resultsSection.classList.add('hidden');
            statsSection.classList.add('hidden');
            pollStatus(sessionId);
        } catch (error) {
            uploadStatus.textContent = `Ошибка: ${error.message}`;
            uploadStatus.style.color = 'red';
            btnUpload.disabled = false;
        }
    });
    async function pollStatus(sessionId) {
        try {
            const res = await fetch(`/api/status/${sessionId}`);
            const data = await res.json();
            progressBar.style.width = `${data.progress}%`;
            progressText.textContent = `Обработано: ${data.processed} из ${data.total} (${data.progress}%)`;
            if (data.status === 'completed') {
                uploadStatus.textContent = 'Анализ завершён!';
                uploadStatus.style.color = 'green';
                loadResults(sessionId);
            } else if (data.status === 'processing' || data.status === 'uploaded') {
                setTimeout(() => pollStatus(sessionId), 1000);
            } else {
                uploadStatus.textContent = `Ошибка анализа: статус ${data.status}`;
                btnUpload.disabled = false;
            }
        } catch (e) {
            console.error('Ошибка опроса статуса', e);
            setTimeout(() => pollStatus(sessionId), 2000);
        }
    }
    async function loadResults(sessionId) {
        currentSessionId = sessionId; 
        try {
            const res = await fetch(`/api/results/${sessionId}`);
            const files = await res.json();
            allReviews = [];
            files.forEach(file => {
                file.reviews.forEach(review => {
                    allReviews.push({
                        ...review,
                        filename: file.filename || 'Без имени',
                        text: review.text || '' 
                    });
                });
            });
            searchInput.value = '';
            filterSentiment.value = 'all';
            sortState = { column: null, asc: true };
            renderTable();
            resultsSection.classList.remove('hidden');
            statsSection.classList.remove('hidden');
            loadStats(sessionId); 
        } catch (e) {
            console.error('Ошибка загрузки результатов', e);
        } finally {
            btnUpload.disabled = false;
        }
    }
    function getSentimentWeight(label) {
        if (label === 'negative') return 1;
        if (label === 'neutral') return 2;
        if (label === 'positive') return 3;
        return 4; 
    }
    function renderTable() {
        const query = searchInput.value.toLowerCase().trim();
        const sentimentFilter = filterSentiment.value;
        let filtered = allReviews.filter(r => {
            const textSafe = (r.text || '').toLowerCase();
            const matchQuery = !query || textSafe.includes(query);
            const matchSentiment = sentimentFilter === 'all' || r.sentiment_label === sentimentFilter;
            return matchQuery && matchSentiment;
        });
        if (sortState.column) {
            filtered.sort((a, b) => {
                let valA = a[sortState.column];
                let valB = b[sortState.column];
                if (sortState.column === 'sentiment_label') {
                    valA = getSentimentWeight(valA);
                    valB = getSentimentWeight(valB);
                } else if (sortState.column === 'sentiment_confidence') {
                    valA = valA || 0;
                    valB = valB || 0;
                } else {
                    valA = (valA || '').toString().toLowerCase();
                    valB = (valB || '').toString().toLowerCase();
                }
                if (valA < valB) return sortState.asc ? -1 : 1;
                if (valA > valB) return sortState.asc ? 1 : -1;
                return 0;
            });
        }
        resultsBody.innerHTML = '';
        if (filtered.length === 0) {
            noResultsMsg.classList.remove('hidden');
        } else {
            noResultsMsg.classList.add('hidden');
            filtered.forEach(review => {
                const tr = document.createElement('tr');
                const label = review.sentiment_label || 'unknown';
                const confidenceText = review.sentiment_manual 
                    ? 'вручную' 
                    : (review.sentiment_confidence ? `${Math.round(review.sentiment_confidence * 100)}%` : '—');              
                const langText = review.language === 'ru' ? '🇷🇺 RU' : (review.language === 'en' ? '🇬🇧 EN' : '?');
                const textSafe = review.text || '';
                const previewText = textSafe.length > 80 ? textSafe.substring(0, 80) + '...' : textSafe;
                tr.innerHTML = `
                    <td>${review.filename}</td>
                    <td title="${textSafe}">${previewText}</td>
                    <td>${langText}</td>
                    <td>
                        <span class="badge ${label}">${label}</span>
                        <select class="edit-select hidden">
                            <option value="positive" ${label === 'positive' ? 'selected' : ''}>Позитивный</option>
                            <option value="neutral" ${label === 'neutral' ? 'selected' : ''}>Нейтральный</option>
                            <option value="negative" ${label === 'negative' ? 'selected' : ''}>Негативный</option>
                        </select>
                    </td>
                    <td>${confidenceText}</td>
                `;
                const badge = tr.querySelector('.badge');
                const select = tr.querySelector('.edit-select');
                badge.addEventListener('click', () => {
                    badge.classList.add('hidden');
                    select.classList.remove('hidden');
                    select.focus();
                });
                select.addEventListener('blur', () => {
                    setTimeout(() => {
                        select.classList.add('hidden');
                        badge.classList.remove('hidden');
                    }, 150);
                });
                select.addEventListener('change', async (e) => {
                    const newLabel = e.target.value;
                    if (newLabel === review.sentiment_label) {
                        select.classList.add('hidden');
                        badge.classList.remove('hidden');
                        return;
                    }
                    try {
                        const res = await fetch(`/api/reviews/${review.id}`, {
                            method: 'PATCH',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ sentiment_label: newLabel })
                        });
                        if (!res.ok) throw new Error();
                        review.sentiment_label = newLabel;
                        review.sentiment_manual = true;
                        review.sentiment_confidence = null;     
                        renderTable();
                    } catch (err) {
                        alert('Не удалось сохранить изменение');
                        select.value = review.sentiment_label;
                        select.classList.add('hidden');
                        badge.classList.remove('hidden');
                    }
                });
                resultsBody.appendChild(tr);
            });
        }
    }
    searchInput.addEventListener('input', renderTable);
    filterSentiment.addEventListener('change', renderTable);
    document.querySelectorAll('th[data-sort]').forEach(th => {
        th.addEventListener('click', () => {
            const column = th.getAttribute('data-sort');
            if (sortState.column === column) {
                sortState.asc = !sortState.asc; 
            } else {
                sortState.column = column;
                sortState.asc = true; 
            }
            renderTable();
        });
    });
    async function loadStats(sessionId) {
        try {
            const res = await fetch(`/api/stats/${sessionId}`);
            const data = await res.json();       
            renderPieChart(data.sentiment_counts);
            renderBarChart(data.word_frequencies.slice(0, 10));
            renderWordCloud(data.word_frequencies);
        } catch (e) {
            console.error('Ошибка загрузки статистики', e);
        }
    }
    function renderPieChart(counts) {
        const ctx = document.getElementById('pie-chart').getContext('2d');
        if (pieChartInstance) pieChartInstance.destroy();
        pieChartInstance = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Позитивные', 'Нейтральные', 'Негативные'],
                datasets: [{
                    data: [counts.positive, counts.neutral, counts.negative],
                    backgroundColor: ['#10b981', '#6b7280', '#ef4444'],
                    borderWidth: 0
                }]
            },
            options: { responsive: true, plugins: { legend: { position: 'bottom' } } }
        });
    }
    function renderBarChart(topWords) {
        const ctx = document.getElementById('bar-chart').getContext('2d');
        if (barChartInstance) barChartInstance.destroy();
        barChartInstance = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: topWords.map(w => w.word),
                datasets: [{
                    label: 'Частота',
                    data: topWords.map(w => w.count),
                    backgroundColor: '#3b82f6',
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                plugins: { legend: { display: false } },
                scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } }
            }
        });
    }
    function renderWordCloud(words) {
        const container = document.getElementById('wordcloud');
        container.innerHTML = ''; 
        const list = words.map(w => [w.word, w.count]);
        if (list.length === 0) {
            container.innerHTML = '<p style="text-align:center;padding-top:100px;color:#999;">Нет данных</p>';
            return;
        }
        const maxWeight = list[0][1];
        const normalizedList = list.map(item => [
            item[0], 
            Math.max(12, Math.round((item[1] / maxWeight) * 60)) 
        ]);
        WordCloud(container, {
            list: normalizedList,
            gridSize: 12,
            weightFactor: 1,
            fontFamily: 'sans-serif',
            color: function () {
                const colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#6b7280'];
                return colors[Math.floor(Math.random() * colors.length)];
            },
            rotateRatio: 0.3,
            backgroundColor: '#f9fafb'
        });
    }
    window.exportData = async function(format) {
        if (!currentSessionId) {
            alert("Сначала загрузите и проанализируйте файлы!");
            return;
        }
        let ext = format === 'excel' ? 'xlsx' : format;
        const url = `/api/export/${format}/${currentSessionId}`;
        const filename = `report_${currentSessionId.substring(0, 8)}.${ext}`;
        try {
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`Сервер вернул ошибку ${response.status}`);
            }
            const blob = await response.blob();
            const blobUrl = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = blobUrl;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            setTimeout(() => {
                document.body.removeChild(a);
                URL.revokeObjectURL(blobUrl);
            }, 1000);      
        } catch (e) {
            console.error('Ошибка скачивания:', e);
            alert(`Не удалось скачать файл: ${e.message}`);
        }
    };
    btnLoadJson.addEventListener('click', async () => {
        if (!jsonInput.files.length) {
            alert("Выберите JSON-файл для загрузки.");
            return;
        }
        btnLoadJson.disabled = true;
        uploadStatus.textContent = "Загрузка сессии...";
        uploadStatus.style.color = "black";
        const formData = new FormData();
        formData.append("file", jsonInput.files[0]);
        try {
            const res = await fetch('/api/session/load', {
                method: 'POST',
                body: formData
            });
            if (!res.ok) throw new Error("Ошибка сервера");      
            const data = await res.json();       
            progressSection.classList.add('hidden');
            uploadStatus.textContent = "Сессия успешно загружена!";
            uploadStatus.style.color = "green";           
            await loadResults(data.session_id);           
        } catch (err) {
            console.error(err);
            uploadStatus.textContent = `Ошибка: ${err.message}`;
            uploadStatus.style.color = "red";
        } finally {
            btnLoadJson.disabled = false;
            jsonInput.value = ''; 
        }
    });
});