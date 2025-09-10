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
        pane: 'shadowPane'
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

    // --- UI Element References & State ---
    const yearSelect = document.getElementById('year-select');
    const monthSelect = document.getElementById('month-select');
    const stateSelect = document.getElementById('state-select');
    const districtSelect = document.getElementById('district-select');
    const statsPanel = document.getElementById('stats-panel');
    let statesGeoJsonLayer = null;
    let districtsGeoJsonLayer = null;
    let legend = L.control({position: 'bottomright'});

    // --- Legend Logic ---
    legend.onAdd = function (map) {
        this._div = L.DomUtil.create('div', 'info legend');
        this.update();
        return this._div;
    };
    legend.update = function (props) {
        let content = '<h4>Methane Concentration</h4>';
        const scope = stateSelect.value ? stateSelect.options[stateSelect.selectedIndex].text : 'All India';
        content += `<strong>Scope:</strong> ${scope}<br>`;
        if (props && props.min !== null) {
            content += `<b>Min:</b> ${props.min.toFixed(2)}<br><b>Max:</b> ${props.max.toFixed(2)}`;
            content += '<div class="gradient-bar"></div>';
            content += '<span class="min-label">Low</span><span class="max-label">High</span>';
        } else {
            content += 'No data for this period.';
        }
        this._div.innerHTML = content;
    };
    legend.addTo(map);

    // --- Core Logic ---
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

        document.body.classList.add('loading');

        fetch(`/api/prepare_data?state=${state || ''}&year=${year}&month=${month}`)
            .then(response => response.json())
            .then(data => {
                legend.update(data);
                methaneLayer.setUrl(getTileLayerUrl(), false);
                methaneLayer.redraw();
                document.body.classList.remove('loading');
            });
    }

    // --- Event Listeners ---
    yearSelect.addEventListener('change', updateMap);
    monthSelect.addEventListener('change', updateMap);
    stateSelect.addEventListener('change', handleStateSelection);
    districtSelect.addEventListener('change', handleDistrictSelection);

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

    // --- Click-to-Select States ---
    fetch('/geojson/states')
        .then(res => res.json())
        .then(geojsonData => {
            statesGeoJsonLayer = L.geoJSON(geojsonData, {
                style: {
                    color: "#3388ff",
                    weight: 1,
                    opacity: 0.5,
                    fillOpacity: 0.1
                },
                onEachFeature: function(feature, layer) {
                    layer.on({
                        mouseover: e => e.target.setStyle({ weight: 3, color: '#ff7800' }),
                        mouseout: e => statesGeoJsonLayer.resetStyle(e.target),
                        click: e => {
                            const stateName = e.target.feature.properties.ST_NM;
                            stateSelect.value = stateName;
                            stateSelect.dispatchEvent(new Event('change'));
                        }
                    });
                }
            }).addTo(map);
        });

    // --- Handler Functions ---
    function handleStateSelection() {
        const selectedState = stateSelect.value;
        districtSelect.innerHTML = '<option value="">-- Select a District --</option>';
        if (districtsGeoJsonLayer) map.removeLayer(districtsGeoJsonLayer);
        if (statesGeoJsonLayer) map.removeLayer(statesGeoJsonLayer);

        if (selectedState) {
            fetch(`/geojson/districts/${selectedState}`)
                .then(response => response.json())
                .then(geojsonData => {
                    districtsGeoJsonLayer = L.geoJSON(geojsonData, {
                        style: { color: "#ff7800", weight: 2, opacity: 0.65, fillOpacity: 0.1 },
                        onEachFeature: function(feature, layer) {
                            layer.on({
                                mouseover: e => e.target.setStyle({ weight: 3, color: '#0078ff' }),
                                mouseout: e => districtsGeoJsonLayer.resetStyle(e.target),
                                click: e => {
                                    const districtName = e.target.feature.properties.DISTRICT;
                                    districtSelect.value = districtName;
                                    districtSelect.dispatchEvent(new Event('change'));
                                }
                            });
                        }
                    }).addTo(map);
                    map.fitBounds(districtsGeoJsonLayer.getBounds());
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
        } else {
            if (statesGeoJsonLayer) statesGeoJsonLayer.addTo(map);
            map.setView([20.5937, 78.9629], 5);
        }
        updateMap();
    }

    function handleDistrictSelection() {
        const selectedDistrict = districtSelect.value;
        const selectedState = stateSelect.value;

        // Don't remove the main districts layer, just highlight the selected one
        if (districtsGeoJsonLayer) {
            districtsGeoJsonLayer.eachLayer(layer => {
                if (layer.feature.properties.DISTRICT.toUpperCase() === selectedDistrict.toUpperCase()) {
                    map.fitBounds(layer.getBounds());
                    layer.setStyle({ color: "#0078ff", weight: 4, opacity: 1, fillOpacity: 0.2 });
                } else {
                    districtsGeoJsonLayer.resetStyle(layer);
                }
            });
        }

        if (selectedDistrict) {
            fetch(`/api/stats/${selectedState}`)
                .then(response => response.json())
                .then(statsData => {
                    const districtStats = statsData.data[selectedDistrict];
                    statsPanel.innerHTML = `<h2>${selectedDistrict.replace(/_/g, ' ')}, ${selectedState.replace(/_/g, ' ')}</h2><p>Average Methane: ${districtStats.average_methane.toFixed(2)}</p><p>Data Point Count: ${districtStats.point_count}</p>`;
                });
        } else {
            // If district is de-selected, reset view to the state level
            if(districtsGeoJsonLayer) map.fitBounds(districtsGeoJsonLayer.getBounds());
        }
    }
});
