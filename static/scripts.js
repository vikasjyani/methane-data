document.addEventListener('DOMContentLoaded', function () {
    // --- Map Initialization ---
    const map = L.map('map').setView([20.5937, 78.9629], 5);

    // --- Base Layers ---
    const satelliteLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        attribution: 'Tiles &copy; Esri'
    });
    const streetLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);

    // --- Overlay Layers ---
    const labelsLayer = L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager_labels_under/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://carto.com/attributions">CARTO</a>',
        pane: 'shadowPane' // Ensures labels are on top of other layers
    });

    let methaneLayer = L.tileLayer(getTileLayerUrl(), {
        attribution: 'Methane Data',
        opacity: 0.7
    }).addTo(map);

    const baseMaps = {
        "Street": streetLayer,
        "Satellite": satelliteLayer
    };
    const overlayMaps = {
        "Methane Emissions": methaneLayer,
        "Labels": labelsLayer
    };
    L.control.layers(baseMaps, overlayMaps).addTo(map);

    // --- UI Element References ---
    const yearSelect = document.getElementById('year-select');
    const monthSelect = document.getElementById('month-select');
    const stateSelect = document.getElementById('state-select');
    const districtSelect = document.getElementById('district-select');
    const statsPanel = document.getElementById('stats-panel');
    let geoJsonLayer = null;
    let legend = L.control({position: 'bottomright'});

    // --- Legend Logic ---
    legend.onAdd = function (map) {
        this._div = L.DomUtil.create('div', 'info legend');
        this.update();
        return this._div;
    };
    legend.update = function (props) {
        let content = '<h4>Methane Concentration</h4>';
        if (props && props.min !== null) {
            content += `<b>Min:</b> ${props.min.toFixed(2)}<br><b>Max:</b> ${props.max.toFixed(2)}`;
            content += '<div class="gradient-bar"></div>';
            content += '<span class="min-label">Low</span><span class="max-label">High</span>';
        } else {
            content += 'Select a state to see the scale.';
        }
        this._div.innerHTML = content;
    };
    legend.addTo(map);

    // --- Date and Geo Selection Logic ---
    function getTileLayerUrl() {
        const year = yearSelect.value;
        const month = monthSelect.value;
        const state = stateSelect.value;
        const district = districtSelect.value;

        let url = `/tiles/{z}/{x}/{y}.png?year=${year}&month=${month}`;
        if (state) url += `&state=${state}`;
        if (district) url += `&district=${district}`;

        return url;
    }

    function updateMap() {
        const state = stateSelect.value;
        const year = yearSelect.value;
        const month = monthSelect.value;

        // Show a loading indicator
        document.body.classList.add('loading');

        if (state) {
            fetch(`/api/prepare_state_data?state=${state}&year=${year}&month=${month}`)
                .then(response => response.json())
                .then(data => {
                    legend.update(data);
                    methaneLayer.setUrl(getTileLayerUrl(), false);
                    methaneLayer.redraw();
                    document.body.classList.remove('loading');
                });
        } else {
            legend.update();
            methaneLayer.setUrl(getTileLayerUrl(), false);
            methaneLayer.redraw();
            document.body.classList.remove('loading');
        }
    }

    // --- Event Listeners ---
    yearSelect.addEventListener('change', updateMap);
    monthSelect.addEventListener('change', updateMap);
    stateSelect.addEventListener('change', function() {
        handleStateSelection();
        // updateMap is called by handleStateSelection
    });
    districtSelect.addEventListener('change', function() {
        handleDistrictSelection();
        methaneLayer.setUrl(getTileLayerUrl(), false);
        methaneLayer.redraw();
    });

    // --- Initial Population ---
    for (let year = 2023; year >= 2014; year--) {
        yearSelect.appendChild(new Option(year, year));
    }
    for (let month = 1; month <= 12; month++) {
        const monthName = new Date(0, month - 1).toLocaleString('default', { month: 'long' });
        monthSelect.appendChild(new Option(monthName, month));
    }
    monthSelect.value = 12;

    fetch('/api/metadata')
        .then(response => response.json())
        .then(data => {
            data.states.forEach(state => {
                const optionText = state.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                stateSelect.appendChild(new Option(optionText, state));
            });
        });

    // --- Handler Functions ---
    function handleStateSelection() {
        const selectedState = stateSelect.value;
        districtSelect.innerHTML = '<option value="">-- Select a District --</option>';
        if (geoJsonLayer) map.removeLayer(geoJsonLayer);

        if (selectedState) {
            fetch(`/geojson/districts/${selectedState}`)
                .then(response => response.json())
                .then(geojsonData => {
                    geoJsonLayer = L.geoJSON(geojsonData, {
                        style: { color: "#ff7800", weight: 2, opacity: 0.65, fillOpacity: 0.1 }
                    }).addTo(map);
                    map.fitBounds(geoJsonLayer.getBounds());
                });
            fetch(`/api/stats/${selectedState}`)
                .then(response => response.json())
                .then(statsData => {
                    statsPanel.innerHTML = `<h2>${selectedState.replace(/_/g, ' ')}</h2><p>Overall Average Methane: ${statsData.statistics.mean.toFixed(2)}</p>`;
                    Object.keys(statsData.data).forEach(district => {
                        const optionText = district.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                        districtSelect.appendChild(new Option(optionText, district));
                    });
                });
        }
        updateMap();
    }

    function handleDistrictSelection() {
        const selectedDistrict = districtSelect.value;
        const selectedState = stateSelect.value;
        if (geoJsonLayer) map.removeLayer(geoJsonLayer);

        if (selectedDistrict) {
            fetch(`/geojson/districts/${selectedState}`)
                .then(response => response.json())
                .then(geojsonData => {
                    const districtFeature = geojsonData.features.find(f => f.properties.DISTRICT.toUpperCase() === selectedDistrict.toUpperCase());
                    if (districtFeature) {
                        geoJsonLayer = L.geoJSON(districtFeature, {
                            style: { color: "#0078ff", weight: 3, opacity: 0.8, fillOpacity: 0.2 }
                        }).addTo(map);
                        map.fitBounds(geoJsonLayer.getBounds());
                    }
                });
            fetch(`/api/stats/${selectedState}`)
                .then(response => response.json())
                .then(statsData => {
                    const districtStats = statsData.data[selectedDistrict];
                    statsPanel.innerHTML = `<h2>${selectedDistrict.replace(/_/g, ' ')}, ${selectedState.replace(/_/g, ' ')}</h2><p>Average Methane: ${districtStats.average_methane.toFixed(2)}</p><p>Data Point Count: ${districtStats.point_count}</p>`;
                });
        } else {
            // If district is de-selected, re-select the state
            handleStateSelection();
        }
    }
});
