import { useState, useEffect } from 'react'

function App() {
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(false)
  const [processing, setProcessing] = useState(false)
  const [scanning, setScanning] = useState(false)
  const [filterDecision, setFilterDecision] = useState('All')
  const [filterStatus, setFilterStatus] = useState('All')

  const fetchJobs = async () => {
    setLoading(true)
    try {
      const res = await fetch('http://localhost:8000/api/jobs')
      const data = await res.json()
      setJobs(data)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchJobs()
  }, [])

  const handleProcessMock = async () => {
    setProcessing(true)
    try {
      await fetch('http://localhost:8000/api/jobs/process-mock', {
        method: 'POST'
      })
      await fetchJobs()
    } catch (err) {
      console.error(err)
    } finally {
      setProcessing(false)
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
      await fetchJobs()
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
    const matchDecision = filterDecision === 'All' || (job.analysis && job.analysis.decision === filterDecision)
    const matchStatus = filterStatus === 'All' || (job.application_status || 'Not Applied') === filterStatus
    return matchDecision && matchStatus
  })

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100 p-8 font-sans">
      <div className="max-w-6xl mx-auto">
        <header className="flex justify-between items-center mb-8 pb-4 border-b border-gray-800">
          <div>
            <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-emerald-400">
              Job Search OS
            </h1>
            <p className="text-gray-400 mt-1">Live Pipeline Dashboard</p>
          </div>
          <div className="flex space-x-4">
            <button 
              onClick={handleProcessMock} 
              disabled={processing || scanning}
              className="bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:text-gray-500 text-white font-semibold py-2 px-6 rounded-lg shadow-lg transition-all duration-200 ease-in-out"
            >
              {processing ? 'Processing...' : 'Process Mock Data'}
            </button>
            <button 
              onClick={handleScanLive} 
              disabled={scanning || processing}
              className="bg-blue-600 hover:bg-blue-500 disabled:bg-blue-900 disabled:text-gray-400 text-white font-semibold py-2 px-6 rounded-lg shadow-lg transition-all duration-200 ease-in-out transform hover:-translate-y-0.5 flex items-center"
            >
              {scanning ? (
                <>
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Scraping live jobs... Please wait
                </>
              ) : (
                'Scan Live Jobs'
              )}
            </button>
          </div>
        </header>

        {jobs.length > 0 && (
          <div className="flex flex-col space-y-4 mb-4">
            <div className="text-gray-300 text-lg font-medium">
              Total Jobs in DB: <span className="text-white font-bold">{jobs.length}</span>
            </div>
            
            <div className="flex flex-wrap items-center gap-6 bg-gray-800/50 p-4 rounded-xl border border-gray-700/50">
              <div className="flex items-center space-x-2">
                <label className="text-gray-400 font-medium">AI Decision:</label>
                <select 
                  value={filterDecision} 
                  onChange={(e) => setFilterDecision(e.target.value)}
                  className="bg-gray-700 text-white rounded px-3 py-1.5 border border-gray-600 focus:outline-none focus:border-blue-500"
                >
                  <option value="All">All</option>
                  <option value="KEEP">KEEP</option>
                  <option value="REVIEW">REVIEW</option>
                  <option value="REJECT">REJECT</option>
                </select>
              </div>
              
              <div className="flex items-center space-x-2">
                <label className="text-gray-400 font-medium">Application Status:</label>
                <select 
                  value={filterStatus} 
                  onChange={(e) => setFilterStatus(e.target.value)}
                  className="bg-gray-700 text-white rounded px-3 py-1.5 border border-gray-600 focus:outline-none focus:border-blue-500"
                >
                  <option value="All">All</option>
                  <option value="Not Applied">Not Applied</option>
                  <option value="Applied">Applied</option>
                  <option value="Interviewing">Interviewing</option>
                  <option value="Rejected">Rejected</option>
                  <option value="Offer">Offer</option>
                </select>
              </div>
            </div>
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
                    <th className="p-4 font-semibold">Job Title</th>
                    <th className="p-4 font-semibold">Company</th>
                    <th className="p-4 font-semibold">Role Family</th>
                    <th className="p-4 font-semibold">Scanned At</th>
                    <th className="p-4 font-semibold text-center">Fit Score</th>
                    <th className="p-4 font-semibold text-center">Decision</th>
                    <th className="p-4 font-semibold text-center">Status</th>
                    <th className="p-4 font-semibold">Notes</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-700/50">
                  {filteredJobs.map((job) => (
                    <tr key={job.id} className="hover:bg-gray-700/30 transition-colors">
                      <td className="p-4">
                        <div className="font-medium text-gray-200">
                          {job.job_url ? (
                            <a href={job.job_url} target="_blank" rel="noopener noreferrer" className="hover:text-blue-400 hover:underline">
                              {job.title}
                            </a>
                          ) : (
                            job.title
                          )}
                        </div>
                        <div className="text-xs text-gray-500 mt-1">{job.location}</div>
                      </td>
                      <td className="p-4 text-gray-300">{job.company}</td>
                      <td className="p-4 text-gray-300">
                        {job.analysis?.role_family || 'N/A'}
                        <div className="text-xs text-gray-500 mt-1">Exp: {job.analysis?.experience_requirement ?? '?'} yrs</div>
                      </td>
                      <td className="p-4 text-gray-400 text-sm whitespace-nowrap">
                        {job.created_at ? (() => {
                          const d = new Date(job.created_at.endsWith('Z') ? job.created_at : job.created_at + 'Z');
                          const pad = (n) => n.toString().padStart(2, '0');
                          return `${pad(d.getDate())}/${pad(d.getMonth()+1)}/${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
                        })() : 'N/A'}
                      </td>
                      <td className="p-4 text-center">
                        {job.analysis ? (
                          <span className={`inline-flex items-center justify-center w-10 h-10 rounded-full font-bold ${
                            job.analysis.fit_score >= 80 ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' :
                            job.analysis.fit_score >= 50 ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' :
                            'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                          }`}>
                            {job.analysis.fit_score}
                          </span>
                        ) : (
                          <span className="text-gray-600">-</span>
                        )}
                      </td>
                      <td className="p-4 text-center">
                        {job.analysis ? (
                          <span className={`px-3 py-1 rounded-full text-xs font-bold tracking-wider ${
                            job.analysis.decision === 'KEEP' ? 'bg-emerald-500 text-white shadow-lg shadow-emerald-500/20' :
                            job.analysis.decision === 'REVIEW' ? 'bg-amber-500 text-white shadow-lg shadow-amber-500/20' :
                            'bg-gray-700 text-gray-300'
                          }`}>
                            {job.analysis.decision}
                          </span>
                        ) : (
                          <span className="text-gray-600">-</span>
                        )}
                      </td>
                      <td className="p-4 text-center">
                        <select 
                          value={job.application_status || 'Not Applied'} 
                          onChange={(e) => handleUpdateJob(job.id, { application_status: e.target.value })}
                          className={`bg-gray-700 text-white rounded px-2 py-1 border focus:outline-none focus:border-blue-500 text-sm ${
                            job.application_status === 'Applied' ? 'border-blue-500' :
                            job.application_status === 'Interviewing' ? 'border-purple-500' :
                            job.application_status === 'Rejected' ? 'border-red-500' :
                            job.application_status === 'Offer' ? 'border-green-500' :
                            'border-gray-600'
                          }`}
                        >
                          <option value="Not Applied">Not Applied</option>
                          <option value="Applied">Applied</option>
                          <option value="Interviewing">Interviewing</option>
                          <option value="Rejected">Rejected</option>
                          <option value="Offer">Offer</option>
                        </select>
                      </td>
                      <td className="p-4">
                        <input 
                          type="text" 
                          placeholder="Add notes..." 
                          defaultValue={job.application_notes || ''}
                          onBlur={(e) => {
                            if (e.target.value !== (job.application_notes || '')) {
                              handleUpdateJob(job.id, { application_notes: e.target.value })
                            }
                          }}
                          className="bg-gray-700/50 text-gray-300 text-sm rounded px-3 py-1.5 border border-gray-600 focus:outline-none focus:border-blue-500 focus:bg-gray-700 w-full min-w-[150px]"
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default App
