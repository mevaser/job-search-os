import { useState, useEffect } from 'react'

function App() {
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(false)
  const [processing, setProcessing] = useState(false)

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

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100 p-8 font-sans">
      <div className="max-w-6xl mx-auto">
        <header className="flex justify-between items-center mb-8 pb-4 border-b border-gray-800">
          <div>
            <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-emerald-400">
              Job Search OS
            </h1>
            <p className="text-gray-400 mt-1">Mock Pipeline Dashboard</p>
          </div>
          <button 
            onClick={handleProcessMock} 
            disabled={processing}
            className="bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:text-gray-400 text-white font-semibold py-2 px-6 rounded-lg shadow-lg transition-all duration-200 ease-in-out transform hover:-translate-y-0.5"
          >
            {processing ? 'Processing...' : 'Process Mock Data'}
          </button>
        </header>

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
                    <th className="p-4 font-semibold text-center">Fit Score</th>
                    <th className="p-4 font-semibold text-center">Decision</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-700/50">
                  {jobs.map((job) => (
                    <tr key={job.id} className="hover:bg-gray-700/30 transition-colors">
                      <td className="p-4">
                        <div className="font-medium text-gray-200">{job.title}</div>
                        <div className="text-xs text-gray-500 mt-1">{job.location}</div>
                      </td>
                      <td className="p-4 text-gray-300">{job.company}</td>
                      <td className="p-4 text-gray-300">
                        {job.analysis?.role_family || 'N/A'}
                        <div className="text-xs text-gray-500 mt-1">Exp: {job.analysis?.experience_requirement ?? '?'} yrs</div>
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
