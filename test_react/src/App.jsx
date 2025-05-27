import { useEffect, useRef, useState } from 'react'
import './App.css'

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
    const ws = new WebSocket('wss://1sdck1nol5.execute-api.us-east-1.amazonaws.com/prod/')
    wsRef.current = ws
    ws.onopen = () => setWsStatus('🟢 Connected')
    ws.onclose = () => setWsStatus('🔴 Disconnected')
    ws.onerror = () => setWsStatus('⚠️ Error')
    ws.onmessage = (event) => setWsMessages(msgs => [...msgs, event.data])
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
    console.log('File selected:', file)
    try {
      const res = await fetch('https://k6pq1bmi62.execute-api.us-east-1.amazonaws.com/Prod/get-presigned-url', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename: file.name })
      })
      const data = await res.json()
      console.log(data)
      if (!data.presigned_url) throw new Error(data.error || 'No presigned URL returned')
      setStatus('Uploading...')
      const uploadRes = await fetch(data.presigned_url, {
        method: 'PUT',
        body: file,
        headers: { 'Content-Type': file.type || 'text/csv' }
      })
      if (!uploadRes.ok) throw new Error('Upload failed')
      setStatus('✅ Uploaded!')
    } catch (err) {
      setStatus('❌ ' + err.message)
    }
  }

  // WebSocket send message
  const [wsInput, setWsInput] = useState('')
  const sendWsMessage = () => {
    if (wsRef.current && wsRef.current.readyState === 1 && wsInput.trim()) {
      wsRef.current.send(JSON.stringify({ action: 'sendmessage', message: wsInput }))
      setWsMessages(msgs => [...msgs, `You: ${wsInput}`])
      setWsInput('')
    }
  }

  return (
    <div className="app-container">
      <h1>File Upload & WebSocket Demo</h1>
      <div className="main-content">
        {/* File Upload */}
        <form onSubmit={handleSubmit}>
          <label>Select CSV File</label>
          <input type="file" accept=".csv" onChange={handleChange} />
          <button type="submit" disabled={!file}>Upload</button>
          {status && <div className="status">{status}</div>}
        </form>
        {/* WebSocket Chat */}
        <div className="ws-box">
          <div>WebSocket Connection</div>
          <div>Status: <span>{wsStatus}</span></div>
          <div className="ws-messages">
            {wsMessages.map((msg, idx) => (
              <div key={idx}>{msg}</div>
            ))}
          </div>
          <input
            type="text"
            value={wsInput}
            onChange={e => setWsInput(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); sendWsMessage(); } }}
            placeholder="Type message..."
          />
          <button type="button" onClick={sendWsMessage} disabled={!wsInput.trim() || wsStatus !== '🟢 Connected'}>Send</button>
        </div>
      </div>
      <footer>Powered by AWS Lambda & API Gateway • {new Date().getFullYear()}</footer>
    </div>
  )
}

export default App
