document.addEventListener('DOMContentLoaded', function () {

    const indiaBounds = [[6, 68], [38, 98]]; // approximate India bounding box
    const map = L.map('map', {
        center: [20.5937, 78.9629],
        zoom: 5,
        maxBounds: indiaBounds,
        maxBoundsViscosity: 1.0
    });

    const satellite = L.tileLayer(
        'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{x}/{y}',
        {
            attribution: 'Tiles \u00a9 Esri',
            noWrap: true,
            maxZoom: 13,
            minZoom: 4
        }
    ).addTo(map);


    let selectedYear = null;
    let selectedMonth = null;
    let availableYears = [];
    let availableMonths = [];

    let methaneLayer = null;

    function addMethaneLayer() {
        if (methaneLayer) {
            layerControl.removeLayer(methaneLayer);
            map.removeLayer(methaneLayer);
        }
        methaneLayer = L.tileLayer(`/tiles/${selectedYear}/${selectedMonth}/{z}/{x}/{y}.png`, {
            attribution: 'Methane Data',

            opacity: 0.7,
            noWrap: true

        });
        methaneLayer.addTo(map);
        layerControl.addOverlay(methaneLayer, 'Methane');
        updateLegend();
    }

    const layerControl = L.control.layers({ 'Satellite': satellite }, {}).addTo(map);

    let stateLayer = null;
    let districtLayer = null;
    let currentState = null;
    let stateStats = null;
    let selectedDistrict = null;
    let chart = null;

    const yearSelect = document.getElementById('year-select');
    const monthSelect = document.getElementById('month-select');
    const playButton = document.getElementById('play-button');
    const statsPanel = document.getElementById('stats-panel');
    let playInterval = null;

    function stopAnimation() {
        if (playInterval) {
            clearInterval(playInterval);
            playInterval = null;
            playButton.textContent = 'Play';
            playButton.classList.remove('stop');
        }
    }

    fetch('/api/metadata')
        .then(response => response.json())
        .then(meta => {
            availableYears = meta.years;
            availableMonths = meta.months;
            availableYears.forEach(y => {
                const option = document.createElement('option');
                option.value = y;
                option.textContent = y;
                yearSelect.appendChild(option);
            });
            selectedYear = availableYears[availableYears.length - 1];
            yearSelect.value = selectedYear;

            availableMonths.forEach(m => {
                const opt = document.createElement('option');
                opt.value = m;
                opt.textContent = m;
                monthSelect.appendChild(opt);
            });
            selectedMonth = availableMonths[0];
            monthSelect.value = selectedMonth;
            addMethaneLayer();
        });

    yearSelect.addEventListener('change', () => {
        stopAnimation();
        selectedYear = yearSelect.value;
        addMethaneLayer();
        if (selectedDistrict) {
            drawChart(selectedDistrict);
        }
    });

    monthSelect.addEventListener('change', () => {
        stopAnimation();
        selectedMonth = monthSelect.value;
        addMethaneLayer();
        if (selectedDistrict) {
            drawChart(selectedDistrict);
        }
    });

    function stepForward() {
        let yearIndex = availableYears.indexOf(parseInt(selectedYear));
        let monthIndex = availableMonths.indexOf(parseInt(selectedMonth));
        monthIndex++;
        if (monthIndex >= availableMonths.length) {
            monthIndex = 0;
            yearIndex++;
            if (yearIndex >= availableYears.length) {
                yearIndex = 0;
            }
            selectedYear = availableYears[yearIndex];
            yearSelect.value = selectedYear;
        }
        selectedMonth = availableMonths[monthIndex];
        monthSelect.value = selectedMonth;
        addMethaneLayer();
        if (selectedDistrict) {
            drawChart(selectedDistrict);
        }
    }

    playButton.addEventListener('click', () => {
        if (playInterval) {
            stopAnimation();
        } else {
            playButton.textContent = 'Stop';
            playButton.classList.add('stop');
            playInterval = setInterval(stepForward, 1000);
        }
    });

    function drawChart(districtKey) {
        if (!stateStats || !stateStats.monthly_data) return;
        const year = yearSelect.value;
        const labels = [];
        const values = [];
        for (let m = 1; m <= 12; m++) {
            const key = `${year}_${String(m).padStart(2, '0')}`;
            const monthData = stateStats.monthly_data[key];
            const distData = monthData ? monthData[districtKey] : null;
            labels.push(m);
            values.push(distData ? distData.average : null);
        }
        if (chart) {
            chart.destroy();
        }
        const ctx = document.getElementById('line-chart').getContext('2d');
        chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: `Average Methane (${districtKey.replace(/_/g, ' ')})`,
                    data: values,
                    borderColor: 'blue',
                    fill: false
                }]
            },
            options: {
                scales: {
                    x: { title: { display: true, text: 'Month' } },
                    y: { title: { display: true, text: 'Methane (ppb)' } }
                }
            }
        });
    }

    function loadStates() {
        fetch('/geojson/states')
            .then(res => res.json())
            .then(data => {
                stateLayer = L.geoJSON(data, {
                    style: { color: '#ff7800', weight: 1, fillOpacity: 0 },
                    onEachFeature: (feature, layer) => {
                        layer.on('click', () => {
                            currentState = feature.properties.STATE;
                            map.fitBounds(layer.getBounds());
                            fetchStateStats(currentState);
                            loadDistricts(currentState);
                        });
                    }
                }).addTo(map);
            });
    }

    function loadDistricts(state) {
        if (districtLayer) {
            map.removeLayer(districtLayer);
        }
        fetch(`/geojson/districts/${state}`)
            .then(res => res.json())
            .then(data => {
                districtLayer = L.geoJSON(data, {
                    style: { color: '#0078ff', weight: 1, fillOpacity: 0 },
                    onEachFeature: (feature, layer) => {
                        layer.on('click', () => {
                            const districtName = feature.properties.District_1;
                            const districtKey = districtName.toUpperCase().replace(/\s+/g, '_');
                            selectedDistrict = districtKey;
                            map.fitBounds(layer.getBounds());
                            showDistrictStats(districtName, districtKey);
                        });
                    }
                }).addTo(map);
            });
    }

    function fetchStateStats(state) {
        fetch(`/api/stats/${state}`)
            .then(res => res.json())
            .then(data => {
                stateStats = data;
                statsPanel.innerHTML = `<h2>${state}</h2><p>Select a district to view details.</p><canvas id="line-chart"></canvas>`;
            });
    }

    function showDistrictStats(districtName, districtKey) {
        const districtStats = stateStats.data[districtKey];
        statsPanel.innerHTML = `<h2>${districtName}, ${currentState}</h2>
            <p>Average Methane: ${districtStats.average_methane.toFixed(2)}</p>
            <p>Data Point Count: ${districtStats.point_count}</p>
            <canvas id="line-chart"></canvas>`;
        drawChart(districtKey);
    }

    const legend = L.control({ position: 'bottomright' });
    legend.onAdd = function () {
        const div = L.DomUtil.create('div', 'legend');
        div.innerHTML = '<span id="legend-min"></span><div class="gradient"></div><span id="legend-max"></span>';
        return div;
    };
    legend.addTo(map);

    function updateLegend() {
        fetch(`/api/color_range/${selectedYear}/${selectedMonth}`)
            .then(res => res.json())
            .then(range => {

                const minEl = document.getElementById('legend-min');
                const maxEl = document.getElementById('legend-max');
                if (range.min == null || range.max == null) {
                    minEl.textContent = 'N/A';
                    maxEl.textContent = 'N/A';
                } else {
                    minEl.textContent = range.min.toFixed(2);
                    maxEl.textContent = range.max.toFixed(2);
                }


            });
    }

    loadStates();
});
