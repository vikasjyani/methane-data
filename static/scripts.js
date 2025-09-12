document.addEventListener('DOMContentLoaded', () => {
    const map = L.map('map').setView([22.9734, 78.6569], 5); // India center
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);

    fetch('/metadata/available').then(r => r.json()).then(meta => {
        if (meta.years.length && meta.months.length) {
            const year = meta.years[0];
            const month = meta.months[0];
            const tileUrl = `/tiles/${year}/${month}/{z}/{x}/{y}.png`;
            const methaneLayer = L.tileLayer(tileUrl, { tms: true, opacity: 0.7 });
            methaneLayer.addTo(map);
        }
    });

    fetch('/geojson/districts')
        .then(r => r.json())
        .then(geojson => {
            L.geoJSON(geojson, {
                style: { color: '#555', weight: 1, fill: false }
            }).addTo(map);
        });
});
