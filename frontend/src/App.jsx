import { useState, useEffect } from 'react'
import { collection, query, orderBy, onSnapshot } from 'firebase/firestore'
import { db } from './firebase'

function App() {
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(false)
  const [processing, setProcessing] = useState(false)
  const [scanning, setScanning] = useState(false)
  const [scanningAts, setScanningAts] = useState(false)
  const [scanProgress, setScanProgress] = useState('')
  const [selectedJob, setSelectedJob] = useState(null)
  const [showAllJobs, setShowAllJobs] = useState(true)
  const [filters, setFilters] = useState({
    title: '',
    company: '',
    notes: ''
  })
  const [activeFilterColumn, setActiveFilterColumn] = useState(null)

  useEffect(() => {
    setLoading(true);
    const q = query(collection(db, 'jobs'), orderBy('timestamp', 'desc'));
    const unsubscribe = onSnapshot(q, (snapshot) => {
      const jobsData = [];
      snapshot.forEach((doc) => {
        jobsData.push({ id: doc.id, ...doc.data() });
      });
      setJobs(jobsData);
      setLoading(false);
    }, (error) => {
      console.error("Error fetching jobs from Firestore:", error);
      setLoading(false);
    });

    return () => unsubscribe();
  }, []);

  const handleProcessMock = async () => {
    setProcessing(true)
    try {
      await fetch('http://localhost:8000/api/jobs/process-mock', {
        method: 'POST'
      })
    } catch (err) {
      console.error(err)
    } finally {
      setProcessing(false)
    }
  }

  const handleScanAts = async (limit = null) => {
    setScanningAts(true)
    setScanProgress('Starting scan...')
    try {
      const url = limit ? `http://localhost:8000/api/jobs/scan-ats?limit=${limit}` : 'http://localhost:8000/api/jobs/scan-ats';
      const res = await fetch(url, {
        method: 'POST'
      })
      if (!res.ok) {
        const errData = await res.json()
        alert(`Error scanning ATS: ${errData.detail || errData.message || 'Unknown error'}`)
        setScanningAts(false)
        setScanProgress('')
        return
      }
      
      const reader = res.body.getReader()
      const decoder = new TextDecoder('utf-8')
      let done = false
      
      while (!done) {
        const { value, done: readerDone } = await reader.read()
        done = readerDone
        if (value) {
          const chunk = decoder.decode(value, { stream: true })
          const lines = chunk.split('\n')
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6))
                if (data.status) {
                  setScanProgress(data.status)
                }
                if (data.type === 'complete') {
                  alert(data.status)
                } else if (data.type === 'error') {
                  console.error("Error from stream:", data.status)
                }
              } catch (e) {
                console.error("Error parsing stream line:", line, e)
              }
            }
          }
        }
      }
      // Explicitly wait for the backend to finalize DB commits and close the stream
      // The real-time listener will automatically update the UI when the backend pushes to Firestore
      setTimeout(async () => {
        console.log("Scan completed.");
      }, 500)
    } catch (err) {
      console.error(err)
      alert(`Error scanning ATS: ${err.message}`)
    } finally {
      setScanningAts(false)
      setScanProgress('')
    }
  }

  const handleScanLive = async () => {
    setScanning(true)
    try {
      await fetch('http://localhost:8000/api/jobs/scan-real', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          search_term: "Junior ML Engineer",
          location: "Israel",
          results_wanted: 10
        })
      })
      // Real-time listener will handle updates
    } catch (err) {
      console.error(err)
    } finally {
      setScanning(false)
    }
  }

  const handleUpdateJob = async (id, updates) => {
    setJobs(jobs.map(job => job.id === id ? { ...job, ...updates } : job))
    try {
      await fetch(`http://localhost:8000/api/jobs/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates)
      })
    } catch (err) {
      console.error(err)
    }
  }

  const filteredJobs = jobs.filter(job => {
    if (!showAllJobs && (job.match_score === undefined || job.match_score < 70)) return false;

    const matchTitle = !filters.title || (job.job_title && job.job_title.toLowerCase().includes(filters.title.toLowerCase()))
    const matchCompany = !filters.company || (job.company_name && job.company_name.toLowerCase().includes(filters.company.toLowerCase()))
    const matchNotes = !filters.notes || (job.match_reason && job.match_reason.toLowerCase().includes(filters.notes.toLowerCase()))
    
    return matchTitle && matchCompany && matchNotes
  })

  const handleFilterChange = (column, value) => {
    setFilters(prev => ({ ...prev, [column]: value }))
  }

  const FilterPopover = ({ column, label, type, options = [], alignRight = false }) => {
    if (activeFilterColumn !== column) return null;

    return (
      <div className={`absolute top-full ${alignRight ? 'right-0' : 'left-0'} mt-2 w-48 bg-gray-800 border border-gray-600 rounded-xl shadow-2xl z-30 p-3 text-left font-normal normal-case`} onClick={e => e.stopPropagation()}>
        <div className="flex justify-between items-center mb-2">
          <span className="text-xs font-semibold text-gray-300">Filter {label}</span>
          <button 
            onClick={(e) => {
              e.stopPropagation();
              handleFilterChange(column, type === 'select' ? 'All' : '');
            }} 
            className="text-gray-500 hover:text-gray-300 text-xs"
          >
            Clear
          </button>
        </div>
        {type === 'select' ? (
          <select 
            value={filters[column]} 
            onChange={(e) => handleFilterChange(column, e.target.value)}
            className="w-full bg-gray-700 text-white rounded px-2 py-1.5 text-sm border border-gray-600 focus:outline-none focus:border-blue-500"
          >
            {options.map(opt => <option key={opt} value={opt}>{opt}</option>)}
          </select>
        ) : (
          <input 
            type="text" 
            placeholder={`Search ${label}...`}
            value={filters[column]}
            onChange={(e) => handleFilterChange(column, e.target.value)}
            className="w-full bg-gray-700 text-white rounded px-2 py-1.5 text-sm border border-gray-600 focus:outline-none focus:border-blue-500"
            autoFocus
          />
        )}
      </div>
    );
  };

  const toggleFilter = (column, e) => {
    e.stopPropagation();
    setActiveFilterColumn(prev => prev === column ? null : column);
  };

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100 p-8 font-sans" onClick={() => setActiveFilterColumn(null)}>
      <div className="max-w-6xl mx-auto">
        <header className="flex justify-between items-center mb-8 pb-4 border-b border-gray-800">
          <div>
            <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-emerald-400">
              Job Search OS
            </h1>
            <p className="text-gray-400 mt-1">Live Pipeline Dashboard</p>
          </div>
          <div className="flex gap-4">
            <div className="flex bg-gray-800 p-1 rounded-lg items-center border border-gray-700 mr-4">
              <button 
                onClick={() => setShowAllJobs(true)}
                className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${showAllJobs ? 'bg-blue-600 text-white shadow' : 'text-gray-400 hover:text-gray-200'}`}
              >
                Show All Jobs
              </button>
              <button 
                onClick={() => setShowAllJobs(false)}
                className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${!showAllJobs ? 'bg-blue-600 text-white shadow' : 'text-gray-400 hover:text-gray-200'}`}
              >
                Relevant Only (Score 70+)
              </button>
            </div>
            <button 
              onClick={handleProcessMock} 
              disabled={processing || scanning || scanningAts}
              className="bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:text-gray-500 text-white font-semibold py-2 px-6 rounded-lg shadow-lg transition-all duration-200 ease-in-out"
            >
              {processing ? 'Processing...' : 'Process Mock Data'}
            </button>
            <button 
              onClick={handleScanLive} 
              disabled={scanning || processing || scanningAts}
              className="bg-blue-600 hover:bg-blue-500 disabled:bg-blue-900 disabled:text-gray-400 text-white font-semibold py-2 px-6 rounded-lg shadow-lg transition-all duration-200 ease-in-out transform hover:-translate-y-0.5 flex items-center"
            >
              {scanning ? (
                <>
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Scraping...
                </>
              ) : (
                'Scan Live Jobs'
              )}
            </button>
            <button 
              onClick={() => handleScanAts(5)} 
              disabled={scanningAts || scanning || processing}
              className="bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-900 disabled:text-gray-400 text-white font-semibold py-2 px-6 rounded-lg shadow-lg transition-all duration-200 ease-in-out transform hover:-translate-y-0.5 flex items-center"
            >
              Test Scan (5 Jobs)
            </button>
            <button 
              onClick={() => handleScanAts()} 
              disabled={scanningAts || scanning || processing}
              className="bg-purple-600 hover:bg-purple-500 disabled:bg-purple-900 disabled:text-gray-400 text-white font-semibold py-2 px-6 rounded-lg shadow-lg transition-all duration-200 ease-in-out transform hover:-translate-y-0.5 flex items-center"
            >
              {scanningAts ? (
                <>
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  <span className="flex flex-col text-left leading-tight">
                    <span>Scanning ATS...</span>
                    {scanProgress && <span className="text-[10px] text-purple-200 truncate max-w-[150px]">{scanProgress}</span>}
                  </span>
                </>
              ) : (
                'Scan ATS (Boolean)'
              )}
            </button>
          </div>
        </header>

        {jobs.length > 0 && (
          <div className="mb-4 text-gray-300 text-lg font-medium">
            Total Jobs in DB: <span className="text-white font-bold">{jobs.length}</span>
          </div>
        )}

        {loading && jobs.length === 0 ? (
          <div className="text-center py-20 text-gray-500">Loading jobs...</div>
        ) : jobs.length === 0 ? (
          <div className="text-center py-20 text-gray-500 bg-gray-800/50 rounded-xl border border-gray-700/50">
            No jobs found. Click 'Process Mock Data' to begin.
          </div>
        ) : (
          <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl overflow-hidden shadow-2xl">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-gray-800/80 border-b border-gray-700 text-gray-400 text-sm uppercase tracking-wider">
                    <th className="p-4 font-semibold relative cursor-pointer hover:bg-gray-700/50 select-none group" onClick={(e) => toggleFilter('title', e)}>
                      <div className="flex items-center space-x-1">
                        <span>Job Title</span>
                        <span className={`text-[10px] ${filters.title ? 'text-blue-400' : 'text-gray-600 group-hover:text-gray-400'}`}>▼</span>
                      </div>
                      <FilterPopover column="title" label="Job Title" type="text" />
                    </th>
                    <th className="p-4 font-semibold relative cursor-pointer hover:bg-gray-700/50 select-none group" onClick={(e) => toggleFilter('company', e)}>
                      <div className="flex items-center space-x-1">
                        <span>Company</span>
                        <span className={`text-[10px] ${filters.company ? 'text-blue-400' : 'text-gray-600 group-hover:text-gray-400'}`}>▼</span>
                      </div>
                      <FilterPopover column="company" label="Company" type="text" />
                    </th>
                    <th className="p-4 font-semibold">Scanned At</th>
                    <th className="p-4 font-semibold text-center">Fit Score</th>
                    <th className="p-4 font-semibold relative cursor-pointer hover:bg-gray-700/50 select-none group" onClick={(e) => toggleFilter('notes', e)}>
                      <div className="flex items-center space-x-1">
                        <span>Notes/Reason</span>
                        <span className={`text-[10px] ${filters.notes ? 'text-blue-400' : 'text-gray-600 group-hover:text-gray-400'}`}>▼</span>
                      </div>
                      <FilterPopover column="notes" label="Notes" type="text" alignRight={true} />
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-700/50">
                  {filteredJobs.map((job) => (
                    <tr key={job.id} className="hover:bg-gray-700/30 transition-colors">
                      <td className="p-4">
                        <div className="flex flex-col space-y-1">
                          <div className="font-medium text-gray-200 flex flex-wrap items-center gap-2">
                            <span className="text-base">{job.job_title || 'Unknown Title'}</span>
                            {job.job_url && (
                              <a href={job.job_url} target="_blank" rel="noopener noreferrer" className="text-gray-500 hover:text-blue-400 p-1" title="Open external link">
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>
                              </a>
                            )}
                          </div>
                          <div className="text-xs text-gray-500 flex justify-between items-center mt-1.5">
                            <button 
                              onClick={() => setSelectedJob(job)}
                              className="text-blue-400 hover:text-blue-300 font-medium px-2.5 py-1 rounded bg-blue-500/10 hover:bg-blue-500/20 transition-colors border border-blue-500/20 flex items-center gap-1"
                            >
                              Details
                            </button>
                          </div>
                        </div>
                      </td>
                      <td className="p-4 text-gray-300">{job.company_name || 'Unknown Company'}</td>
                      <td className="p-4 text-gray-400 text-sm whitespace-nowrap">
                        {job.timestamp ? (() => {
                          const dateObj = job.timestamp.toDate ? job.timestamp.toDate() : new Date(job.timestamp);
                          const pad = (n) => n.toString().padStart(2, '0');
                          return `${pad(dateObj.getDate())}/${pad(dateObj.getMonth()+1)}/${dateObj.getFullYear()} ${pad(dateObj.getHours())}:${pad(dateObj.getMinutes())}`;
                        })() : 'N/A'}
                      </td>
                      <td className="p-4 text-center">
                        {job.match_score !== undefined ? (
                          <span className={`inline-flex items-center justify-center w-10 h-10 rounded-full font-bold ${
                            job.match_score >= 80 ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' :
                            job.match_score >= 50 ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' :
                            'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                          }`}>
                            {job.match_score}
                          </span>
                        ) : (
                          <span className="text-gray-600">-</span>
                        )}
                      </td>
                      <td className="p-4 text-gray-300 text-sm max-w-xs truncate" title={job.match_reason}>
                        {job.match_reason || '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* Modal */}
      {selectedJob && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm" onClick={() => setSelectedJob(null)}>
          <div className="bg-gray-800 border border-gray-700 rounded-2xl w-full max-w-3xl max-h-[90vh] overflow-y-auto shadow-2xl" onClick={e => e.stopPropagation()}>
            <div className="p-6 border-b border-gray-700 flex justify-between items-start">
              <div>
                <h2 className="text-2xl font-bold text-gray-100 flex items-center space-x-3">
                  <span>{selectedJob.title}</span>
                  {selectedJob.is_updated && (
                    <span className="bg-blue-500/20 text-blue-400 text-xs font-bold px-2 py-1 rounded-full border border-blue-500/30">
                      UPDATED
                    </span>
                  )}
                </h2>
                <div className="text-gray-400 mt-1">{selectedJob.company} • {selectedJob.location}</div>
              </div>
              <button onClick={() => setSelectedJob(null)} className="text-gray-400 hover:text-white">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
              </button>
            </div>
            <div className="p-6 space-y-8">
              {/* Sniper Evaluation */}
              {selectedJob.match_score !== undefined && (
                <div className="bg-gray-900/60 p-6 rounded-2xl border border-gray-700/60 shadow-inner">
                  <div className="flex items-center gap-2 mb-4 border-b border-gray-700/60 pb-3">
                    <svg className="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
                    <h3 className="text-lg font-bold text-gray-100">Sniper Evaluation</h3>
                  </div>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                    <div className="bg-gray-800/80 p-4 rounded-xl border border-gray-700">
                      <div className="text-xs text-gray-400 mb-1 uppercase tracking-wider font-semibold">Fit Score</div>
                      <div className="text-xl font-bold text-blue-400">{selectedJob.match_score}<span className="text-sm text-gray-500">/100</span></div>
                    </div>
                  </div>
                  <div className="bg-gray-800/40 p-4 rounded-xl border border-gray-700/50 space-y-3">
                    <div className="text-sm text-gray-300 leading-relaxed">
                      <strong className="text-gray-200 mr-2">Match Reason:</strong> 
                      {selectedJob.match_reason || '-'}
                    </div>
                  </div>
                </div>
              )}
              
              {/* Description */}
              <div>
                <div className="flex items-center gap-2 mb-4 border-b border-gray-700/60 pb-3">
                  <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h7" /></svg>
                  <h3 className="text-lg font-bold text-gray-200">Job Description</h3>
                </div>
                <div className="bg-gray-900/80 p-6 rounded-2xl border border-gray-700 text-base text-gray-300 whitespace-pre-wrap leading-relaxed max-h-[500px] overflow-y-auto shadow-inner">
                  {selectedJob.job_description || 'No description available.'}
                </div>
              </div>

              {/* Version History */}
              {selectedJob.is_updated && selectedJob.versions && selectedJob.versions.length > 0 && (
                <div className="bg-blue-900/10 p-6 rounded-2xl border border-blue-900/30">
                  <div className="flex items-center gap-2 mb-4 border-b border-blue-900/50 pb-3">
                    <svg className="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                    <h3 className="text-lg font-bold text-blue-200">Update History</h3>
                  </div>
                  <div className="space-y-5">
                    {selectedJob.versions.map((v, i) => (
                      <div key={i} className="bg-gray-800/80 p-5 rounded-xl border border-gray-700 shadow-sm relative">
                        <div className="absolute top-0 right-0 bg-gray-700 text-gray-300 text-xs px-3 py-1 rounded-bl-lg rounded-tr-xl font-medium">
                          {new Date(v.changed_at.endsWith('Z') ? v.changed_at : v.changed_at + 'Z').toLocaleString()}
                        </div>
                        <div className="mt-2 text-sm text-gray-300 mb-3">
                          <strong className="text-gray-200">Previous Title:</strong> {v.old_title}
                        </div>
                        <div className="text-sm text-gray-400 whitespace-pre-wrap max-h-48 overflow-y-auto bg-gray-900/60 p-4 rounded-lg border border-gray-700/50 leading-relaxed">
                          {v.old_description}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
            
            {/* Action Buttons */}
            <div className="p-6 border-t border-gray-700 flex justify-end gap-4 bg-gray-800/80 rounded-b-2xl sticky bottom-0">
              <button onClick={() => setSelectedJob(null)} className="px-6 py-2.5 rounded-lg font-semibold text-gray-300 bg-gray-700 hover:bg-gray-600 hover:text-white transition-colors border border-gray-600 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 focus:ring-offset-gray-800">
                Close
              </button>
              {selectedJob.job_url && (
                <a href={selectedJob.job_url} target="_blank" rel="noopener noreferrer" className="px-6 py-2.5 rounded-lg font-semibold text-white bg-blue-600 hover:bg-blue-500 transition-all shadow-lg shadow-blue-500/20 flex items-center gap-2 border border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-gray-800">
                  Apply Now
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>
                </a>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default App
