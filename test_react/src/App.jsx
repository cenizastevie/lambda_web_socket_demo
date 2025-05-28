import { useEffect, useRef, useState } from 'react'
import 'bootstrap/dist/css/bootstrap.min.css';
import './App.css'

// API and WebSocket endpoints
const API_BASE = 'https://k6pq1bmi62.execute-api.us-east-1.amazonaws.com/Prod';
const WEBSOCKET_URL = 'wss://1sdck1nol5.execute-api.us-east-1.amazonaws.com/prod/';

function App() {
  // File upload state
  const [file, setFile] = useState(null)
  const [status, setStatus] = useState('')

  // WebSocket state
  const [wsStatus, setWsStatus] = useState('Connecting...')
  const [wsMessages, setWsMessages] = useState([])
  const wsRef = useRef(null)

  // WebSocket setup
  useEffect(() => {
    const ws = new WebSocket(WEBSOCKET_URL)
    wsRef.current = ws
    ws.onopen = () => setWsStatus('🟢 Connected')
    ws.onclose = () => setWsStatus('🔴 Disconnected')
    ws.onerror = () => setWsStatus('⚠️ Error')
    ws.onmessage = (event) => {
      setWsMessages(msgs => [...msgs, event.data])
      try {
        const msg = JSON.parse(event.data)
        if (msg.connectionId) setConnectionId(msg.connectionId)
        if (msg.scatter_plot_url) setScatterUrl(msg.scatter_plot_url)
        if (msg.bar_plot_url) setBarUrl(msg.bar_plot_url)
      } catch {}
    }
    return () => ws.close()
  }, [])

  // File upload logic
  const handleChange = (e) => {
    setFile(e.target.files[0])
    setStatus('')
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!file) return
    setStatus('Requesting presigned URL...')
    try {
      const res = await fetch(`${API_BASE}/get-presigned-url`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename: file.name })
      })
      const data = await res.json()
      if (!data.presigned_url) throw new Error(data.error || 'No presigned URL returned')
      setStatus('Uploading...')
      const uploadRes = await fetch(data.presigned_url, {
        method: 'PUT',
        body: file,
        headers: { 'Content-Type': file.type || 'text/csv' }
      })
      if (!uploadRes.ok) throw new Error('Upload failed')
      setStatus('✅ Uploaded! Now processing...')
      // After upload, trigger processing
      const processRes = await fetch(`${API_BASE}/process-csv`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ csv_filename: file.name, connection_id: connectionId })
      })
      const processData = await processRes.json()
      if (processRes.status !== 202) throw new Error(processData.error || 'Processing initiation failed')
      setStatus('Processing started! Awaiting results via WebSocket...')
    } catch (err) {
      setStatus('❌ ' + err.message)
    }
  }

  // WebSocket send message
  const [wsInput, setWsInput] = useState('')
  const [connectionId, setConnectionId] = useState('')
  const [scatterUrl, setScatterUrl] = useState('')
  const [barUrl, setBarUrl] = useState('')

  const sendWsMessage = () => {
    if (wsRef.current && wsRef.current.readyState === 1 && wsInput.trim()) {
      wsRef.current.send(JSON.stringify({ action: 'sendmessage', message: wsInput }))
      setWsMessages(msgs => [...msgs, `You: ${wsInput}`])
      setWsInput('')
    }
  }

  return (
    <div className="app-container bg-light min-vh-100 d-flex flex-column">
      <div className="container py-4 flex-grow-1">
        <h1 className="mb-4 text-center">File Upload & WebSocket Demo</h1>
        <div className="d-flex flex-column align-items-end mb-3">
          <span className="me-3">Status: <span>{wsStatus}</span></span>
          <span>Connection ID: <b>{connectionId}</b></span>
        </div>
        <div className="card mb-4">
          <div className="card-body">
            <div className="fw-bold mb-2">System Messages:</div>
            <div className="ws-messages mb-2 bg-light text-dark" style={{minHeight: 40, maxHeight: 80, overflowY: 'auto'}}>
              {wsMessages.map((msg, idx) => (
                <div key={idx}>{msg}</div>
              ))}
              {status && <div className="text-primary">{status}</div>}
            </div>
          </div>
        </div>
        <div className="card mb-4">
          <div className="card-body">
            <form onSubmit={handleSubmit} className="row g-3 align-items-center">
              <div className="col-auto">
                <label className="form-label fw-bold mb-0">File:</label>
              </div>
              <div className="col-auto">
                <input type="file" accept=".csv" onChange={handleChange} className="form-control" />
              </div>
              <div className="col-auto">
                <button type="submit" className="btn btn-primary" disabled={!file}>Upload</button>
              </div>
            </form>
          </div>
        </div>
        <div className="card mb-4">
          <div className="card-body">
            <div className="fw-bold mb-2">Bar Plot:</div>
            {barUrl ? (
              <img src={barUrl} alt="Bar Plot" className="img-fluid border rounded bg-white" style={{minHeight: 200}} />
            ) : (
              <div className="bg-light border border-2 border-dashed rounded" style={{minHeight: 200}}></div>
            )}
          </div>
        </div>
        <div className="card mb-4">
          <div className="card-body">
            <div className="fw-bold mb-2">Scatter Plot:</div>
            {scatterUrl ? (
              <img src={scatterUrl} alt="Scatter Plot" className="img-fluid border rounded bg-white" style={{minHeight: 200}} />
            ) : (
              <div className="bg-light border border-2 border-dashed rounded" style={{minHeight: 200}}></div>
            )}
          </div>
        </div>
      </div>
      <footer className="text-center py-3 text-muted bg-white mt-auto">Powered by AWS Lambda & API Gateway • {new Date().getFullYear()}</footer>
    </div>
  )
}

export default App
