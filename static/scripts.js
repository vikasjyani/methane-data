document.addEventListener('DOMContentLoaded', function () {
    // Initialize the map
    const map = L.map('map').setView([20.5937, 78.9629], 5); // Centered on India

    // Add a base map layer (OpenStreetMap)
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);

    // Date selection
    const yearSelect = document.getElementById('year-select');
    const monthSelect = document.getElementById('month-select');

    // Populate date dropdowns
    for (let year = 2023; year >= 2014; year--) {
        const option = document.createElement('option');
        option.value = year;
        option.textContent = year;
        yearSelect.appendChild(option);
    }
    for (let month = 1; month <= 12; month++) {
        const option = document.createElement('option');
        option.value = month;
        option.textContent = new Date(0, month - 1).toLocaleString('default', { month: 'long' });
        monthSelect.appendChild(option);
    }
    monthSelect.value = 12; // Default to December

    // Function to update the tile layer URL
    function getTileLayerUrl() {
        const year = yearSelect.value;
        const month = monthSelect.value;
        return `/tiles/{z}/{x}/{y}.png?year=${year}&month=${month}`;
    }

    // Add our custom methane tile layer
    let methaneLayer = L.tileLayer(getTileLayerUrl(), {
        attribution: 'Methane Data',
        opacity: 0.7
    }).addTo(map);

    // Function to update the map
    function updateMap() {
        methaneLayer.setUrl(getTileLayerUrl());
    }

    // Add event listeners for date changes
    yearSelect.addEventListener('change', updateMap);
    monthSelect.addEventListener('change', updateMap);


    // State and District selection
    const stateSelect = document.getElementById('state-select');
    const districtSelect = document.getElementById('district-select');
    const statsPanel = document.getElementById('stats-panel');
    let geoJsonLayer = null;

    // Fetch metadata to populate the state dropdown
    fetch('/api/metadata')
        .then(response => response.json())
        .then(data => {
            const states = data.states;
            states.forEach(state => {
                const option = document.createElement('option');
                option.value = state;
                option.textContent = state.charAt(0).toUpperCase() + state.slice(1).toLowerCase().replace(/_/g, ' ');
                stateSelect.appendChild(option);
            });
        });

    // Handle state selection
    stateSelect.addEventListener('change', function () {
        const selectedState = this.value;
        districtSelect.innerHTML = '<option value="">--Select a District--</option>'; // Reset districts

        if (geoJsonLayer) {
            map.removeLayer(geoJsonLayer);
        }

        if (selectedState) {
            // Fetch and display state boundary
            fetch(`/geojson/districts/${selectedState}`)
                .then(response => response.json())
                .then(geojsonData => {
                    geoJsonLayer = L.geoJSON(geojsonData, {
                        style: {
                            color: "#ff7800",
                            weight: 2,
                            opacity: 0.65
                        }
                    }).addTo(map);
                    map.fitBounds(geoJsonLayer.getBounds());
                });

            // Fetch and display stats
            fetch(`/api/stats/${selectedState}`)
                .then(response => response.json())
                .then(statsData => {
                    let statsHtml = `<h2>${selectedState}</h2>`;
                    statsHtml += `<p>Overall Average Methane: ${statsData.statistics.mean.toFixed(2)}</p>`;
                    statsPanel.innerHTML = statsHtml;

                    // Populate district dropdown
                    const districts = Object.keys(statsData.data);
                    districts.forEach(district => {
                        const option = document.createElement('option');
                        option.value = district;
                        option.textContent = district.charAt(0).toUpperCase() + district.slice(1).toLowerCase().replace(/_/g, ' ');
                        districtSelect.appendChild(option);
                    });
                });
        }
    });

    // Handle district selection
    districtSelect.addEventListener('change', function() {
        const selectedDistrict = this.value;
        const selectedState = stateSelect.value;

        if (geoJsonLayer) {
            map.removeLayer(geoJsonLayer);
        }

        if (selectedDistrict) {
             fetch(`/geojson/districts/${selectedState}`)
                .then(response => response.json())
                .then(geojsonData => {
                    const districtFeature = geojsonData.features.find(f => f.properties.DISTRICT.toUpperCase() === selectedDistrict.toUpperCase());
                    if (districtFeature) {
                        geoJsonLayer = L.geoJSON(districtFeature, {
                            style: {
                                color: "#0078ff",
                                weight: 3,
                                opacity: 0.8
                            }
                        }).addTo(map);
                        map.fitBounds(geoJsonLayer.getBounds());
                    }
                });

            // Display district stats
            fetch(`/api/stats/${selectedState}`)
                .then(response => response.json())
                .then(statsData => {
                    const districtStats = statsData.data[selectedDistrict];
                    let statsHtml = `<h2>${selectedDistrict}, ${selectedState}</h2>`;
                    statsHtml += `<p>Average Methane: ${districtStats.average_methane.toFixed(2)}</p>`;
                    statsHtml += `<p>Data Point Count: ${districtStats.point_count}</p>`;
                    statsPanel.innerHTML = statsHtml;
                });
        }
    });
});
