import { useState, useEffect } from 'react';
import { usePollenData } from './hooks/usePollenData';
import Header from './components/Header';
import CampusMap from './components/CampusMap';
import AdvisoryBanner from './components/AdvisoryBanner';
import SidePanel from './components/SidePanel';
import TreeInfoCard from './components/TreeInfoCard';
import { fetchCampuses } from './utils/api';
import type { FloraItem, Campus, TestParams } from './utils/api';

export default function App() {
  const [campuses, setCampuses] = useState<Campus[]>([]);
  const [campusKey, setCampusKey] = useState<string>('gunn');
  const [receptorHeight, setReceptorHeight] = useState<number>(1.5);
  const [testEnabled, setTestEnabled] = useState<boolean>(false);
  const [testParams, setTestParams] = useState<TestParams>({
    day: 105, wind_speed: 3.5, wind_dir: 240, stability: 'D',
  });
  const data = usePollenData(campusKey, receptorHeight, testEnabled ? testParams : undefined);
  const [selectedTree, setSelectedTree] = useState<FloraItem | null>(null);
  const [showPanel, setShowPanel] = useState(true);

  useEffect(() => {
    fetchCampuses()
      .then((res) => {
        setCampuses(res.campuses);
        if (res.default) setCampusKey(res.default);
      })
      .catch(() => {});
  }, []);

  const activeCampus = campuses.find((c) => c.key === campusKey) || null;

  // Reset any selected tree when switching campuses
  useEffect(() => {
    setSelectedTree(null);
  }, [campusKey]);

  if (data.loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-slate-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-600 mx-auto mb-4"></div>
          <p className="text-slate-600 text-lg">Loading Campus AeroAllergen Map...</p>
          <p className="text-slate-400 text-sm mt-2">Computing pollen dispersion field</p>
        </div>
      </div>
    );
  }

  if (data.error) {
    return (
      <div className="flex items-center justify-center h-screen bg-slate-50">
        <div className="bg-white rounded-xl shadow-lg p-8 max-w-md text-center">
          <div className="text-4xl mb-4">⚠</div>
          <h2 className="text-xl font-bold text-slate-800 mb-2">Connection Error</h2>
          <p className="text-slate-600 mb-4">{data.error}</p>
          <button
            onClick={data.refreshData}
            className="bg-emerald-600 text-white px-6 py-2 rounded-lg hover:bg-emerald-700 transition"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col overflow-hidden">
      <Header
        weather={data.weather}
        activeSpecies={data.activeSpecies}
        campuses={campuses}
        campusKey={campusKey}
        onCampusChange={setCampusKey}
        receptorHeight={receptorHeight}
        onHeightChange={setReceptorHeight}
      />

      {data.advisory?.advisory_message && (
        <AdvisoryBanner advisory={data.advisory} />
      )}

      <div className="flex-1 flex overflow-hidden" style={{ height: 'calc(100vh - 60px)' }}>
        <div className="flex-1 relative h-full">
          <CampusMap
            key={campusKey}
            heatmap={data.heatmap}
            flora={data.flora}
            buildings={data.buildings}
            campus={activeCampus}
            onTreeSelect={setSelectedTree}
            testEnabled={testEnabled}
            testParams={testParams}
            onTestToggle={setTestEnabled}
            onTestChange={setTestParams}
          />

          {selectedTree && (
            <div className="absolute top-4 right-4 z-50">
              <TreeInfoCard
                tree={selectedTree}
                activeSpecies={data.activeSpecies}
                weather={data.weather}
                onClose={() => setSelectedTree(null)}
              />
            </div>
          )}
        </div>

        {showPanel && (
          <SidePanel
            forecast={data.forecast}
            advisory={data.advisory}
            activeSpecies={data.activeSpecies}
            weather={data.weather}
          />
        )}
      </div>

      <button
        onClick={() => setShowPanel(!showPanel)}
        className="fixed bottom-4 right-4 z-50 bg-white rounded-full p-3 shadow-lg hover:shadow-xl transition border border-slate-200"
        title={showPanel ? 'Hide panel' : 'Show panel'}
      >
        {showPanel ? '→' : '←'}
      </button>
    </div>
  );
}
